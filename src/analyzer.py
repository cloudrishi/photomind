import anthropic
import base64
import os
from pathlib import Path
from PIL import Image
from PIL.ExifTags import TAGS
from slugify import slugify
from datetime import datetime
from anthropic.types import MessageParam

"""
analyzer.py — the brain:
  encode_image() — converts photo to base64 for the API
  get_exif_date() — pulls the date the photo was taken from metadata
  analyze_image() — sends photo to Claude, gets back JSON with filename, description, tags, people
  rename_photo() — applies the new name (or just previews it in dry run mode)
"""


def encode_image(image_path: str) -> tuple[str, str]:
    """Encode image to base64 and detect media type."""
    path = Path(image_path)
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
    img.thumbnail((2048, 2048))  # Max 2048px on longest side

    import io

    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=85)
    buffer.seek(0)

    return base64.standard_b64encode(buffer.read()).decode("utf-8"), "image/jpeg"


#    with open(image_path, "rb") as f:
#        return base64.standard_b64encode(f.read()).decode("utf-8"), media_type


def get_exif_date(image_path: str) -> str | None:
    """Extract data from Inage EXIF data"""
    try:
        img = Image.open(image_path)
        exif_data = img.getexif()
        if exif_data:
            for tag_id, value in exif_data.items():
                tag = TAGS.get(tag_id, tag_id)
                if tag == "DataTimeOriginal":
                    # Format: "2024:03:15 10:30:00" -> "2024-03-15"
                    dt_obj = datetime.strptime(value, "%Y:%m:%d %H:%M:%S")
                    return dt_obj.strftime("%Y-%m-%d")
    except Exception:
        pass
    return None


def analyze_image(image_path: str, include_people: bool = True) -> dict:
    """
    Analyze image using Claude Vision API.
    Returns a dictionary with suggested filename, description, and people tags
    """
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    image_data, media_type = encode_image(image_path)

    # Build prompt based on options
    people_instruction = ""
    if include_people:
        people_instruction = """
- People: Describe any people present (e.g. 'young-woman-laughing', 'elderly-couple', 'two-kids-playing')
  If no people, say 'no-people'."""

    prompt = f"""Analyze this image and provide:
1. A descriptive filename slug (5-8 words, hyphenated, lowercase, no special chars)
2. A short description (1-2 sentences)
3. Key tags (5-7 words){people_instruction}

Respond in this exact JSON format:
{{
  "filename_slug": "descriptive-slug-here",
  "description": "Short description of the image.",
  "tags": ["tag1", "tag2", "tag3"],
  "people": ["person-description-1", "person-description-2"]
}}

For the filename_slug, be specific and meaningful. Examples:
- "golden-retriever-running-on-beach-sunset"
- "family-birthday-cake-candles-living-room"
- "downtown-austin-skyline-night-lights"
claude-haiku-4-5-20251001
Only respond with the JSON, nothing else."""
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

    import json

    # print(type(response.content[0]))
    # print(response.content[0])
    raw = response.content[0].text
    raw = (
        raw.strip()
        .removeprefix("```json")
        .removeprefix("```")
        .removesuffix("```")
        .strip()
    )
    result = json.loads(raw)
    # result = json.loads(response.content[0].text)

    # Add EXIF date if available
    exif_date = get_exif_date(image_path)
    if exif_date:
        result["exif_date"] = exif_date
        result["filename_with_date"] = f"{exif_date}-{result['filename_slug']}"
    else:
        result["filename_with_date"] = result["filename_slug"]

    # Add original filename
    result["original_filename"] = Path(image_path).name
    result["extension"] = Path(image_path).suffix.lower()

    return result


def rename_photo(image_path: str, result: dict, dry_run: bool = True) -> str:
    """
    Rename photo based. on analysis result.
    dry_run=True jsut returns the new name without renaming
    """
    new_name = f"{result['filename_with_date']}{result['extension']}"
    new_path = Path(image_path).parent / new_name

    if not dry_run:
        Path(image_path).rename(new_path)
        return str(new_path)

    return str(new_path)
