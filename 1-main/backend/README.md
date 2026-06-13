# Shorts Factory — Backend

The backend pipeline from the implementation blueprint: it turns a raw
phone video into a polished vertical 9:16 clip. Built week by week.

## What's implemented

### Week 1 — The Cutting Room

| Component | File | Role |
|-----------|------|------|
| Sanitizer | `app/sanitizer.py` | VFR->CFR 60fps, rotation bake, H.264/MP4, contrast eq |
| One Euro Filter | `app/one_euro.py` | Smooths the face-tracking signal |
| Face tracker | `app/face_tracker.py` | MediaPipe detection -> smoothed 9:16 crop path (center-crop fallback) |
| Slicer | `app/slicer.py` | Keyframe-aware cuts + concat stitching |

### Week 2 — The Sound Stage

| Component | File | Role |
|-----------|------|------|
| Transcribe | `app/transcribe.py` | faster-whisper word-level timestamps + energy-word flags |
| Captions | `app/captions.py` | Animated 1-3 word ASS captions (neon emphasis), burned in via FFmpeg |
| Beats | `app/beats.py` | librosa beat detection -> beat-synced segment planning |
| Audio mix | `app/audio_mix.py` | Sidechain ducking: music lowered while you speak |

The pipeline (`app/pipeline.py`) wires sanitize -> track -> slice, then the
optional Sound Stage (beat-synced segments, captions, music ducking). The
API lives in `app/main.py`.

> Note: the blueprint specifies YOLOv8 for face tracking. This build uses
> MediaPipe (CPU, no weight downloads) behind a model-agnostic interface so
> YOLOv8 can be swapped in later without touching the slicer.

### Week 3 — The AI Brain

| Component | File | Role |
|-----------|------|------|
| Director | `app/director.py` | Gemini-backed vibe engine (energy/reverence/rhythm) + heuristic fallback |
| Memes | `app/memes.py` | GIPHY/Tenor lookup + FFmpeg chromakey overlay |
| Transitions | `app/transitions.py` | OpenCV optical-flow outfit-change detector, beat-aligned |
| Orchestrator | `app/orchestrator.py` | LangGraph state graph coordinating the 5 agents -> EditPlan |

The agentic path is exposed at `POST /process/agentic`. It degrades
gracefully: without `GEMINI_API_KEY` the Director uses a heuristic, and
without `GIPHY_API_KEY`/`TENOR_API_KEY` memes are skipped.

## Environment variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `WHISPER_MODEL` | `base` | faster-whisper model size (`tiny`/`base`/`small`/...) |
| `WHISPER_DEVICE` | `cpu` | `cpu` or `cuda` |
| `WHISPER_COMPUTE_TYPE` | `int8` | compute type (`int8`, `float16`, ...) |
| `GEMINI_API_KEY` | _(unset)_ | enables Gemini vibe scoring in the Director |
| `GEMINI_MODEL` | `gemini-1.5-flash` | Gemini model id for the Director |
| `GIPHY_API_KEY` | _(unset)_ | enables GIPHY reaction-GIF lookup |
| `TENOR_API_KEY` | _(unset)_ | enables Tenor GIF lookup (fallback) |
| `PORT` | `8080` | server port (set by Cloud Run) |

## Run locally

Requires `ffmpeg` and `ffprobe` on your PATH.

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Basic vertical reel:

```bash
curl -F "file=@raw_clip.mp4" http://localhost:8000/process -o output.mp4
```

Beat-synced + captioned + ducked music:

```bash
curl -F "file=@raw_clip.mp4" \
     -F "music=@trending_song.mp3" \
     -F "captions=true" \
     -F "beats_per_cut=4" \
     http://localhost:8000/process -o output.mp4
```

## Run with Docker (Cloud Run parity)

```bash
cd backend
docker build -t shorts-factory-backend .
docker run -p 8080:8080 shorts-factory-backend
```

### Week 4 — The Red Carpet

| Component | File | Role |
|-----------|------|------|
| Niches | `app/niches.py` | 4 creator profiles (Podcaster/Dancer/Artist/Life Coach) |
| Plan API | `app/api_plan.py` + `POST /plan` | Returns the EditPlan as JSON for the free browser preview |
| Frontend | `../frontend/` | Next.js + Remotion `<Player>` previewing the plan in-browser |
| Deploy | `../deploy/` | Cloud Run service, Cloud Build, GCS 24h lifecycle |

The full creator flow: upload → `POST /plan` → scrub the free Remotion
preview → `POST /process/agentic` to render the final MP4.

See `../frontend/README.md` and `../deploy/README.md` for run/deploy steps.

## Roadmap

All four blueprint weeks are now scaffolded end to end. Next hardening
steps: per-frame animated cropping in the final render, the seamless-loop
editor, and the Instagram Sound ID bridge.
