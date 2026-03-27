import anthropic
import base64
import os
from pathlib import Path
from PIL import Image
from PIL.ExifTags import TAGS
from datetime import datetime
import io
import json


def encode_image(image_path: str) -> tuple[str, str]:
    """Encode image to base64 and detect media type."""
    path = Path(image_path).expanduser()
    ext = path.suffix.lower()
    media_type_map = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }
    media_type = media_type_map.get(ext, "image/jpeg")

    # Resize if image is too large
    img = Image.open(path)
    img.thumbnail((2048, 2048))

    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=85)
    buffer.seek(0)

    return base64.standard_b64encode(buffer.read()).decode("utf-8"), "image/jpeg"


def get_exif_date(image_path: str) -> str | None:
    """Extract date from image EXIF data."""
    try:
        img = Image.open(image_path)
        exif_data = img._getexif()
        if exif_data:
            for tag_id, value in exif_data.items():
                tag = TAGS.get(tag_id, tag_id)
                if tag == "DateTimeOriginal":
                    return value[:10].replace(":", "-")
    except Exception:
        pass
    return None


def get_known_people_in_photo(image_path: str) -> list[str]:
    """
    Use face_recognition to identify known people in a photo.
    Returns list of known names found. Falls back gracefully if face_recognition fails.
    """
    try:
        import face_recognition
        import numpy as np
        from .database import get_all_faces

        # Load known faces from MongoDB
        known_faces = get_all_faces()
        if not known_faces:
            return []

        # Load and resize image
        img = Image.open(Path(image_path).expanduser())
        img.thumbnail((1024, 1024))
        img = img.convert("RGB")
        img_array = np.array(img)

        # Detect faces in photo
        face_locations = face_recognition.face_locations(img_array)
        if not face_locations:
            return []

        # Get encodings for detected faces
        face_encodings = face_recognition.face_encodings(img_array, face_locations)

        # Load known encodings from MongoDB
        known_encodings = [np.array(f["encoding"]) for f in known_faces]
        known_names = [f["display_name"] for f in known_faces]

        # Match each detected face
        matched_names = []
        for face_encoding in face_encodings:
            matches = face_recognition.compare_faces(
                known_encodings, face_encoding, tolerance=0.6
            )
            distances = face_recognition.face_distance(known_encodings, face_encoding)

            if True in matches:
                best_match_idx = np.argmin(distances)
                if matches[best_match_idx]:
                    matched_names.append(known_names[best_match_idx])
                else:
                    matched_names.append("unknown")
            else:
                matched_names.append("unknown")

        return matched_names

    except Exception as e:
        print(f"Face recognition failed, falling back to Claude: {e}")
        return []


def analyze_image(image_path: str, include_people: bool = True) -> dict:
    """
    Analyze image using Claude Vision API.
    If include_people=True, first tries face_recognition for known people,
    then passes that info to Claude for filename generation.
    """
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    image_data, media_type = encode_image(image_path)

    # Phase 2 — get known people first
    known_people = []
    if include_people:
        known_people = get_known_people_in_photo(image_path)

    # Build people context for Claude
    known_people_context = ""
    if known_people:
        names = [n for n in known_people if n != "unknown"]
        unknowns = known_people.count("unknown")
        if names:
            known_people_context = (
                f"\nKnown people identified in this photo: {', '.join(names)}."
            )
            if unknowns:
                known_people_context += (
                    f" There are also {unknowns} unidentified person(s)."
                )
            known_people_context += (
                " Please use their actual names in the description and filename."
            )

    # Build prompt
    people_instruction = ""
    if include_people:
        people_instruction = """
- People: Describe any people present. Use provided names for identified people.
  For unidentified people use descriptive slugs (e.g. 'elderly-man', 'young-girl').
  If no people, return ["no-people"]."""

    prompt = f"""Analyze this image and provide:
1. A descriptive filename slug (5-8 words, hyphenated, lowercase)
2. A short description (1-2 sentences) — use known people's names if identified"
3. Key tags (5-7 words){people_instruction}
{known_people_context}

Respond in this exact JSON format:
{{
  "filename_slug": "descriptive-slug-here",
  "description": "Short description of the image.",
  "tags": ["tag1", "tag2", "tag3"],
  "people": ["person1", "person2"]
}}

For filename_slug, incorporate known people names if present.
Example: "rishi-and-anya-birthday-cake-celebration"

Only respond with raw JSON, no markdown, no backticks, nothing else."""

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=500,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_data,
                        },
                    },
                    {"type": "text", "text": prompt},
                ],
            }
        ],
    )

    raw = response.content[0].text
    raw = (
        raw.strip()
        .removeprefix("```json")
        .removeprefix("```")
        .removesuffix("```")
        .strip()
    )
    result = json.loads(raw)

    # Add EXIF date if available
    exif_date = get_exif_date(image_path)
    if exif_date:
        result["exif_date"] = exif_date
        result["filename_with_date"] = f"{exif_date}-{result['filename_slug']}"
    else:
        result["filename_with_date"] = result["filename_slug"]

    # Add known people to result
    result["known_people"] = [n for n in known_people if n != "unknown"]
    result["unknown_faces"] = known_people.count("unknown")

    # Add original filename
    result["original_filename"] = Path(image_path).name
    result["extension"] = Path(image_path).suffix.lower()

    return result


def rename_photo(image_path: str, result: dict, dry_run: bool = True) -> str:
    """Rename photo based on analysis result."""
    new_name = f"{result['filename_with_date']}{result['extension']}"
    new_path = Path(image_path).parent / new_name

    if not dry_run:
        Path(image_path).rename(new_path)
        return str(new_path)

    return str(new_path)
