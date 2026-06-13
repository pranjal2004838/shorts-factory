"""Visual agent (lighter variant): MediaPipe face detection + One Euro.

The blueprint specifies YOLOv8 for face tracking. To keep this first slice
lightweight and dependency-friendly we use MediaPipe Face Detection, which
runs on CPU with no model-weight downloads. The public API
(``compute_crop_path``) is deliberately model-agnostic so the detector can
be swapped for YOLOv8 later without touching the slicer.

The tracker returns, for every frame, the x-centre (in pixels) of a 9:16
crop window. When no face is found it falls back to the previous known
centre, and ultimately to the geometric centre of the frame.
"""
from __future__ import annotations

from dataclasses import dataclass

import cv2
import mediapipe as mp

from .one_euro import OneEuroFilter

TARGET_ASPECT = 9 / 16


@dataclass
class CropPath:
    """Per-frame crop geometry for a 9:16 vertical output."""

    crop_w: int
    crop_h: int
    centers_x: list[int]
    fps: float
    fell_back: bool


def _detect_center_x(detector, frame_bgr, width: int) -> float | None:
    """Return the x-centre (px) of the most confident face, or None."""
    rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    result = detector.process(rgb)
    if not result.detections:
        return None
    best = max(
        result.detections,
        key=lambda d: d.score[0] if d.score else 0.0,
    )
    box = best.location_data.relative_bounding_box
    return (box.xmin + box.width / 2.0) * width


def compute_crop_path(video_path: str, fps: float) -> CropPath:
    """Scan ``video_path`` and produce a smoothed 9:16 crop path."""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"could not open video: {video_path}")

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    # Compute the largest 9:16 window that fits inside the source frame.
    crop_w = min(width, int(round(height * TARGET_ASPECT)))
    crop_h = min(height, int(round(crop_w / TARGET_ASPECT)))
    half = crop_w / 2.0
    default_center = width / 2.0

    smoother = OneEuroFilter(freq=max(fps, 1.0), min_cutoff=0.6, beta=0.01)
    centers: list[int] = []
    last_center = default_center
    fell_back = False

    detector = mp.solutions.face_detection.FaceDetection(
        model_selection=1, min_detection_confidence=0.5
    )
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            cx = _detect_center_x(detector, frame, width)
            if cx is None:
                cx = last_center
                fell_back = True
            last_center = cx
            smoothed = smoother(cx)
            # Clamp so the crop window never leaves the frame.
            clamped = max(half, min(width - half, smoothed))
            centers.append(int(round(clamped)))
    finally:
        detector.close()
        cap.release()

    if not centers:
        fell_back = True
        centers = [int(default_center)]

    return CropPath(
        crop_w=crop_w,
        crop_h=crop_h,
        centers_x=centers,
        fps=fps,
        fell_back=fell_back,
    )
