from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from app.services.analysis.config import AnalysisTuning, DEFAULT_ANALYSIS_TUNING
from app.services.analysis.pose import PoseSequence, get_landmark, midpoint


@dataclass(frozen=True)
class MotionSeries:
    pelvis: np.ndarray
    shoulders: np.ndarray
    left_foot: np.ndarray
    right_foot: np.ndarray
    left_wrist: np.ndarray
    right_wrist: np.ndarray
    left_ankle: np.ndarray
    right_ankle: np.ndarray
    body_scale: float
    direction: float
    visibility_ratio: float


def build_motion_series(
    sequence: PoseSequence,
    tuning: AnalysisTuning = DEFAULT_ANALYSIS_TUNING,
) -> MotionSeries:
    pelvis = _midpoint_series(sequence, "left_hip", "right_hip", tuning)
    shoulders = _midpoint_series(sequence, "left_shoulder", "right_shoulder", tuning)
    left_foot = _midpoint_series(sequence, "left_ankle", "left_foot_index", tuning)
    right_foot = _midpoint_series(sequence, "right_ankle", "right_foot_index", tuning)
    left_wrist = _single_joint_series(sequence, "left_wrist", tuning)
    right_wrist = _single_joint_series(sequence, "right_wrist", tuning)
    left_ankle = _single_joint_series(sequence, "left_ankle", tuning)
    right_ankle = _single_joint_series(sequence, "right_ankle", tuning)

    raw_body_scale = np.linalg.norm(shoulders - pelvis, axis=1)
    body_scale = float(np.nanmedian(raw_body_scale))
    if not np.isfinite(body_scale) or body_scale <= 1e-6:
        hip_width = np.linalg.norm(
            _single_joint_series(sequence, "left_hip", tuning)
            - _single_joint_series(sequence, "right_hip", tuning),
            axis=1,
        )
        body_scale = float(np.nanmedian(hip_width))
    if not np.isfinite(body_scale) or body_scale <= 1e-6:
        body_scale = 0.10

    valid_pelvis = pelvis[np.isfinite(pelvis[:, 0])]
    direction = 1.0
    if len(valid_pelvis) >= 2:
        delta_x = float(valid_pelvis[-1][0] - valid_pelvis[0][0])
        direction = 1.0 if delta_x >= 0.0 else -1.0

    visibility_ratio = (
        float(np.mean([frame.mean_visibility for frame in sequence.frames])) if sequence.frames else 0.0
    )

    return MotionSeries(
        pelvis=_smooth_positions(_fill_positions(pelvis), tuning.moving_average_window),
        shoulders=_smooth_positions(_fill_positions(shoulders), tuning.moving_average_window),
        left_foot=_smooth_positions(_fill_positions(left_foot), tuning.moving_average_window),
        right_foot=_smooth_positions(_fill_positions(right_foot), tuning.moving_average_window),
        left_wrist=_smooth_positions(_fill_positions(left_wrist), tuning.moving_average_window),
        right_wrist=_smooth_positions(_fill_positions(right_wrist), tuning.moving_average_window),
        left_ankle=_smooth_positions(_fill_positions(left_ankle), tuning.moving_average_window),
        right_ankle=_smooth_positions(_fill_positions(right_ankle), tuning.moving_average_window),
        body_scale=body_scale,
        direction=direction,
        visibility_ratio=visibility_ratio,
    )


def speed(signal: np.ndarray, fps: float) -> np.ndarray:
    dx = np.gradient(signal[:, 0]) * fps
    dy = np.gradient(signal[:, 1]) * fps
    return np.sqrt(dx**2 + dy**2)


def signed_velocity(signal: np.ndarray, fps: float) -> np.ndarray:
    return np.gradient(signal) * fps


def normalized(value: np.ndarray | float, body_scale: float) -> np.ndarray | float:
    return value / max(body_scale, 1e-6)


def _single_joint_series(
    sequence: PoseSequence,
    landmark_name: str,
    tuning: AnalysisTuning,
) -> np.ndarray:
    series = np.full((len(sequence.frames), 2), np.nan, dtype=float)
    for index, frame in enumerate(sequence.frames):
        landmark = get_landmark(
            frame,
            landmark_name,
            min_visibility=tuning.min_landmark_visibility,
            min_presence=tuning.min_presence_confidence,
        )
        if landmark is None:
            continue
        series[index] = [landmark.x, landmark.y]
    return series


def _midpoint_series(
    sequence: PoseSequence,
    left_name: str,
    right_name: str,
    tuning: AnalysisTuning,
) -> np.ndarray:
    series = np.full((len(sequence.frames), 2), np.nan, dtype=float)
    for index, frame in enumerate(sequence.frames):
        landmark = midpoint(
            get_landmark(
                frame,
                left_name,
                min_visibility=tuning.min_landmark_visibility,
                min_presence=tuning.min_presence_confidence,
            ),
            get_landmark(
                frame,
                right_name,
                min_visibility=tuning.min_landmark_visibility,
                min_presence=tuning.min_presence_confidence,
            ),
        )
        if landmark is None:
            continue
        series[index] = [landmark.x, landmark.y]
    return series


def _fill_positions(series: np.ndarray) -> np.ndarray:
    filled = series.copy()
    for column in range(series.shape[1]):
        values = filled[:, column]
        valid = np.isfinite(values)
        if not np.any(valid):
            filled[:, column] = 0.0
            continue
        valid_indices = np.where(valid)[0]
        filled[:, column] = np.interp(np.arange(len(values)), valid_indices, values[valid])
    return filled


def _smooth_positions(series: np.ndarray, window: int) -> np.ndarray:
    if window <= 1 or len(series) < 3:
        return series
    kernel = np.ones(window, dtype=float) / float(window)
    smoothed = np.zeros_like(series)
    for column in range(series.shape[1]):
        smoothed[:, column] = np.convolve(series[:, column], kernel, mode="same")
    return smoothed
