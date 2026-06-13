"""Meme agent (Week 3): reaction-GIF lookup + chromakey overlay.

The Meme agent reads emphasised / relatable phrases from the transcript,
fetches a matching reaction GIF from GIPHY (or Tenor as a fallback), removes
any green-screen background with FFmpeg's chromakey filter, and overlays it
on the video at the precise word timestamp.

API keys are read from the environment (GIPHY_API_KEY, TENOR_API_KEY). When
neither is set, lookup returns None and the pipeline simply skips memes.
"""
from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

import requests

from .ffmpeg_utils import run_ffmpeg
from .transcribe import Transcript

_TIMEOUT = 10


@dataclass(frozen=True)
class MemeCue:
    """A meme to overlay: source GIF URL and when to show it."""

    query: str
    start: float
    end: float
    gif_url: str


def _giphy_search(query: str) -> str | None:
    key = os.getenv("GIPHY_API_KEY")
    if not key:
        return None
    resp = requests.get(
        "https://api.giphy.com/v1/gifs/search",
        params={"api_key": key, "q": query, "limit": 1, "rating": "pg-13"},
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json().get("data") or []
    if not data:
        return None
    return data[0]["images"]["original"]["url"]


def _tenor_search(query: str) -> str | None:
    key = os.getenv("TENOR_API_KEY")
    if not key:
        return None
    resp = requests.get(
        "https://tenor.googleapis.com/v2/search",
        params={"key": key, "q": query, "limit": 1},
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    results = resp.json().get("results") or []
    if not results:
        return None
    return results[0]["media_formats"]["gif"]["url"]


def search_gif(query: str) -> str | None:
    """Return a GIF URL for ``query`` from GIPHY, then Tenor, else None."""
    for provider in (_giphy_search, _tenor_search):
        try:
            url = provider(query)
            if url:
                return url
        except Exception:
            continue
    return None


def plan_memes(transcript: Transcript, *, max_memes: int = 3) -> list[MemeCue]:
    """Pick up to ``max_memes`` emphasised moments and find matching GIFs."""
    cues: list[MemeCue] = []
    for w in transcript.words:
        if not w.is_energy:
            continue
        url = search_gif(w.text)
        if url:
            cues.append(
                MemeCue(query=w.text, start=w.start, end=w.start + 1.5, gif_url=url)
            )
        if len(cues) >= max_memes:
            break
    return cues


def _download(url: str, dst: Path) -> Path:
    resp = requests.get(url, timeout=_TIMEOUT)
    resp.raise_for_status()
    dst.write_bytes(resp.content)
    return dst


def overlay_memes(
    video: str | Path,
    cues: list[MemeCue],
    dst: str | Path,
    *,
    chromakey: bool = True,
) -> Path:
    """Overlay each meme GIF onto ``video`` at its timestamp.

    Green backgrounds are removed via the chromakey filter when
    ``chromakey`` is True. Memes float in the top-right quadrant.
    """
    video, dst = Path(video), Path(dst)
    if not cues:
        Path(video).replace(dst)
        return dst

    tmp = Path(tempfile.mkdtemp(prefix="memes_"))
    inputs: list[str] = ["-i", str(video)]
    for idx, cue in enumerate(cues):
        gif = _download(cue.gif_url, tmp / f"meme_{idx}.gif")
        inputs += ["-ignore_loop", "0", "-i", str(gif)]

    filters: list[str] = []
    last = "[0:v]"
    for idx, cue in enumerate(cues, start=1):
        src = f"[{idx}:v]"
        scaled = f"[m{idx}]"
        keyed = f"[k{idx}]"
        out = f"[v{idx}]"
        filters.append(f"{src}scale=320:-1{scaled}")
        if chromakey:
            filters.append(
                f"{scaled}chromakey=0x00FF00:0.30:0.10{keyed}"
            )
        else:
            keyed = scaled
        enable = f"between(t,{cue.start:.3f},{cue.end:.3f})"
        filters.append(
            f"{last}{keyed}overlay=W-w-40:80:enable='{enable}'{out}"
        )
        last = out

    filter_complex = ";".join(filters)
    run_ffmpeg(
        [
            *inputs,
            "-filter_complex",
            filter_complex,
            "-map",
            last,
            "-map",
            "0:a?",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "20",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "copy",
            str(dst),
        ]
    )
    return dst
