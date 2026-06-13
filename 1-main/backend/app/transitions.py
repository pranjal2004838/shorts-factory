"""Transition detector (Week 3): OpenCV optical flow for dance reels.

The signature dance-reel move is an outfit change that hits exactly on a
beat drop. We detect candidate transition frames by finding moments of
maximum motion (or a near-black covered-lens frame) using dense optical
flow, then align those candidates to the nearest beat.
"""
from __future__ import annotations

import cv2
import numpy as np


def _motion_series(video_path: str, sample_stride: int = 2) -> tuple[list[float], list[float]]:
    """Return (timestamps, motion_magnitude) sampled across the video."""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"could not open video: {video_path}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0

    times: list[float] = []
    motion: list[float] = []
    prev_gray = None
    idx = 0
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            if idx % sample_stride == 0:
                small = cv2.resize(frame, (160, 284))
                gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
                if prev_gray is not None:
                    flow = cv2.calcOpticalFlowFarneback(
                        prev_gray, gray, None, 0.5, 3, 15, 3, 5, 1.2, 0
                    )
                    mag = float(np.mean(np.abs(flow)))
                    # A near-black covered-lens frame is also a transition.
                    darkness = 1.0 - float(np.mean(gray)) / 255.0
                    times.append(idx / fps)
                    motion.append(mag + darkness * 2.0)
                prev_gray = gray
            idx += 1
    finally:
        cap.release()
    return times, motion


def _nearest(value: float, options: list[float]) -> float:
    return min(options, key=lambda o: abs(o - value)) if options else value


def detect_transitions(
    video_path: str,
    beats: list[float] | None = None,
    *,
    max_transitions: int = 3,
    min_gap: float = 1.0,
) -> list[float]:
    """Return transition timestamps, snapped to beats when provided."""
    times, motion = _motion_series(video_path)
    if not motion:
        return []

    order = np.argsort(motion)[::-1]
    picked: list[float] = []
    for i in order:
        t = times[int(i)]
        if all(abs(t - p) >= min_gap for p in picked):
            picked.append(t)
        if len(picked) >= max_transitions:
            break

    if beats:
        picked = sorted({round(_nearest(t, beats), 3) for t in picked})
    return sorted(picked)
