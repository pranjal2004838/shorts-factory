"""Thin wrappers around the ffmpeg / ffprobe binaries.

We shell out to ffmpeg directly (rather than a Python binding) because the
blueprint's pipeline relies on specific filter chains and concat behaviour
that are easiest to express on the command line and easiest to debug.
"""
from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path


class FFmpegError(RuntimeError):
    """Raised when an ffmpeg/ffprobe invocation fails."""


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise FFmpegError(
            f"command failed ({proc.returncode}): {' '.join(cmd)}\n{proc.stderr}"
        )
    return proc


@dataclass(frozen=True)
class VideoInfo:
    """Subset of probe data the pipeline cares about."""

    width: int
    height: int
    duration: float
    rotation: int
    avg_fps: float
    codec: str


def probe(path: str | Path) -> VideoInfo:
    """Return basic metadata for the first video stream."""
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_streams",
        "-show_format",
        "-of",
        "json",
        str(path),
    ]
    data = json.loads(_run(cmd).stdout)
    stream = (data.get("streams") or [{}])[0]
    fmt = data.get("format", {})

    num, _, den = (stream.get("avg_frame_rate") or "0/1").partition("/")
    den_val = float(den) if den and float(den) != 0 else 1.0
    avg_fps = float(num) / den_val if num else 0.0

    rotation = 0
    for sd in stream.get("side_data_list", []) or []:
        if "rotation" in sd:
            rotation = int(sd["rotation"])
    tag_rot = (stream.get("tags") or {}).get("rotate")
    if tag_rot is not None:
        rotation = int(tag_rot)

    return VideoInfo(
        width=int(stream.get("width", 0)),
        height=int(stream.get("height", 0)),
        duration=float(fmt.get("duration", 0.0) or 0.0),
        rotation=rotation % 360,
        avg_fps=avg_fps,
        codec=str(stream.get("codec_name", "")),
    )


def keyframe_timestamps(path: str | Path) -> list[float]:
    """Return the presentation timestamps (seconds) of all keyframes."""
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-skip_frame",
        "nokey",
        "-show_entries",
        "frame=best_effort_timestamp_time",
        "-of",
        "csv=print_section=0",
        str(path),
    ]
    out = _run(cmd).stdout
    stamps: list[float] = []
    for line in out.splitlines():
        line = line.strip().rstrip(",")
        if not line:
            continue
        try:
            stamps.append(float(line))
        except ValueError:
            continue
    return sorted(stamps)


def run_ffmpeg(args: list[str]) -> None:
    """Run ffmpeg with -y and the given args (excluding the binary name)."""
    _run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", *args])
