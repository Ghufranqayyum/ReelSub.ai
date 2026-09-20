# 🎬 ReelSub AI

**AI-powered video editing web app that turns raw footage into Instagram-Reels-style vertical videos with automatic, word-level animated subtitles.**

Built with **Flask + React + OpenAI Whisper + FFmpeg + MoviePy** — upload a long video or multiple clips, get back a fully captioned, transition-stitched, logo-branded reel with background music, no manual editing required.

---

## ✨ Features

- **Two editing modes**
  - **Single Long Video** — upload one video, define multiple timestamp segments, auto-crop and merge them into one reel.
  - **Multiple Clips** — drag-and-drop several clips, reorder them, and stitch them together with per-transition control.
- **AI transcription** — OpenAI Whisper generates word-level timestamps, automatically grouped into short, punchy subtitle "cards."
- **Kinetic subtitle styling** — three subtitle styles (highlight box, bold outline, plain), configurable font, size, color, and screen position.
- **Per-word color highlighting** — tap any individual word in the review step to give it its own color (e.g. make "STARVING" pop in red) without affecting the rest of the sentence.
- **20+ FFmpeg transitions** — fade, dissolve, wipe (4 directions), slide (4 directions), circle crop/open/close, zoom, pixelize, blur, and more, applied per-clip-boundary.
- **Logo overlay** — upload a PNG logo, position it in any corner, and scale it.
- **Background music mixing** — upload a track, control its volume, and it's automatically looped/trimmed to match video length and mixed under the original audio.
- **Arabic subtitle support** — automatic RTL reshaping for correct glyph rendering.
- **Async job pipeline** — long-running transcription/render jobs run in background threads with live progress polling (no blocking requests).
- **Memory-efficient model loading** — Whisper model is loaded into RAM only when a job needs it and released immediately after, keeping the app lightweight to host.
- **Review & edit step** — before final render, review auto-generated subtitles, fix any transcription errors, and tune per-word colors.

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python, Flask, Flask-CORS |
| Frontend | React (Vite) |
| Speech-to-Text | OpenAI Whisper (word-level timestamps) |
| Video Processing | FFmpeg, MoviePy, PIL/Pillow |
| Deployment | Railway |

---

## 📐 Architecture

```
┌─────────────┐      REST API       ┌──────────────────┐
│   React UI  │ ─────────────────▶ │   Flask Backend    │
│  (Vite app) │ ◀───────────────── │                     │
└─────────────┘   JSON + polling    │  ┌───────────────┐ │
                                    │  │ Whisper Model │ │
                                    │  │ (lazy loaded) │ │
                                    │  └───────────────┘ │
                                    │  ┌───────────────┐ │
                                    │  │ FFmpeg /      │ │
                                    │  │ MoviePy       │ │
                                    │  │ render engine │ │
                                    │  └───────────────┘ │
                                    └──────────────────┘
```

The frontend uploads media via REST endpoints, kicks off a background job (transcription or render), and polls `/status/<job_id>` for progress until the job completes.

---

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- Node.js 18+
- [FFmpeg](https://ffmpeg.org/download.html) installed and available on your system `PATH`
- ~2–5 GB free disk (for the Whisper model + temp render files)

### Backend Setup

```bash
git clone https://github.com/<Ghufranqayyum>/reelsub-ai.git
cd reelsub-ai/backend

python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

pip install -r requirements.txt

python app.py
```

The API will start on `http://localhost:5000` by default (configurable via the `PORT` env var).

### Frontend Setup

```bash
cd ../frontend
npm install

# create a .env file
echo "VITE_API_URL=http://localhost:5000" > .env

npm run dev
```

Open `http://localhost:5173` in your browser.

### Environment Variables

| Variable | Where | Description |
|---|---|---|
| `PORT` | backend | Port the Flask server runs on |
| `WHISPER_CACHE` | backend | Directory to cache the downloaded Whisper model (e.g. a Railway Volume) |
| `VITE_API_URL` | frontend | Base URL of the backend API |

---

## 📖 Usage

1. **Choose a mode** — Single Long Video or Multiple Clips.
2. **Upload media** — your source video(s), and optionally a logo and background music.
3. **Set segments / order** — trim timestamp ranges (Mode 1) or drag clips into order and pick transitions between them (Mode 2).
4. **Auto-transcribe** — Whisper transcribes speech and generates subtitle cards.
5. **Review & style** — edit subtitle text, recolor individual words, and choose font/size/position/highlight style.
6. **Render** — the backend composites subtitles, logo, and music, then exports the final vertical (1080×1920) MP4.
7. **Download** — grab your finished reel.

---

## 📁 Project Structure

```
reelsub-ai/
├── backend/
│   ├── app.py              # Flask API — upload, transcribe, merge, render endpoints
│   ├── fonts/               # Bundled font files used for subtitle rendering
│   ├── Whisper-model/       # (optional) locally bundled Whisper weights
│   ├── uploads/              # Temp uploads & intermediate render artifacts
│   ├── Outputs/               # Final rendered videos
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.jsx           # Main React app (modes, review UI, style panel)
│   │   └── fonts.css
│   └── package.json
└── README.md
```

---

## 🗺️ Roadmap

- [ ] User accounts & saved project history
- [ ] Cloud storage integration for source media
- [ ] Multi-language transcription UI
- [ ] Template presets for common reel styles
- [ ] GPU-accelerated rendering

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

## 🙋 About

Built by **Ghufran** — AI Engineer & Full-Stack Developer.
https://www.linkedin.com/in/ghufran-qayyum-826456253/ ··ghufranqayyum786@gmail.com
