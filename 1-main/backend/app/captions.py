"""Caption agent (Week 2): animated 1-3 word captions via ASS + FFmpeg.

Research in the blueprint says showing only 1-3 words at a time, animated,
keeps viewers actively reading and lifts watch time. We build an Advanced
SubStation Alpha (ASS) subtitle file with pysubs2: normal words get a clean
pop, high-energy words get a larger neon style with a bounce. The ASS file
is then burned into the video with FFmpeg's subtitles filter.
"""
from __future__ import annotations

from pathlib import Path

import pysubs2

from .ffmpeg_utils import run_ffmpeg
from .transcribe import Transcript, Word

MAX_WORDS_PER_CUE = 3
# Max silent gap (s) within which words are grouped into one caption cue.
_GROUP_GAP = 0.45


def _group_words(words: list[Word]) -> list[list[Word]]:
    """Group consecutive words into cues of at most MAX_WORDS_PER_CUE."""
    groups: list[list[Word]] = []
    current: list[Word] = []
    for w in words:
        if current:
            gap = w.start - current[-1].end
            if len(current) >= MAX_WORDS_PER_CUE or gap > _GROUP_GAP:
                groups.append(current)
                current = []
        current.append(w)
    if current:
        groups.append(current)
    return groups


def _build_styles() -> pysubs2.SSAFile:
    subs = pysubs2.SSAFile()
    subs.info["PlayResX"] = "1080"
    subs.info["PlayResY"] = "1920"

    base = pysubs2.SSAStyle(
        fontname="Montserrat",
        fontsize=96,
        bold=True,
        primarycolor=pysubs2.Color(255, 255, 255),
        outlinecolor=pysubs2.Color(0, 0, 0),
        outline=6,
        shadow=0,
        alignment=pysubs2.Alignment.BOTTOM_CENTER,
        marginv=320,
    )
    energy = pysubs2.SSAStyle(
        fontname="Montserrat",
        fontsize=120,
        bold=True,
        primarycolor=pysubs2.Color(255, 234, 0),  # neon yellow
        outlinecolor=pysubs2.Color(0, 0, 0),
        outline=8,
        shadow=0,
        alignment=pysubs2.Alignment.BOTTOM_CENTER,
        marginv=320,
    )
    subs.styles["Base"] = base
    subs.styles["Energy"] = energy
    return subs


def _cue_text(group: list[Word]) -> tuple[str, str]:
    """Return (style_name, ass_text) for a word group.

    A pop/scale-in animation is applied via the \\fad and \\t transform
    tags. Energy groups bounce slightly larger.
    """
    has_energy = any(w.is_energy for w in group)
    style = "Energy" if has_energy else "Base"
    text = " ".join(w.text for w in group).upper()
    # Fade in 60ms; scale from 80% -> 100% over 120ms for a pop.
    anim = r"{\fad(60,40)\fscx80\fscy80\t(0,120,\fscx100\fscy100)}"
    return style, anim + text


def build_ass(transcript: Transcript, dst: str | Path) -> Path:
    """Write an animated ASS caption file for ``transcript``."""
    dst = Path(dst)
    subs = _build_styles()
    for group in _group_words(transcript.words):
        if not group:
            continue
        style, text = _cue_text(group)
        subs.append(
            pysubs2.SSAEvent(
                start=int(group[0].start * 1000),
                end=int(group[-1].end * 1000),
                style=style,
                text=text,
            )
        )
    subs.save(str(dst))
    return dst


def burn_in(video: str | Path, ass: str | Path, dst: str | Path) -> Path:
    """Burn an ASS subtitle file into ``video`` -> ``dst``."""
    video, ass, dst = Path(video), Path(ass), Path(dst)
    # Escape the path for the subtitles filter (colons/backslashes).
    ass_arg = str(ass).replace("\\", "/").replace(":", "\\:")
    run_ffmpeg(
        [
            "-i",
            str(video),
            "-vf",
            f"subtitles='{ass_arg}'",
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
