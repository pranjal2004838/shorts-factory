"""Steno agent (Week 2): word-level transcription via faster-whisper.

Produces a precise map of every spoken word and the exact millisecond it
was said. Each word is also flagged as "energy" (emphasised) using a small
heuristic so the caption engine can style hype words differently.

The model is loaded lazily and cached so repeated calls in a long-running
process (e.g. Cloud Run) don't reload weights.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from functools import lru_cache

# Words that almost always carry vocal emphasis in short-form content.
_ENERGY_LEXICON = {
    "insane", "crazy", "never", "always", "changed", "best", "worst",
    "huge", "massive", "boom", "wow", "stop", "wait", "actually",
    "literally", "everything", "nothing", "finally", "secret", "viral",
}


@dataclass(frozen=True)
class Word:
    """A single transcribed word with timing and emphasis flag."""

    text: str
    start: float
    end: float
    is_energy: bool


@dataclass(frozen=True)
class Transcript:
    words: list[Word]

    @property
    def text(self) -> str:
        return " ".join(w.text for w in self.words)


def _is_energy_word(text: str) -> bool:
    cleaned = re.sub(r"[^a-z]", "", text.lower())
    if not cleaned:
        return False
    if cleaned in _ENERGY_LEXICON:
        return True
    # ALL-CAPS or trailing exclamation is a strong emphasis signal.
    return text.isupper() and len(cleaned) >= 3


@lru_cache(maxsize=2)
def _load_model(model_size: str, device: str, compute_type: str):
    from faster_whisper import WhisperModel

    return WhisperModel(model_size, device=device, compute_type=compute_type)


def transcribe(audio_or_video: str) -> Transcript:
    """Transcribe ``audio_or_video`` to word-level timestamps.

    Honours the env vars WHISPER_MODEL (default ``base``),
    WHISPER_DEVICE (default ``cpu``) and WHISPER_COMPUTE_TYPE
    (default ``int8``).
    """
    model = _load_model(
        os.getenv("WHISPER_MODEL", "base"),
        os.getenv("WHISPER_DEVICE", "cpu"),
        os.getenv("WHISPER_COMPUTE_TYPE", "int8"),
    )
    segments, _info = model.transcribe(
        audio_or_video, word_timestamps=True, vad_filter=True
    )

    words: list[Word] = []
    for seg in segments:
        for w in seg.words or []:
            text = w.word.strip()
            if not text:
                continue
            words.append(
                Word(
                    text=text,
                    start=float(w.start),
                    end=float(w.end),
                    is_energy=_is_energy_word(text),
                )
            )
    return Transcript(words=words)
