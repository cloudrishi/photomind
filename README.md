# 📸 PhotoMind

> Give meaningful names to your photos with AI — and remember the people in them

PhotoMind uses **Claude Vision AI** and **face recognition** to analyze your photos, identify known people, and suggest meaningful, searchable filenames. Say goodbye to `IMG_0957.jpg` and hello to `2015-09-26-rishi-and-rakesh-bar-portrait-arms.jpeg`.

---

## ✨ Features

### Phase 1 — Smart Naming
- **Claude Vision AI** — analyzes content and generates descriptive slugs
- **People Detection** — describes people in photos generically
- **EXIF Date Extraction** — prepends date from photo metadata
- **Batch Processing** — rename entire folders at once
- **Dry Run Mode** — preview suggested names before applying
- **Web UI** — drag & drop interface via Gradio
- **Auto Resize** — handles large photos automatically

### Phase 2 — Face Recognition
- **Known People Detection** — identifies enrolled people by name using `face_recognition`
- **MongoDB Storage** — stores face encodings in a local MongoDB instance
- **Hybrid Approach** — face recognition for known people, Claude for unknowns
- **Real Names in Filenames** — `rishi-and-rakesh-bar-portrait.jpeg` instead of `two-men-bar-photo.jpeg`
- **Enrollment Script** — enroll people from a reference photo folder
- **Graceful Fallback** — if face recognition fails, Claude handles people detection

---

## 🖼️ Demo

| Original | Phase 1 | Phase 2 |
|---|---|---|
| `IMG_0957.jpeg` | `two-men-bar-casual-portrait.jpeg` | `2015-09-26-rishi-and-rakesh-bar-portrait-arms.jpeg` |
| `photo1.jpg` | `elderly-man-teaching-children.jpg` | `grandfather-teaching-grandchildren-cooking-kitchen.jpg` |

---

## 🏗️ Architecture

```
Photo (JPG/PNG/WebP)
        │
        ▼
   Auto Resize (if > 5MB)
        │
        ├── face_recognition
        │   ├── Detect faces
        │   ├── Compare against MongoDB encodings
        │   └── Return known names ["rishi", "rakesh"]
        │
        ▼
  Claude Vision API (Haiku)
  + Known people context
        │
        ▼
  JSON Response
  (slug, description, tags, people)
        │
        ├── EXIF Date Extraction
        │
        ▼
  New Filename
  2015-09-26-rishi-and-rakesh-bar-portrait.jpeg
        │
        ├── Gradio Web UI
        └── CLI
```

---

## 🚀 Getting Started

### Prerequisites

- Python 3.11+
- Docker Desktop (for MongoDB)
- Anthropic API key — get one at [console.anthropic.com](https://console.anthropic.com)
- CMake and dlib (for face recognition)

### Installation

```bash
# Install dlib dependencies
brew install cmake
brew install dlib

# Clone the repo
git clone https://github.com/cloudrishi/photomind.git
cd photomind

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set your API key
export ANTHROPIC_API_KEY="sk-ant-..."
```

### Start MongoDB

```bash
docker compose up -d
```

### Enroll Known People (Phase 2)

```bash
# Create reference folder
mkdir reference_faces

# Add photos named after each person
# reference_faces/rishi.jpeg
# reference_faces/anya.jpeg
# reference_faces/rakesh.jpeg

# Enroll all people
python -c "
from src.enroll import enroll_from_folder
results = enroll_from_folder('reference_faces')
for r in results:
    print(r)
"
```

### Run Web UI

```bash
python main.py
# Opens at http://127.0.0.1:7860
```

---

## 📁 Project Structure

```
photomind/
├── src/
│   ├── analyzer.py      # Core AI logic — Claude Vision + face recognition
│   ├── app.py           # Gradio web UI
│   ├── cli.py           # CLI interface
│   ├── database.py      # MongoDB operations
│   ├── enroll.py        # Face enrollment script
│   └── __init__.py
├── reference_faces/     # Reference photos for enrollment (gitignored)
├── sample_photos/       # Test photos (gitignored)
├── docker-compose.yml   # MongoDB container
├── main.py              # Entry point
└── requirements.txt
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| AI Vision | Claude Haiku (Anthropic) |
| Face Recognition | face_recognition + dlib |
| Database | MongoDB (Docker) |
| Web UI | Gradio |
| Image Processing | Pillow |
| CLI | Click |
| Filename Slugs | python-slugify |

---

## 💰 Cost

Using Claude Haiku — the most cost-efficient model:
- ~$0.001 per photo
- 1,000 photos ≈ $1.00
- New accounts get $5 free credit

---

## 🗺️ Roadmap

- [x] **Phase 1** — Smart naming, people detection, batch processing, Gradio UI
- [x] **Phase 2** — Known people recognition using face_recognition + MongoDB
- [ ] **Phase 3** — "Who is this?" unknown face prompt in Gradio UI
- [ ] **Phase 4** — Auto-organize into folders by date/event/people

---

## 🧑‍💻 Author

**Rishi Pherwani** — Senior Technical Architect & Software Engineer  
[GitHub](https://github.com/cloudrishi) · [LinkedIn](https://linkedin.com/in/rpherwani)

---

## 📄 License

MIT
