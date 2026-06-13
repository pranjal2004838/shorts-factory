"""The Slicer engine: keyframe-aware cutting, cropping and stitching.

The slicer turns an edit plan into a final file. Two responsibilities live
here:

1. Keyframe-aware cuts. You can only cut cleanly on a keyframe; cutting
   between them produces a black flash. ``snap_to_keyframe`` snaps any
   requested cut time to the nearest available keyframe.
2. Stitching. Pre-processed segments are joined with ffmpeg's concat
   demuxer in a single pass for zero quality loss.

The 9:16 crop derived by the face tracker is applied here as a single
representative crop (the median centre) so this first slice renders end to
end; per-frame animated cropping arrives with the Remotion preview later.
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass
from pathlib import Path

from .face_tracker import CropPath
from .ffmpeg_utils import keyframe_timestamps, run_ffmpeg


@dataclass
class Segment:
    """A requested [start, end] slice of the source video, in seconds."""

    start: float
    end: float


def snap_to_keyframe(t: float, keyframes: list[float]) -> float:
    """Snap ``t`` to the nearest keyframe timestamp."""
    if not keyframes:
        return t
    return min(keyframes, key=lambda k: abs(k - t))


def _crop_filter(path: CropPath) -> str:
    """Build a static crop filter from the median tracked centre."""
    center = int(statistics.median(path.centers_x)) if path.centers_x else 0
    x = max(0, center - path.crop_w // 2)
    return f"crop={path.crop_w}:{path.crop_h}:{x}:0"


def _extract_segment(
    src: Path, seg: Segment, crop: str, out: Path, keyframes: list[float]
) -> None:
    start = snap_to_keyframe(seg.start, keyframes)
    duration = max(0.0, seg.end - start)
    run_ffmpeg(
        [
            "-ss",
            f"{start:.3f}",
            "-i",
            str(src),
            "-t",
            f"{duration:.3f}",
            "-vf",
            crop,
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
            str(out),
        ]
    )


def slice_and_stitch(
    src: str | Path,
    segments: list[Segment],
    crop_path: CropPath,
    dst: str | Path,
    workdir: str | Path,
) -> Path:
    """Cut ``segments`` from ``src``, crop to 9:16, and stitch into ``dst``."""
    src, dst, workdir = Path(src), Path(dst), Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    keyframes = keyframe_timestamps(src)
    crop = _crop_filter(crop_path)

    parts: list[Path] = []
    for idx, seg in enumerate(segments):
        part = workdir / f"part_{idx:03d}.mp4"
        _extract_segment(src, seg, crop, part, keyframes)
        parts.append(part)

    if not parts:
        raise ValueError("no segments to stitch")

    if len(parts) == 1:
        parts[0].replace(dst)
        return dst

    concat_list = workdir / "concat.txt"
    concat_list.write_text(
        "".join(f"file '{p.resolve()}'\n" for p in parts), encoding="utf-8"
    )
    run_ffmpeg(
        [
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_list),
            "-c",
            "copy",
            "-movflags",
            "+faststart",
            str(dst),
        ]
    )
    return dst
