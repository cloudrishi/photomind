import face_recognition
from pathlib import Path
from PIL import Image
import numpy as np
from .database import save_face_encoding, list_known_people

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def enroll_person(image_path: str, name: str = None) -> dict:
    """
    Enroll a person from a reference phot.
    If name is not provided, used the filename as the name.
    Returns a dict with status and name.
    """
    path = Path(image_path).expanduser()

    # Use filename as name if not provided
    if not name:
        name = path.stem  # filname without extension

    # Resize large images
    img = Image.open(path)
    img.thumbnail((1024, 1024))
    img = img.convert("RGB")

    # Convert to numpy array for face_recognition
    img_array = np.array(img)

    # Detect faces
    face_locations = face_recognition.face_locations(img_array)

    if len(face_locations) == 0:
        return {
            "status": "error",
            "name": name,
            "message": f"No face detected in {path.name}",
        }

    if len(face_locations) == 0:
        return {
            "status": "error",
            "name": name,
            "message": f"Multiple faces detected in {path.name}. Use a solo photo.",
        }

    # Generate face encoding
    encodings = face_recognition.face_encodings(img_array, face_locations)
    encoding = encodings[0].tolist()  # Convert numpy to list for MongoDB

    # Save to MongoDB
    save_face_encoding(name, encoding, str(path))

    return {
        "status": "success",
        "name": name,
        "message": f"✅ Enrolled {name} successfully!",
    }


def enroll_from_folder(folder_path: str) -> list:
    """
    Enroll all people from a reference folder.
    Each photo should be named after the person.
    """
    folder = Path(folder_path).expanduser()
    if not folder.exists():
        return [{"status": "error", "message": f"Folder not found: {folder_path}"}]

    photos = [f for f in folder.iterdir() if f.suffix.lower() in SUPPORTED_EXTENSIONS]
    if not photos:
        return [{"status": "error", "message": "No photos found in folder"}]

    results = []
    for photo in photos:
        print(f"Enrolling {photo.stem}...")
        result = enroll_person(str(photo))
        results.append(result)
        print(f"  {result['message']}")

    return results


def match_faces(image_path: str, tolerance: float = 0.6) -> list:
    """
    Match faces in a photo against known faces in MongoDB.
    Returns list of matched names or 'unknown' for unrecognized faces.
    tolerance: lower = stricter matching (0.4-0.6 recommended)
    """
    from .database import get_all_faces

    path = Path(image_path).expanduser()

    # Load and resize image
    img = Image.open(path)
    img.thumbnail((1024, 1024))
    img = img.convert("RGB")
    img_array = np.array(img)

    # Detect faces in photo
    face_locations = face_recognition.face_locations(img_array)
    if not face_locations:
        return []

    # Get encodings for detected faces
    face_encodings = face_recognition.face_encodings(img_array, face_locations)

    # Load known faces from MongoDB
    known_faces = get_all_faces()
    if not known_faces:
        return ["unknown"] * len(face_encodings)

    known_encodings = [np.array(f["encoding"]) for f in known_faces]
    known_names = [f["display_name"] for f in known_faces]

    # Match each detected face
    matched_names = []
    for face_encoding in face_encodings:
        matches = face_recognition.compare_faces(
            known_encodings, face_encoding, tolerance=tolerance
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


def get_unknown_faces(image_path: str, tolerance: float = 0.6) -> list[dict]:
    """
    Detect unknown faces in a photo.
    Returns list of dicts with cropped face image and encoding.
    """
    import face_recognition
    import numpy as np
    from .database import get_all_faces

    path = Path(image_path).expanduser()

    # Load and resize image
    img = Image.open(path)
    img.thumbnail((1024, 1024))
    img = img.convert("RGB")
    img_array = np.array(img)

    # Detect faces
    face_locations = face_recognition.face_locations(img_array)
    if not face_locations:
        return []

    # Get encodings
    face_encodings = face_recognition.face_encodings(img_array, face_locations)

    # Load known faces from MongoDB
    known_faces = get_all_faces()
    known_encodings = [np.array(f["encoding"]) for f in known_faces]

    unknown_faces = []
    for i, (face_encoding, face_location) in enumerate(
        zip(face_encodings, face_locations)
    ):
        # Check if face is known
        if known_encodings:
            matches = face_recognition.compare_faces(
                known_encodings, face_encoding, tolerance=tolerance
            )
            if True in matches:
                continue  # Skip known faces

        # Crop unknown face
        top, right, bottom, left = face_location
        padding = 20
        top = max(0, top - padding)
        right = min(img_array.shape[1], right + padding)
        bottom = min(img_array.shape[0], bottom + padding)
        left = max(0, left - padding)

        face_crop = img.crop((left, top, right, bottom))

        # Save cropped face to temp file
        crops_dir = Path(__file__).parent.parent / "temp_crops"
        crops_dir.mkdir(exist_ok=True)
        crop_path = str(crops_dir / f"unknown_face_{i}.jpg")
        face_crop.save(crop_path)

        unknown_faces.append(
            {
                "index": i,
                "encoding": face_encoding.tolist(),
                "crop_path": crop_path,
                "location": face_location,
            }
        )

    return unknown_faces


def enroll_unknown_face(encoding: list, name: str, crop_path: str) -> dict:
    """
    Enroll an unknown face that was identified by the user.
    """
    from .database import save_face_encoding

    save_face_encoding(name, encoding, crop_path)
    return {
        "status": "success",
        "name": name,
        "message": f"✅ {name} enrolled successfully!",
    }
