"""The 4 creator niches (Week 4).

Each niche tunes how the agent EditPlan is built and rendered. The niche
doesn't replace the agents — it biases them, exactly as the blueprint
describes (e.g. the Life Coach trims filler, the Dancer aligns an
outfit-change transition to a beat drop).
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Niche(str, Enum):
    PODCASTER = "podcaster"
    DANCER = "dancer"
    ARTIST = "artist"
    LIFE_COACH = "life_coach"


@dataclass(frozen=True)
class NicheProfile:
    """Knobs the pipeline reads when a niche is selected."""

    beats_per_cut: int
    trim_filler: bool
    speedup_static: bool
    detect_outfit_change: bool
    prefer_memes: bool
    caption_style: str  # "hype" or "elegant"


_PROFILES: dict[Niche, NicheProfile] = {
    Niche.PODCASTER: NicheProfile(
        beats_per_cut=8,
        trim_filler=True,
        speedup_static=False,
        detect_outfit_change=False,
        prefer_memes=True,
        caption_style="hype",
    ),
    Niche.DANCER: NicheProfile(
        beats_per_cut=2,
        trim_filler=False,
        speedup_static=False,
        detect_outfit_change=True,
        prefer_memes=False,
        caption_style="hype",
    ),
    Niche.ARTIST: NicheProfile(
        beats_per_cut=4,
        trim_filler=False,
        speedup_static=True,
        detect_outfit_change=False,
        prefer_memes=False,
        caption_style="elegant",
    ),
    Niche.LIFE_COACH: NicheProfile(
        beats_per_cut=6,
        trim_filler=True,
        speedup_static=False,
        detect_outfit_change=False,
        prefer_memes=False,
        caption_style="elegant",
    ),
}


def profile_for(niche: Niche | str | None) -> NicheProfile | None:
    """Return the profile for a niche, or None when unspecified."""
    if niche is None:
        return None
    if isinstance(niche, str):
        try:
            niche = Niche(niche)
        except ValueError:
            return None
    return _PROFILES[niche]
