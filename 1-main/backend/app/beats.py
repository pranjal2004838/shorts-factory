"""Sound agent (Week 2): beat detection and beat-synced segment planning.

Uses librosa to find every beat in an audio/music track. The Slicer then
places cuts on beats so the video feels rhythmic and satisfying. We also
expose a helper that turns a beat grid into a list of Segments whose cut
points land on beats.
"""
from __future__ import annotations

from .slicer import Segment


def detect_beats(audio_path: str) -> list[float]:
    """Return beat timestamps (seconds) for ``audio_path``."""
    import librosa

    y, sr = librosa.load(audio_path, mono=True)
    _tempo, frames = librosa.beat.beat_track(y=y, sr=sr, units="frames")
    times = librosa.frames_to_time(frames, sr=sr)
    return [float(t) for t in times]


def estimate_tempo(audio_path: str) -> float:
    """Return the estimated tempo (BPM) for ``audio_path``."""
    import librosa

    y, sr = librosa.load(audio_path, mono=True)
    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
    return float(tempo)


def beat_synced_segments(
    beats: list[float],
    total_duration: float,
    *,
    beats_per_cut: int = 4,
    min_len: float = 0.6,
) -> list[Segment]:
    """Build segments whose boundaries fall on every ``beats_per_cut`` beat.

    Args:
        beats: sorted beat timestamps.
        total_duration: length of the source clip.
        beats_per_cut: how many beats each segment spans.
        min_len: drop segments shorter than this (avoids flicker cuts).
    """
    if not beats:
        return [Segment(start=0.0, end=total_duration)]

    boundaries = [0.0]
    boundaries += [beats[i] for i in range(0, len(beats), max(1, beats_per_cut))]
    boundaries.append(total_duration)
    boundaries = sorted({round(b, 3) for b in boundaries if 0 <= b <= total_duration})

    segments: list[Segment] = []
    for start, end in zip(boundaries, boundaries[1:]):
        if end - start >= min_len:
            segments.append(Segment(start=start, end=end))
    return segments or [Segment(start=0.0, end=total_duration)]
