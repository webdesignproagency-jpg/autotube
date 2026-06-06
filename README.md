# AutoTube Pipeline

A 13-layer fully automated YouTube channel system.
React frontend + FastAPI backend. 100% local, 100% free.

---

## 🚀 Quick Start

### 1. Prerequisites
- Python 3.11+
- Node.js 18+
- [Ollama](https://ollama.ai) running locally with `qwen2.5:14b` and `llama3:8b`
- [ComfyUI](https://github.com/comfyanonymous/ComfyUI) running on port 8188 with Wan 2.1 + Flux.1 Schnell models
- FFmpeg installed (`brew install ffmpeg` or `apt install ffmpeg`)
- Google Cloud project with YouTube Data API v3 + YouTube Analytics API enabled

### 2. Backend setup
```bash
cd backend
cp .env.example .env
# Fill in your Google credentials in .env

pip install -r requirements.txt

# Pull Ollama models
ollama pull qwen2.5:14b
ollama pull llama3:8b

# Create ambient music folder and add some .mp3 files
mkdir -p ambient_music  # add royalty-free spooky tracks here
mkdir -p temp_render output

python main.py
# Backend runs on http://localhost:8000
```

### 3. Frontend setup
```bash
cd frontend
npm install
npm run dev
# Frontend runs on http://localhost:3000
```

### 4. Connect your YouTube channel
1. Go to http://localhost:3000
2. Click "Connect channel"
3. Complete Google OAuth — your tokens are saved locally in production_vault.db

---

## 🏗 Architecture

```
AutoTube/
├── backend/
│   ├── main.py                    # FastAPI app + WebSocket + pipeline orchestrator
│   ├── requirements.txt
│   ├── .env.example
│   ├── models/
│   │   └── schemas.py             # Pydantic models for all layers
│   ├── db/
│   │   └── vault.py               # SQLite async database
│   └── layers/
│       ├── layer01_trend_scraper.py
│       ├── layer02_duplicate_auditor.py
│       ├── layer03_seo_planner.py
│       ├── layer04_hook_architect.py
│       ├── layer05_script_continuum.py
│       ├── layer06_prompt_director.py
│       ├── layer07_video_render.py
│       ├── layer08_voice_engineer.py
│       ├── layer09_master_editor.py
│       ├── layer10_evidence_auditor.py
│       ├── layer11_thumbnail_artist.py
│       ├── layer12_publisher.py
│       └── layer13_channel_analyzer.py  ← runs first, routes improvements
│
└── frontend/
    ├── package.json
    ├── vite.config.js
    ├── index.html
    └── src/
        ├── main.jsx
        ├── App.jsx                # Full dashboard with WebSocket live updates
        └── index.css
```

---

## 🔄 Pipeline Flow

```
L13 Channel Analyzer (runs first — audits your channel)
         ↓ routes improvements to →  L3, L4, L11
L1  Trend Scraper
L2  Duplicate Auditor  
L3  SEO Planner  ← may receive L13 instruction
L4  Hook Architect  ← may receive L13 instruction
L5  Script Continuum
L6  Prompt Director
L7  Video Render (ComfyUI + Wan 2.1)
L8  Voice Engineer (Kokoro-82M)
L9  Master Editor (FFmpeg)
L10 QC Gate (auto re-renders bad scenes)
L11 Thumbnail Artist (Flux.1 Schnell)  ← may receive L13 instruction
L12 Publisher → Human approval dashboard
         ↓
   [Upload] [Save] [Redo] [Cancel]
```

---

## ⚙️ WebSocket Events

| Event | Direction | Payload |
|-------|-----------|---------|
| `pipeline_start` | server→client | `{message}` |
| `layer_update` | server→client | `{layer, status, message, data}` |
| `pipeline_complete` | server→client | `{topic, title, reroutes_applied}` |
| `uploaded` | server→client | `{url}` |
| `state_sync` | server→client | current state on connect |

---

## 📡 REST API

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/pipeline/start` | Trigger pipeline manually |
| GET | `/api/pipeline/status` | Current pipeline state |
| POST | `/api/pipeline/approve` | Approval action: upload/save/redo/cancel |
| GET | `/api/channel/analysis` | Latest L13 channel analysis |
| GET | `/auth/youtube` | Get OAuth URL |
| GET | `/auth/callback` | OAuth callback |

---

## 🎵 Ambient Music
Place royalty-free `.mp3` or `.wav` files in `backend/ambient_music/`.
Recommended sources: FreeMusicArchive.org, Pixabay Music (CC0 licensed).

---

## 📝 Notes
- The pipeline auto-runs every 12 hours via APScheduler cron.
- All video data is tracked in `production_vault.db` (SQLite).
- Duplicate detection uses TheFuzz with a 75% similarity threshold.
- QC gate automatically re-renders failed scenes without crashing.
- Layer 13 runs before every pipeline run — no separate trigger needed.
