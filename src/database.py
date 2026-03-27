from pymongo import MongoClient
from datetime import datetime
import numpy as np

MONGO_URI = "mongodb://admin:photomind123@localhost:27017/"
DB_NAME = "photomind"


def get_db():
    """Get database connection."""
    client = MongoClient(MONGO_URI)
    return client[DB_NAME]


# ─── Face Operations ─────────────────────────────────────────────────────────
def save_face_encoding(name: str, encoding: list, photo_path: str) -> str:
    """Save a person's face encoding to MongoDB"""
    db = get_db()
    # Remove existing encoding for the same person
    db.faces.delete_many({"name": name.lower()})

    result = db.faces.insert_one(
        {
            "name": name.lower(),
            "display_name": name,
            "encoding": encoding,
            "reference_photo": photo_path,
            "added_on": datetime.utcnow().isoformat(),
        }
    )
    return str(result.inserted_id)


def get_all_faces() -> list:
    """Get all known face encodings for MongoDB."""
    db = get_db()
    return list(db.faces.find({}, {"_id": 0}))


def list_known_people() -> list[str]:
    """List all known people names"""
    db = get_db()
    return [doc["display_name"] for doc in db.faces.find({}, {"display_name": 1})]


# ─── Photo History Operations ─────────────────────────────────────────────────────────
def save_photo_history(
    original: str, renamed: str, description: str, tags: list, people: list
):
    """Save photo rename history to MongoDB"""
    db = get_db()
    db.photo_history.insert_one(
        {
            "original_filename": original,
            "renamed_filename": renamed,
            "description": description,
            "tags": tags,
            "people": people,
            "processed_on": datetime.utcnow().isoformat(),
        }
    )


def get_photo_history(limit: int = 50) -> list:
    """Get recent photo rename history."""
    db = get_db()
    return list(
        db.photo_history.find({}, {"_id": 0}).sort("processed_on", -1).limit(limit)
    )
