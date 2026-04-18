from __future__ import annotations

import base64
from pathlib import Path
from typing import Union

import cv2
import numpy as np

from app.services.analysis.events import SprintEvents
from app.services.analysis.pose import PoseSequence

SKELETON_CONNECTIONS = [
    ("left_shoulder", "right_shoulder"),
    ("left_shoulder", "left_elbow"),
    ("left_elbow", "left_wrist"),
    ("right_shoulder", "right_elbow"),
    ("right_elbow", "right_wrist"),
    ("left_shoulder", "left_hip"),
    ("right_shoulder", "right_hip"),
    ("left_hip", "right_hip"),
    ("left_hip", "left_knee"),
    ("left_knee", "left_ankle"),
    ("right_hip", "right_knee"),
    ("right_knee", "right_ankle"),
    ("left_ankle", "left_foot_index"),
    ("right_ankle", "right_foot_index"),
    ("nose", "left_shoulder"),
    ("nose", "right_shoulder"),
]

KEY_FRAME_LABELS: dict[str, str] = {
    "set": "セット",
    "first_contact": "1歩目接地",
    "second_contact": "2歩目接地",
    "third_contact": "3歩目接地",
}


def render_key_frames(
    video_path: Union[str, Path],
    sequence: PoseSequence,
    events: SprintEvents,
) -> dict[str, str]:
    key_frame_indices: dict[str, int] = {}
    if events.set_position_frame is not None:
        key_frame_indices["set"] = events.set_position_frame
    if events.first_ground_contact_frame is not None:
        key_frame_indices["first_contact"] = events.first_ground_contact_frame
    if events.second_step_contact_frame is not None:
        key_frame_indices["second_contact"] = events.second_step_contact_frame
    if events.third_step_contact_frame is not None:
        key_frame_indices["third_contact"] = events.third_step_contact_frame

    if not key_frame_indices:
        return {}

    frame_lookup = {f.frame_index: f for f in sequence.frames}
    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        return {}

    result: dict[str, str] = {}
    try:
        for label, frame_index in key_frame_indices.items():
            capture.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
            success, bgr_frame = capture.read()
            if not success:
                continue

            pose_frame = frame_lookup.get(frame_index)
            if pose_frame and pose_frame.landmarks:
                h, w = bgr_frame.shape[:2]
                _draw_skeleton_overlay(bgr_frame, pose_frame.landmarks, w, h)

            _draw_label(bgr_frame, KEY_FRAME_LABELS.get(label, label))

            _, buffer = cv2.imencode(".jpg", bgr_frame, [cv2.IMWRITE_JPEG_QUALITY, 82])
            result[label] = base64.b64encode(buffer).decode("utf-8")
    finally:
        capture.release()

    return result


def _draw_skeleton_overlay(
    frame: np.ndarray,
    landmarks: dict,
    width: int,
    height: int,
) -> None:
    for start_name, end_name in SKELETON_CONNECTIONS:
        start = landmarks.get(start_name)
        end = landmarks.get(end_name)
        if start is None or end is None:
            continue
        if start.visibility < 0.45 or end.visibility < 0.45:
            continue
        x1, y1 = int(start.x * width), int(start.y * height)
        x2, y2 = int(end.x * width), int(end.y * height)
        cv2.line(frame, (x1, y1), (x2, y2), (220, 220, 220), 2, cv2.LINE_AA)

    for name, point in landmarks.items():
        if point.visibility < 0.45:
            continue
        x, y = int(point.x * width), int(point.y * height)
        is_key_joint = any(kw in name for kw in ("hip", "knee", "ankle", "shoulder", "elbow", "wrist"))
        color = (60, 140, 255) if is_key_joint else (180, 180, 180)
        radius = 5 if is_key_joint else 3
        cv2.circle(frame, (x, y), radius, color, -1, cv2.LINE_AA)


def _draw_label(frame: np.ndarray, text: str) -> None:
    h, w = frame.shape[:2]
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = max(0.5, w / 1200)
    thickness = max(1, int(w / 600))
    (text_w, text_h), baseline = cv2.getTextSize(text, font, font_scale, thickness)
    padding = 8
    cv2.rectangle(
        frame,
        (10, 10),
        (10 + text_w + padding * 2, 10 + text_h + baseline + padding * 2),
        (0, 0, 0),
        -1,
    )
    cv2.putText(
        frame,
        text,
        (10 + padding, 10 + text_h + padding),
        font,
        font_scale,
        (255, 255, 255),
        thickness,
        cv2.LINE_AA,
    )
