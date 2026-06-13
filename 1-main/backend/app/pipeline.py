"""Pipeline orchestration: deterministic Week 1/2 path + agentic Week 3 path.

* ``process_video`` — the explicit sanitize -> track -> slice (+ Sound
  Stage) flow from Weeks 1-2.
* ``process_video_agentic`` — runs the LangGraph 5-agent orchestrator
  (Week 3) to build an EditPlan, then renders captions, beat-synced cuts,
  memes and music ducking from that plan.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .audio_mix import duck_and_mix
from .beats import beat_synced_segments, detect_beats
from .captions import build_ass, burn_in
from .face_tracker import compute_crop_path
from .ffmpeg_utils import probe
from .memes import overlay_memes
from .orchestrator import EditPlan, build_edit_plan
from .sanitizer import sanitize
from .slicer import Segment, slice_and_stitch
from .transcribe import transcribe


@dataclass
class PipelineResult:
    output_path: Path
    duration: float
    fps: float
    used_center_crop_fallback: bool
    captioned: bool = False
    beat_synced: bool = False
    music_ducked: bool = False
    memes_added: int = 0
    vibe: dict[str, float] | None = None
    segments: list[Segment] = field(default_factory=list)


def process_video(
    src: str | Path,
    workdir: str | Path,
    *,
    segments: list[Segment] | None = None,
    music: str | Path | None = None,
    captions: bool = False,
    beats_per_cut: int = 4,
) -> PipelineResult:
    """Deterministic Weeks 1-2 pipeline."""
    src, workdir = Path(src), Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)

    info = probe(src)
    sanitized = sanitize(src, workdir / "sanitized.mp4", info=info)

    clean_info = probe(sanitized)
    crop_path = compute_crop_path(str(sanitized), fps=clean_info.avg_fps or 60.0)

    beat_synced = False
    if segments is None and music is not None:
        beats = detect_beats(str(music))
        segments = beat_synced_segments(
            beats, clean_info.duration, beats_per_cut=beats_per_cut
        )
        beat_synced = True
    if not segments:
        segments = [Segment(start=0.0, end=clean_info.duration)]

    current = slice_and_stitch(
        sanitized,
        segments,
        crop_path,
        workdir / "sliced.mp4",
        workdir / "segments",
    )

    captioned = False
    if captions:
        transcript = transcribe(str(current))
        if transcript.words:
            ass = build_ass(transcript, workdir / "captions.ass")
            current = burn_in(current, ass, workdir / "captioned.mp4")
            captioned = True

    music_ducked = False
    if music is not None:
        current = duck_and_mix(current, music, workdir / "mixed.mp4")
        music_ducked = True

    output = workdir / "output.mp4"
    Path(current).replace(output)

    return PipelineResult(
        output_path=output,
        duration=clean_info.duration,
        fps=clean_info.avg_fps,
        used_center_crop_fallback=crop_path.fell_back,
        captioned=captioned,
        beat_synced=beat_synced,
        music_ducked=music_ducked,
        segments=segments,
    )


def _render_from_plan(
    sanitized: Path, plan: EditPlan, music: Path | None, workdir: Path
) -> tuple[Path, bool, int]:
    """Render a final video from an agent-produced EditPlan."""
    current = slice_and_stitch(
        sanitized,
        plan.segments,
        plan.crop_path,
        workdir / "sliced.mp4",
        workdir / "segments",
    )

    captioned = False
    if plan.ass_path is not None:
        current = burn_in(current, plan.ass_path, workdir / "captioned.mp4")
        captioned = True

    memes_added = 0
    if plan.meme_cues:
        current = overlay_memes(current, plan.meme_cues, workdir / "memed.mp4")
        memes_added = len(plan.meme_cues)

    if music is not None:
        current = duck_and_mix(current, music, workdir / "mixed.mp4")

    return Path(current), captioned, memes_added


def process_video_agentic(
    src: str | Path,
    workdir: str | Path,
    *,
    music: str | Path | None = None,
) -> PipelineResult:
    """Week 3 agentic pipeline: orchestrate agents -> EditPlan -> render."""
    src, workdir = Path(src), Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)

    info = probe(src)
    sanitized = sanitize(src, workdir / "sanitized.mp4", info=info)
    clean_info = probe(sanitized)
    music_path = Path(music) if music else None

    plan = build_edit_plan(sanitized, workdir / "plan", music_path)
    current, captioned, memes_added = _render_from_plan(
        sanitized, plan, music_path, workdir
    )

    output = workdir / "output.mp4"
    Path(current).replace(output)

    return PipelineResult(
        output_path=output,
        duration=clean_info.duration,
        fps=clean_info.avg_fps,
        used_center_crop_fallback=plan.crop_path.fell_back,
        captioned=captioned,
        beat_synced=music_path is not None,
        music_ducked=music_path is not None,
        memes_added=memes_added,
        vibe={
            "energy": plan.vibe.energy,
            "reverence": plan.vibe.reverence,
            "rhythm_dependency": plan.vibe.rhythm_dependency,
        },
        segments=plan.segments,
    )
