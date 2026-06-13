"""The Sanitizer engine: the "washing machine" for raw phone video.

Raw phone clips carry hidden problems that break downstream editing:
variable frame rate, rotation metadata, bad exposure and exotic codecs.
The sanitizer normalises every input into a predictable shape:

* constant 60fps (fixes VFR audio drift)
* rotation baked into pixels (no orientation metadata surprises)
* H.264 / MP4 (universally readable)
* optional contrast equalization for face detection
"""
from __future__ import annotations

from pathlib import Path

from .ffmpeg_utils import VideoInfo, probe, run_ffmpeg

TARGET_FPS = 60


def _rotation_filter(rotation: int) -> str | None:
    """Map a rotation tag to a transpose/hflip filter chain."""
    rotation %= 360
    if rotation == 90:
        return "transpose=1"
    if rotation == 180:
        return "transpose=2,transpose=2"
    if rotation == 270:
        return "transpose=2"
    return None


def sanitize(
    src: str | Path,
    dst: str | Path,
    *,
    equalize: bool = True,
    info: VideoInfo | None = None,
) -> Path:
    """Normalise ``src`` and write the cleaned file to ``dst``.

    Returns the path to the sanitized file.
    """
    src, dst = Path(src), Path(dst)
    info = info or probe(src)

    filters: list[str] = []
    rot = _rotation_filter(info.rotation)
    if rot:
        filters.append(rot)
    if equalize:
        # Gentle, perceptually safe contrast lift to help face detection.
        filters.append("eq=contrast=1.05:brightness=0.02:saturation=1.05")
    # Force constant frame rate to kill VFR audio drift.
    filters.append(f"fps={TARGET_FPS}")

    args = ["-i", str(src), "-vf", ",".join(filters)]
    # Strip stale rotation metadata now that we baked it into pixels.
    args += ["-metadata:s:v:0", "rotate=0"]
    args += [
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "20",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-movflags",
        "+faststart",
        str(dst),
    ]
    run_ffmpeg(args)
    return dst
