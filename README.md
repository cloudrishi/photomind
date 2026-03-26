# 📸 PhotoMind

> Give meaningful names to your photos with AI

PhotoMind uses **Claude Vision AI** to analyze your photos and suggest meaningful, searchable filenames. Say goodbye to `IMG_4821.jpg` and hello to `grandfather-teaching-grandchildren-cooking-kitchen.jpg`.

---

## ✨ Features

- **Smart Naming** — Claude Vision analyzes content and generates descriptive slugs
- **People Detection** — Identifies and describes people in photos
- **EXIF Date Extraction** — Prepends date from photo metadata (e.g. `2024-03-15-sunset-over-lake.jpg`)
- **Batch Processing** — Rename entire folders at once
- **Dry Run Mode** — Preview suggested names before applying
- **Web UI** — Drag & drop interface via Gradio
- **CLI** — Power user mode for terminal workflows
- **Auto Resize** — Handles large photos automatically (resizes before sending to API)

---

## 🖼️ Demo

| Original | Suggested |
|---|---|
| `photo1.jpg` | `grandfather-teaching-grandchildren-cooking-kitchen.jpg` |
| `photo2.jpg` | `modern-glass-building-geometric-architecture.jpg` |
| `photo3.jpg` | `woman-tropical-plants-sunglasses-headwrap.jpg` |
| `IMG_4821.jpg` | `wildflower-meadow-sunset-mountain-landscape.jpg` |

---

## 🏗️ Architecture

```
Photo (JPG/PNG/WebP)
        │
        ▼
   Auto Resize (if > 5MB)
        │
        ▼
  Claude Vision API
  (Haiku model — fast & cheap)
        │
        ▼
  JSON Response
  (slug, description, tags, people)
        │
        ├── EXIF Date Extraction
        │
        ▼
  New Filename
  (date-descriptive-slug.jpg)
        │
        ├── Gradio Web UI
        └── CLI
```

---

## 🚀 Getting Started

### Prerequisites

- Python 3.11+
- Anthropic API key — get one at [console.anthropic.com](https://console.anthropic.com)

### Installation

```bash
# Clone the repo
git clone https://github.com/cloudrishi/photomind.git
cd photomind

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set your API key
export ANTHROPIC_API_KEY="sk-ant-..."
# Or add to ~/.zshrc for permanent use
```

### Run Web UI

```bash
python main.py
# Opens at http://127.0.0.1:7860
```

### Run CLI

```bash
# Single photo — dry run
python -m src.cli analyze ~/Photos/IMG_4821.jpg

# Single photo — rename
python -m src.cli analyze ~/Photos/IMG_4821.jpg --rename

# Batch folder — dry run
python -m src.cli batch ~/Photos/vacation/

# Batch folder — rename all
python -m src.cli batch ~/Photos/vacation/ --rename

# Save batch results to JSON
python -m src.cli batch ~/Photos/vacation/ --output-json results.json
```

---

## ⚙️ Configuration

| Environment Variable | Description |
|---|---|
| `ANTHROPIC_API_KEY` | Your Anthropic API key (required) |

---

## 📁 Project Structure

```
photomind/
├── src/
│   ├── analyzer.py      # Core AI logic — Claude Vision API
│   ├── app.py           # Gradio web UI
│   ├── cli.py           # CLI interface
│   └── __init__.py
├── main.py              # Entry point for web UI
├── requirements.txt     # Dependencies
└── README.md
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| AI Vision | Claude Haiku (Anthropic) |
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
- [ ] **Phase 2** — Known people recognition using reference photos (`face_recognition`)
- [ ] **Phase 3** — Auto-organize into folders by date/event/people

---

## 🧑‍💻 Author

**Rishi Pherwani** — Senior Technical Architect & Software Engineer  
[GitHub](https://github.com/cloudrishi) · [LinkedIn](https://linkedin.com/in/rpherwani)

---

## 📄 License

MIT
