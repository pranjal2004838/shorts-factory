"""Helper that builds an EditPlan and returns its JSON form.

The browser preview (Remotion) calls this before any paid cloud render so
the creator can scrub the timeline for free. We sanitize first so the
preview matches what the renderer will actually produce.
"""
from __future__ import annotations

from pathlib import Path

from .ffmpeg_utils import probe
from .niches import profile_for
from .orchestrator import build_edit_plan
from .sanitizer import sanitize


def build_plan_json(
    src: str | Path,
    workdir: str | Path,
    *,
    music: str | Path | None = None,
    niche: str | None = None,
) -> dict:
    """Sanitize ``src``, run the agents, and return the EditPlan as JSON."""
    src, workdir = Path(src), Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)

    info = probe(src)
    sanitized = sanitize(src, workdir / "sanitized.mp4", info=info)
    plan = build_edit_plan(sanitized, workdir / "plan", Path(music) if music else None)

    payload = plan.to_dict()
    profile = profile_for(niche)
    payload["niche"] = niche
    payload["caption_style"] = profile.caption_style if profile else "hype"
    payload["duration"] = info.duration
    return payload
