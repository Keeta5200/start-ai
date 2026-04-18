from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Optional, Union

import cv2

# MediaPipe may attempt to initialize GPU services on macOS even for CPU-style usage.
# Force CPU mode so validation scripts and backend jobs behave the same in headless runs.
os.environ.setdefault("MEDIAPIPE_DISABLE_GPU", "1")

import mediapipe as mp
import numpy as np

from app.services.analysis.config import AnalysisTuning, DEFAULT_ANALYSIS_TUNING

POSE_LANDMARK = mp.solutions.pose.PoseLandmark


@dataclass(frozen=True)
class LandmarkPoint:
    x: float
    y: float
    z: float
    visibility: float
    presence: Optional[float] = None


@dataclass(frozen=True)
class PoseFrame:
    frame_index: int
    timestamp_ms: float
    landmarks: dict[str, LandmarkPoint]
    mean_visibility: float


@dataclass(frozen=True)
class PoseSequence:
    fps: float
    width: int
    height: int
    frame_count: int
    frames: list[PoseFrame]


def normalize_presence(raw_presence: Optional[float]) -> Optional[float]:
    # MediaPipe Pose often reports presence as 0.0 even when landmarks are valid and visible.
    # Treat non-positive values as unavailable instead of rejecting otherwise high-quality joints.
    if raw_presence is None:
        return None
    value = float(raw_presence)
    if value <= 0.0:
        return None
    return value


def get_landmark(
    frame: PoseFrame,
    name: str,
    min_visibility: float = 0.0,
    min_presence: float = 0.0,
) -> Optional[LandmarkPoint]:
    landmark = frame.landmarks.get(name)
    if landmark is None:
        return None
    if landmark.visibility < min_visibility:
        return None
    if landmark.presence is not None and landmark.presence < min_presence:
        return None
    return landmark


def midpoint(
    point_a: Optional[LandmarkPoint],
    point_b: Optional[LandmarkPoint],
) -> Optional[LandmarkPoint]:
    if point_a is None or point_b is None:
        return None
    return LandmarkPoint(
        x=(point_a.x + point_b.x) / 2.0,
        y=(point_a.y + point_b.y) / 2.0,
        z=(point_a.z + point_b.z) / 2.0,
        visibility=(point_a.visibility + point_b.visibility) / 2.0,
        presence=_average_optional(point_a.presence, point_b.presence),
    )


def extract_pose_sequence(
    video_path: Union[str, Path],
    tuning: AnalysisTuning = DEFAULT_ANALYSIS_TUNING,
) -> PoseSequence:
    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise ValueError(f"Unable to open video: {video_path}")

    fps = capture.get(cv2.CAP_PROP_FPS) or 30.0
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    estimated_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    frames: list[PoseFrame] = []

    with mp.solutions.pose.Pose(
        static_image_mode=False,
        model_complexity=2,
        enable_segmentation=False,
        min_detection_confidence=tuning.min_presence_confidence,
        min_tracking_confidence=tuning.min_landmark_visibility,
    ) as pose:
        frame_index = 0
        while True:
            success, frame = capture.read()
            if not success:
                break

            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            result = pose.process(rgb_frame)

            landmarks: dict[str, LandmarkPoint] = {}
            mean_visibility = 0.0
            if result.pose_landmarks:
                visibility_values: list[float] = []
                for landmark_index, landmark_name in enumerate(POSE_LANDMARK):
                    landmark = result.pose_landmarks.landmark[landmark_index]
                    visibility = float(getattr(landmark, "visibility", 0.0))
                    presence = normalize_presence(getattr(landmark, "presence", None))
                    point = LandmarkPoint(
                        x=float(landmark.x),
                        y=float(landmark.y),
                        z=float(landmark.z),
                        visibility=visibility,
                        presence=presence,
                    )
                    landmarks[landmark_name.name.lower()] = point
                    visibility_values.append(visibility)
                mean_visibility = float(np.mean(visibility_values)) if visibility_values else 0.0

            frames.append(
                PoseFrame(
                    frame_index=frame_index,
                    timestamp_ms=(frame_index / fps) * 1000.0,
                    landmarks=landmarks,
                    mean_visibility=mean_visibility,
                )
            )
            frame_index += 1

    capture.release()
    if not frames:
        raise ValueError("Unreadable clip: no frames could be decoded.")

    return PoseSequence(
        fps=fps,
        width=width,
        height=height,
        frame_count=estimated_frames or len(frames),
        frames=frames,
    )


def summarize_pose_quality(
    sequence: PoseSequence,
    tuning: AnalysisTuning = DEFAULT_ANALYSIS_TUNING,
) -> dict[str, float | int | list[str]]:
    total_frames = len(sequence.frames)
    if total_frames == 0:
        return {
            "mean_visibility": 0.0,
            "detected_frame_ratio": 0.0,
            "edge_frame_ratio": 0.0,
            "low_visibility_frame_count": 0,
            "warnings": ["Pose sequence is empty."],
        }

    mean_visibilities = np.array([frame.mean_visibility for frame in sequence.frames], dtype=float)
    detected_frame_ratio = float(np.mean(mean_visibilities > 0.0))
    mean_visibility = float(np.mean(mean_visibilities))
    low_visibility_frame_count = int(np.sum(mean_visibilities < tuning.warning_visibility_ratio))
    edge_frame_ratio = _edge_frame_ratio(sequence, tuning)

    warnings: list[str] = []
    if mean_visibility < tuning.low_confidence_visibility_ratio:
        warnings.append("Low-confidence pose detection across the clip.")
    elif mean_visibility < tuning.warning_visibility_ratio:
        warnings.append("Pose confidence is moderate; event timing may need review.")

    if detected_frame_ratio < tuning.low_detected_frame_ratio:
        warnings.append("Landmarks were missing in too many frames for reliable sprint analysis.")

    if edge_frame_ratio >= tuning.cut_off_frame_ratio_warning:
        warnings.append("Athlete appears partially cut off near the frame edges.")

    if total_frames < tuning.preferred_minimum_frames:
        warnings.append("Clip is short for stable step-phase validation.")

    return {
        "mean_visibility": round(mean_visibility, 4),
        "detected_frame_ratio": round(detected_frame_ratio, 4),
        "edge_frame_ratio": round(edge_frame_ratio, 4),
        "low_visibility_frame_count": low_visibility_frame_count,
        "warnings": warnings,
    }


def _average_optional(value_a: Optional[float], value_b: Optional[float]) -> Optional[float]:
    values = [value for value in (value_a, value_b) if value is not None]
    if not values:
        return None
    return float(sum(values) / len(values))


def _edge_frame_ratio(
    sequence: PoseSequence,
    tuning: AnalysisTuning,
) -> float:
    edge_frames = 0
    valid_frames = 0
    margin = tuning.edge_margin_ratio

    for frame in sequence.frames:
        if not frame.landmarks:
            continue
        valid_frames += 1
        points = list(frame.landmarks.values())
        if any(
            point.x <= margin
            or point.x >= 1.0 - margin
            or point.y <= margin
            or point.y >= 1.0 - margin
            for point in points
            if point.visibility >= tuning.min_landmark_visibility
        ):
            edge_frames += 1

    if valid_frames == 0:
        return 0.0
    return float(edge_frames / valid_frames)
