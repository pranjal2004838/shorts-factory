"""The AI Brain (Week 3): LangGraph 5-agent orchestrator.

Instead of one monolithic model, a state graph coordinates specialised
agents — exactly the "band + conductor" model from the blueprint:

* Director  — assesses the clip's vibe (sets the rules for everyone else)
* Steno     — word-level transcription
* Sound     — beat detection + tempo
* Visual    — 9:16 face-tracking crop path
* Meme      — reaction-GIF cues (gated by the vibe)
* Caption   — animated caption file (gated by the vibe)

The graph produces an ``EditPlan`` that the renderer consumes. The graph
degrades gracefully: if LangGraph isn't importable we run the same nodes
sequentially, so the pipeline always works.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, TypedDict

from .beats import beat_synced_segments, detect_beats, estimate_tempo
from .captions import build_ass
from .director import Vibe, assess_vibe
from .face_tracker import CropPath, compute_crop_path
from .ffmpeg_utils import probe
from .memes import MemeCue, plan_memes
from .slicer import Segment
from .transcribe import Transcript, transcribe
from .transitions import detect_transitions


@dataclass
class EditPlan:
    """The complete creative plan emitted by the agent graph."""

    vibe: Vibe
    segments: list[Segment]
    crop_path: CropPath
    transcript: Transcript
    meme_cues: list[MemeCue] = field(default_factory=list)
    transitions: list[float] = field(default_factory=list)
    ass_path: Path | None = None

    def to_dict(self) -> dict:
        """Serialise the plan for the browser preview (Remotion)."""
        return {
            "vibe": {
                "energy": self.vibe.energy,
                "reverence": self.vibe.reverence,
                "rhythm_dependency": self.vibe.rhythm_dependency,
            },
            "crop": {
                "width": self.crop_path.crop_w,
                "height": self.crop_path.crop_h,
                "fps": self.crop_path.fps,
                "centers_x": self.crop_path.centers_x,
            },
            "segments": [
                {"start": s.start, "end": s.end} for s in self.segments
            ],
            "words": [
                {
                    "text": w.text,
                    "start": w.start,
                    "end": w.end,
                    "energy": w.is_energy,
                }
                for w in self.transcript.words
            ],
            "memes": [
                {
                    "query": m.query,
                    "start": m.start,
                    "end": m.end,
                    "gif_url": m.gif_url,
                }
                for m in self.meme_cues
            ],
            "transitions": self.transitions,
        }


class _State(TypedDict, total=False):
    video: str
    music: str | None
    workdir: str
    duration: float
    fps: float
    transcript: Transcript
    beats: list[float]
    tempo: float
    vibe: Vibe
    crop_path: CropPath
    segments: list[Segment]
    meme_cues: list[MemeCue]
    transitions: list[float]
    ass_path: str | None


def _node_probe(state: _State) -> dict[str, Any]:
    info = probe(state["video"])
    return {"duration": info.duration, "fps": info.avg_fps or 60.0}


def _node_steno(state: _State) -> dict[str, Any]:
    return {"transcript": transcribe(state["video"])}


def _node_sound(state: _State) -> dict[str, Any]:
    music = state.get("music")
    if not music:
        return {"beats": [], "tempo": 0.0}
    return {"beats": detect_beats(music), "tempo": estimate_tempo(music)}


def _node_visual(state: _State) -> dict[str, Any]:
    return {"crop_path": compute_crop_path(state["video"], fps=state["fps"])}


def _node_director(state: _State) -> dict[str, Any]:
    tempo = state.get("tempo") or None
    vibe = assess_vibe(state["transcript"], tempo)
    beats = state.get("beats") or []
    if beats:
        segments = beat_synced_segments(beats, state["duration"])
    else:
        segments = [Segment(start=0.0, end=state["duration"])]
    return {"vibe": vibe, "segments": segments}


def _node_meme(state: _State) -> dict[str, Any]:
    vibe = state["vibe"]
    if not vibe.allow_memes:
        return {"meme_cues": []}
    return {"meme_cues": plan_memes(state["transcript"])}


def _node_caption(state: _State) -> dict[str, Any]:
    transcript = state["transcript"]
    if not transcript.words:
        return {"ass_path": None}
    ass = Path(state["workdir"]) / "captions.ass"
    build_ass(transcript, ass)
    return {"ass_path": str(ass)}


def _node_transitions(state: _State) -> dict[str, Any]:
    if not state["vibe"].allow_flash_transitions:
        return {"transitions": []}
    return {
        "transitions": detect_transitions(state["video"], state.get("beats") or [])
    }


def _run_sequential(state: _State) -> _State:
    """Fallback execution path when LangGraph is unavailable."""
    state.update(_node_probe(state))
    state.update(_node_steno(state))
    state.update(_node_sound(state))
    state.update(_node_visual(state))
    state.update(_node_director(state))
    state.update(_node_meme(state))
    state.update(_node_caption(state))
    state.update(_node_transitions(state))
    return state


def _build_graph():
    from langgraph.graph import END, START, StateGraph

    g = StateGraph(_State)
    g.add_node("probe", _node_probe)
    g.add_node("steno", _node_steno)
    g.add_node("sound", _node_sound)
    g.add_node("visual", _node_visual)
    g.add_node("director", _node_director)
    g.add_node("meme", _node_meme)
    g.add_node("caption", _node_caption)
    g.add_node("transitions", _node_transitions)

    # Probe first, then the perception agents run, then the Director sets
    # rules, then the gated creative agents.
    g.add_edge(START, "probe")
    for n in ("steno", "sound", "visual"):
        g.add_edge("probe", n)
        g.add_edge(n, "director")
    g.add_edge("director", "meme")
    g.add_edge("director", "caption")
    g.add_edge("director", "transitions")
    for n in ("meme", "caption", "transitions"):
        g.add_edge(n, END)
    return g.compile()


def build_edit_plan(
    video: str | Path, workdir: str | Path, music: str | Path | None = None
) -> EditPlan:
    """Run the agent graph and return a complete EditPlan."""
    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    state: _State = {
        "video": str(video),
        "music": str(music) if music else None,
        "workdir": str(workdir),
    }

    try:
        compiled = _build_graph()
        result = dict(compiled.invoke(state))
    except Exception:
        result = dict(_run_sequential(state))

    ass = result.get("ass_path")
    return EditPlan(
        vibe=result["vibe"],
        segments=result["segments"],
        crop_path=result["crop_path"],
        transcript=result["transcript"],
        meme_cues=result.get("meme_cues", []),
        transitions=result.get("transitions", []),
        ass_path=Path(ass) if ass else None,
    )
