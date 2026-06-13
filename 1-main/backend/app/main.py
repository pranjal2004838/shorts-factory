"""FastAPI entrypoint for the Shorts Factory backend.

Exposes:
* ``/process``        — deterministic Weeks 1-2 pipeline.
* ``/process/agentic`` — Week 3 LangGraph 5-agent pipeline (Director, Steno,
  Sound, Visual, Meme, Caption) producing an EditPlan, then rendering it.

Designed to run on GCP Cloud Run.
"""
from __future__ import annotations

import shutil
import tempfile
import uuid
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from fastapi.middleware.cors import CORSMiddleware

from .api_plan import build_plan_json
from .pipeline import process_video, process_video_agentic

app = FastAPI(title="Shorts Factory", version="0.4.0")

# The Next.js preview runs in the browser and calls these endpoints.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


def _save_upload(upload: UploadFile, workdir: Path) -> Path:
    dst = workdir / (upload.filename or uuid.uuid4().hex)
    with dst.open("wb") as fh:
        shutil.copyfileobj(upload.file, fh)
    return dst


def _new_workdir() -> Path:
    wd = Path(tempfile.gettempdir()) / f"sf_{uuid.uuid4().hex}"
    wd.mkdir(parents=True, exist_ok=True)
    return wd


def _result_headers(result) -> dict[str, str]:
    headers = {
        "X-Used-Center-Crop-Fallback": str(result.used_center_crop_fallback),
        "X-Captioned": str(result.captioned),
        "X-Beat-Synced": str(result.beat_synced),
        "X-Music-Ducked": str(result.music_ducked),
        "X-Memes-Added": str(result.memes_added),
        "X-Duration": f"{result.duration:.3f}",
        "X-FPS": f"{result.fps:.3f}",
    }
    if result.vibe:
        headers["X-Vibe"] = (
            f"energy={result.vibe['energy']},"
            f"reverence={result.vibe['reverence']},"
            f"rhythm={result.vibe['rhythm_dependency']}"
        )
    return headers


@app.post("/process")
async def process(
    file: UploadFile = File(...),
    music: UploadFile | None = File(default=None),
    captions: bool = Form(default=False),
    beats_per_cut: int = Form(default=4),
) -> FileResponse:
    """Deterministic pipeline (Weeks 1-2)."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="missing filename")

    workdir = _new_workdir()
    raw = _save_upload(file, workdir)
    music_path = _save_upload(music, workdir) if music is not None else None

    try:
        result = process_video(
            raw,
            workdir,
            music=music_path,
            captions=captions,
            beats_per_cut=beats_per_cut,
        )
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return FileResponse(
        path=result.output_path,
        media_type="video/mp4",
        filename="shorts_factory_output.mp4",
        headers=_result_headers(result),
    )


@app.post("/process/agentic")
async def process_agentic(
    file: UploadFile = File(...),
    music: UploadFile | None = File(default=None),
) -> FileResponse:
    """Week 3 agentic pipeline: 5-agent orchestration -> EditPlan -> render."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="missing filename")

    workdir = _new_workdir()
    raw = _save_upload(file, workdir)
    music_path = _save_upload(music, workdir) if music is not None else None

    try:
        result = process_video_agentic(raw, workdir, music=music_path)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return FileResponse(
        path=result.output_path,
        media_type="video/mp4",
        filename="shorts_factory_output.mp4",
        headers=_result_headers(result),
    )


@app.post("/plan")
async def plan(
    file: UploadFile = File(...),
    music: UploadFile | None = File(default=None),
    niche: str | None = Form(default=None),
) -> dict:
    """Return the AI EditPlan as JSON for the free browser preview."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="missing filename")

    workdir = _new_workdir()
    raw = _save_upload(file, workdir)
    music_path = _save_upload(music, workdir) if music is not None else None

    try:
        return build_plan_json(raw, workdir, music=music_path, niche=niche)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
