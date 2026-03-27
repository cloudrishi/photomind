# PhotoMind — Architecture & Module Documentation

## Overview

PhotoMind is organized into 5 core modules, each with a single clear responsibility.

```
User
 ├── Web Browser → app.py (Gradio UI)
 └── Terminal    → cli.py (CLI)
                      │
                      ▼
                 analyzer.py (Core AI Engine)
                 ├── Claude Vision API
                 └── enroll.py (Face Recognition)
                          │
                          ▼
                    database.py (MongoDB)
```

---

## 📄 Module Breakdown

---

### 1. `analyzer.py` — Core AI Engine

**Purpose:** The brain of PhotoMind. Orchestrates the entire photo analysis pipeline.

**Responsibilities:**
- Encode photos to base64 for Claude Vision API
- Resize large images (>5MB) before sending to API
- Extract EXIF date metadata from photos
- Call `get_known_people_in_photo()` from `enroll.py` to identify known faces
- Build Claude prompt with known people context
- Call Claude Haiku Vision API and parse JSON response
- Combine face recognition results + Claude response into final result
- Rename or copy photo to output location

**Key Functions:**

| Function | Description |
|---|---|
| `encode_image(path)` | Converts photo to base64, resizes if >5MB |
| `get_exif_date(path)` | Extracts date taken from photo EXIF metadata |
| `get_known_people_in_photo(path)` | Runs face recognition, returns known names |
| `analyze_image(path, include_people)` | Main function — full analysis pipeline |
| `rename_photo(path, result, dry_run)` | Renames or copies photo with new filename |

**Data flow:**
```
image_path
    → encode_image() → base64
    → get_known_people_in_photo() → ["rishi", "rakesh"]
    → build Claude prompt with names
    → Claude API → JSON response
    → get_exif_date() → "2015-09-26"
    → combine → final result dict
```

---

### 2. `app.py` — Gradio Web UI

**Purpose:** The web interface. Provides a user-friendly drag-and-drop UI for all PhotoMind features.

**Responsibilities:**
- Build and serve the Gradio web application on `http://127.0.0.1:7860`
- Handle photo uploads and pass them to `analyzer.py`
- Display analysis results (filename, description, tags, people)
- Show cropped unknown faces in gallery — "Who is this?"
- Handle face enrollment from the UI
- Process batch folder analysis with progress tracking
- Manage people enrollment and listing via Manage People tab

**Tabs:**

| Tab | Functionality |
|---|---|
| 🖼️ Single Photo | Upload, analyze, enroll unknown faces, save to output folder |
| 📁 Batch Folder | Process entire folder, dry run or apply rename |
| 👥 Manage People | Enroll from reference folder, view enrolled people |

**Key Functions:**

| Function | Description |
|---|---|
| `process_photo()` | Handles single photo analysis, returns 8 outputs to UI |
| `enroll_selected()` | Enrolls unknown face with user-provided name |
| `process_batch()` | Processes all photos in a folder with progress log |
| `enroll_from_folder_ui()` | Wraps enroll_from_folder for UI |
| `get_known()` | Returns list of enrolled people for display |
| `build_ui()` | Constructs the full Gradio interface |

---

### 3. `cli.py` — Command Line Interface

**Purpose:** Power user mode. Provides terminal commands for single photo and batch processing without a browser.

**Responsibilities:**
- Parse command line arguments and flags using `click`
- Call `analyze_image()` from `analyzer.py`
- Display results in formatted terminal output
- Support dry run and apply rename modes
- Support batch folder processing with optional JSON output

**Commands:**

| Command | Description |
|---|---|
| `analyze <path>` | Analyze a single photo, show suggested name |
| `analyze <path> --rename` | Analyze and rename the file |
| `analyze <path> --no-people` | Skip people detection |
| `batch <folder>` | Analyze all photos in folder (dry run) |
| `batch <folder> --rename` | Analyze and rename all photos |
| `batch <folder> --output-json results.json` | Save results to JSON |

**Example output:**
```
📸 Original:    IMG_0957.jpeg
✨ Suggested:   2015-09-26-rishi-and-rakesh-bar-portrait-arms.jpeg
📝 Description: Rishi and Rakesh pose together at a bar...
🏷️  Tags:        bar, portrait, friends, casual, indoor
👤 People:      rishi, rakesh
📅 Date:        2015-09-26
```

---

### 4. `database.py` — MongoDB Data Layer

**Purpose:** All database operations. Single source of truth for face encodings and photo history.

**Responsibilities:**
- Manage MongoDB connection (`admin/photomind123@localhost:27017`)
- CRUD operations on the `faces` collection
- Store and retrieve photo rename history in `photo_history` collection

**Collections:**

#### `faces` collection
Stores face encodings for known people.
```json
{
  "name": "rishi",
  "display_name": "rishi",
  "encoding": [0.12, -0.45, ...],
  "reference_photo": "/path/to/rishi.jpeg",
  "added_on": "2026-03-26T10:00:00"
}
```

#### `photo_history` collection
Stores history of renamed photos.
```json
{
  "original_filename": "IMG_0957.jpeg",
  "renamed_filename": "2015-09-26-rishi-and-rakesh-bar-portrait.jpeg",
  "description": "Rishi and Rakesh at a bar...",
  "tags": ["bar", "portrait", "friends"],
  "people": ["rishi", "rakesh"],
  "processed_on": "2026-03-26T10:00:00"
}
```

**Key Functions:**

| Function | Description |
|---|---|
| `get_db()` | Returns MongoDB database connection |
| `save_face_encoding(name, encoding, photo_path)` | Saves or updates a person's face encoding |
| `get_all_faces()` | Returns all enrolled face documents |
| `delete_face(name)` | Removes a person from the database |
| `list_known_people()` | Returns list of enrolled person names |
| `save_photo_history(...)` | Saves rename history entry |
| `get_photo_history(limit)` | Returns recent rename history |

---

### 5. `enroll.py` — Face Recognition Engine

**Purpose:** Everything related to face detection, encoding, matching, and enrollment.

**Responsibilities:**
- Enroll known people from reference photos
- Generate 128-point face encodings using `face_recognition` + `dlib`
- Match faces in photos against MongoDB encodings
- Detect and crop unknown faces for UI display
- Enroll unknown faces identified by the user

**Key Functions:**

| Function | Description |
|---|---|
| `enroll_person(path, name)` | Enrolls a single person from a reference photo |
| `enroll_from_folder(folder)` | Enrolls all people from a reference folder |
| `match_faces(path, tolerance)` | Matches faces in photo against MongoDB, returns names |
| `get_unknown_faces(path)` | Detects unknown faces, returns cropped images + encodings |
| `enroll_unknown_face(encoding, name, crop_path)` | Saves a newly identified unknown face to MongoDB |

**Face matching logic:**
```
Detect face locations in photo
    → Generate 128-point encoding per face
    → Load known encodings from MongoDB
    → Compare each face against known encodings
    → Distance < 0.6 → match → return name
    → Distance > 0.6 → no match → return "unknown"
```

**Tolerance:**
- `0.4` — very strict, fewer false positives
- `0.6` — default, good balance
- `0.7` — lenient, more matches but risk of false positives

---

## 🔄 How the Modules Work Together

### Single Photo Analysis Flow
```
User uploads photo (app.py)
    → process_photo() calls analyze_image() (analyzer.py)
        → get_known_people_in_photo() calls match_faces() (enroll.py)
            → get_all_faces() fetches encodings (database.py)
            → returns ["rishi", "rakesh"]
        → Claude API called with names as context
        → returns result dict
    → get_unknown_faces() (enroll.py) detects unrecognized faces
    → crops saved to temp_crops/
    → UI displays results + unknown face gallery (app.py)

User enrolls unknown face (app.py)
    → enroll_selected() calls enroll_unknown_face() (enroll.py)
        → save_face_encoding() saves to MongoDB (database.py)
    → User re-analyzes → now recognized!
```

### Batch Processing Flow
```
User enters folder path (app.py or cli.py)
    → iterate all photos
    → analyze_image() for each (analyzer.py)
    → rename_photo() or copy to output folder
    → log results
```

---

## 🛠️ Tech Stack Summary

| Module | Key Libraries |
|---|---|
| `analyzer.py` | `anthropic`, `Pillow`, `python-slugify` |
| `app.py` | `gradio` |
| `cli.py` | `click` |
| `database.py` | `pymongo` |
| `enroll.py` | `face_recognition`, `dlib`, `numpy`, `Pillow` |
