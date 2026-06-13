"""Smart audio ducking (Week 2): lower music while the creator speaks.

The blueprint's Sound agent manages mixing so music is loud during quiet
moments and softer when you're speaking. We implement this with FFmpeg's
``sidechaincompress`` filter: the speech track is the sidechain key that
ducks the music bed automatically, then both are mixed back together.
"""
from __future__ import annotations

from pathlib import Path

from .ffmpeg_utils import run_ffmpeg


def duck_and_mix(
    speech_video: str | Path,
    music: str | Path,
    dst: str | Path,
    *,
    music_gain_db: float = -6.0,
) -> Path:
    """Mix ``music`` under the speech of ``speech_video`` with ducking.

    The video stream of ``speech_video`` is copied through untouched; only
    the audio is re-mixed. ``music_gain_db`` sets the baseline music level
    before ducking is applied.
    """
    speech_video, music, dst = Path(speech_video), Path(music), Path(dst)
    # [1:a] music is pre-attenuated, then ducked by the speech key [0:a].
    filter_complex = (
        f"[1:a]volume={music_gain_db}dB[bed];"
        "[bed][0:a]sidechaincompress=threshold=0.03:ratio=8:"
        "attack=5:release=300[ducked];"
        "[ducked][0:a]amix=inputs=2:duration=first:"
        "dropout_transition=0[aout]"
    )
    run_ffmpeg(
        [
            "-i",
            str(speech_video),
            "-i",
            str(music),
            "-filter_complex",
            filter_complex,
            "-map",
            "0:v",
            "-map",
            "[aout]",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "160k",
            "-shortest",
            str(dst),
        ]
    )
    return dst
