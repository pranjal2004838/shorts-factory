"""Layer 0: The Director (context & vibe engine).

The Director watches the clip's transcript and audio profile and produces a
continuous "vibe" rather than a hardcoded mood. It measures three sliders:

* energy (0-10): how hype / fast the content is,
* reverence (0-10): serious/sad/sacred vs. comedic,
* rhythm_dependency (0-10): how much the edit should lean on beat drops.

These sliders set the rules other agents follow (e.g. high reverence
disables memes and bouncy text). When a Gemini API key is present we ask
Gemini to score the vibe; otherwise we fall back to a deterministic
heuristic so the pipeline always runs offline.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass

from .transcribe import Transcript


@dataclass(frozen=True)
class Vibe:
    energy: float
    reverence: float
    rhythm_dependency: float

    @property
    def allow_memes(self) -> bool:
        return self.reverence < 6.0 and self.energy >= 3.0

    @property
    def allow_flash_transitions(self) -> bool:
        return self.rhythm_dependency >= 5.0 and self.reverence < 7.0

    @property
    def bouncy_captions(self) -> bool:
        return self.energy >= 5.0 and self.reverence < 6.0


def _heuristic_vibe(transcript: Transcript, tempo: float | None) -> Vibe:
    words = transcript.words
    if not words:
        return Vibe(energy=5.0, reverence=5.0, rhythm_dependency=5.0)
    duration = max(1e-6, words[-1].end - words[0].start)
    wpm = len(words) / duration * 60.0
    energy_ratio = sum(1 for w in words if w.is_energy) / len(words)

    energy = min(10.0, wpm / 30.0 + energy_ratio * 20.0)
    # Slower, sparse speech reads as more reverent.
    reverence = max(0.0, 8.0 - energy)
    rhythm = 5.0 if tempo is None else min(10.0, max(2.0, tempo / 18.0))
    return Vibe(
        energy=round(energy, 2),
        reverence=round(reverence, 2),
        rhythm_dependency=round(rhythm, 2),
    )


def _gemini_vibe(transcript: Transcript, tempo: float | None) -> Vibe | None:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI

        model = ChatGoogleGenerativeAI(
            model=os.getenv("GEMINI_MODEL", "gemini-1.5-flash"),
            google_api_key=api_key,
            temperature=0.2,
        )
        prompt = (
            "You score short-form video vibe. Given the transcript and tempo, "
            "return ONLY compact JSON with float fields energy, reverence, "
            "rhythm_dependency, each 0-10.\n"
            f"tempo_bpm: {tempo}\n"
            f"transcript: {transcript.text[:4000]}"
        )
        raw = model.invoke(prompt).content
        if isinstance(raw, list):
            raw = "".join(str(p) for p in raw)
        start, end = raw.find("{"), raw.rfind("}")
        data = json.loads(raw[start : end + 1])
        return Vibe(
            energy=float(data["energy"]),
            reverence=float(data["reverence"]),
            rhythm_dependency=float(data["rhythm_dependency"]),
        )
    except Exception:
        # Any failure (network, quota, parse) falls back to the heuristic.
        return None


def assess_vibe(transcript: Transcript, tempo: float | None = None) -> Vibe:
    """Return the clip's vibe, preferring Gemini when configured."""
    return _gemini_vibe(transcript, tempo) or _heuristic_vibe(transcript, tempo)
