from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np

from app.services.analysis.config import AnalysisTuning, DEFAULT_ANALYSIS_TUNING
from app.services.analysis.kinematics import MotionSeries, build_motion_series, normalized, signed_velocity, speed
from app.services.analysis.pose import PoseSequence


@dataclass(frozen=True)
class SprintEvents:
    set_position_frame: Optional[int]
    movement_initiation_frame: Optional[int]
    first_ground_contact_frame: Optional[int]
    second_step_contact_frame: Optional[int]
    third_step_contact_frame: Optional[int]
    contact_legs: dict[str, Optional[str]]
    debug: dict[str, float | int | list[dict[str, float | int | str]]]


def detect_sprint_events(
    sequence: PoseSequence,
    tuning: AnalysisTuning = DEFAULT_ANALYSIS_TUNING,
) -> SprintEvents:
    if not sequence.frames:
        return SprintEvents(None, None, None, None, None, {}, {"reason": "empty_sequence"})

    motion = build_motion_series(sequence, tuning)
    motion_energy = _movement_energy(sequence, motion)
    forward_velocity = motion.direction * normalized(
        signed_velocity(motion.pelvis[:, 0], sequence.fps), motion.body_scale
    )
    set_frame = _detect_set_frame(motion_energy, tuning)
    initiation_frame, baseline_energy, threshold, velocity_threshold = _detect_movement_initiation(
        motion_energy, forward_velocity, set_frame, tuning
    )
    contacts, contact_debug = _detect_ground_contacts(sequence, motion, initiation_frame, tuning)

    return SprintEvents(
        set_position_frame=set_frame,
        movement_initiation_frame=initiation_frame,
        first_ground_contact_frame=contacts[0]["frame"] if len(contacts) > 0 else None,
        second_step_contact_frame=contacts[1]["frame"] if len(contacts) > 1 else None,
        third_step_contact_frame=contacts[2]["frame"] if len(contacts) > 2 else None,
        contact_legs={
            "first": contacts[0]["side"] if len(contacts) > 0 else None,
            "second": contacts[1]["side"] if len(contacts) > 1 else None,
            "third": contacts[2]["side"] if len(contacts) > 2 else None,
        },
        debug={
            "motion_energy_baseline": round(float(baseline_energy), 4),
            "motion_energy_threshold": round(float(threshold), 4),
            "forward_velocity_threshold": round(float(velocity_threshold), 4),
            "contact_candidates": contact_debug,
        },
    )


def _movement_energy(sequence: PoseSequence, motion: MotionSeries) -> np.ndarray:
    pelvis_speed = normalized(speed(motion.pelvis, sequence.fps), motion.body_scale)
    shoulder_speed = normalized(speed(motion.shoulders, sequence.fps), motion.body_scale)
    wrist_speed = normalized(
        (speed(motion.left_wrist, sequence.fps) + speed(motion.right_wrist, sequence.fps)) / 2.0,
        motion.body_scale,
    )
    ankle_speed = normalized(
        (speed(motion.left_ankle, sequence.fps) + speed(motion.right_ankle, sequence.fps)) / 2.0,
        motion.body_scale,
    )
    return 0.35 * pelvis_speed + 0.25 * shoulder_speed + 0.20 * wrist_speed + 0.20 * ankle_speed


def _detect_set_frame(motion_energy: np.ndarray, tuning: AnalysisTuning) -> int:
    early_window = max(3, int(len(motion_energy) * tuning.early_window_ratio))
    return int(np.argmin(motion_energy[:early_window]))


def _detect_movement_initiation(
    motion_energy: np.ndarray,
    forward_velocity: np.ndarray,
    set_frame: int,
    tuning: AnalysisTuning,
) -> tuple[int, float, float, float]:
    baseline_window_start = max(0, set_frame - 4)
    baseline_window_end = min(len(motion_energy), set_frame + 3)
    baseline_energy = float(np.median(motion_energy[baseline_window_start:baseline_window_end]))
    threshold = baseline_energy + tuning.movement_energy_threshold
    baseline_velocity = float(np.median(forward_velocity[baseline_window_start:baseline_window_end]))
    velocity_threshold = max(
        tuning.initiation_velocity_threshold,
        baseline_velocity + tuning.initiation_velocity_threshold,
    )

    start_index = min(len(motion_energy) - 1, set_frame + 1)
    for frame_index in range(start_index, len(motion_energy) - tuning.movement_confirmation_frames + 1):
        energy_ready = np.all(
            motion_energy[frame_index : frame_index + tuning.movement_confirmation_frames] >= threshold
        )
        velocity_ready = np.all(
            forward_velocity[frame_index : frame_index + tuning.movement_confirmation_frames]
            >= velocity_threshold
        )
        mixed_ready = np.mean(
            motion_energy[frame_index : frame_index + tuning.movement_confirmation_frames]
        ) >= (baseline_energy + tuning.movement_energy_threshold * 0.65) and np.mean(
            forward_velocity[frame_index : frame_index + tuning.movement_confirmation_frames]
        ) >= velocity_threshold * 0.7

        if velocity_ready or (energy_ready and mixed_ready):
            return frame_index, baseline_energy, threshold, velocity_threshold

    fallback_frame = min(len(motion_energy) - 1, set_frame + 2)
    return fallback_frame, baseline_energy, threshold, velocity_threshold


def _detect_ground_contacts(
    sequence: PoseSequence,
    motion: MotionSeries,
    initiation_frame: int,
    tuning: AnalysisTuning,
) -> tuple[list[dict[str, int | float | str]], list[dict[str, int | float | str]]]:
    left_candidates = _foot_contact_candidates(
        foot=motion.left_foot,
        pelvis=motion.pelvis,
        side="left",
        fps=sequence.fps,
        body_scale=motion.body_scale,
        start_frame=max(0, initiation_frame - tuning.contact_pre_start_frames),
        tuning=tuning,
    )
    right_candidates = _foot_contact_candidates(
        foot=motion.right_foot,
        pelvis=motion.pelvis,
        side="right",
        fps=sequence.fps,
        body_scale=motion.body_scale,
        start_frame=max(0, initiation_frame - tuning.contact_pre_start_frames),
        tuning=tuning,
    )
    candidate_pool = sorted(left_candidates + right_candidates, key=lambda item: item["frame"])
    candidate_pool = [
        candidate for candidate in candidate_pool if int(candidate["frame"]) >= initiation_frame
    ]
    selected: list[dict[str, int | float | str]] = []
    debug_pool = [dict(item) for item in candidate_pool]

    for candidate in candidate_pool:
        if not selected:
            selected.append(candidate)
            continue

        previous = selected[-1]
        frame_gap = int(candidate["frame"]) - int(previous["frame"])
        if frame_gap < tuning.contact_min_spacing_frames:
            if float(candidate["candidate_score"]) > float(previous["candidate_score"]):
                selected[-1] = candidate
            continue
        if frame_gap > tuning.contact_max_spacing_frames:
            break

        expected_side = "right" if previous["side"] == "left" else "left"
        if candidate["side"] != expected_side and frame_gap <= tuning.contact_max_spacing_frames:
            alternate = _find_alternate_side_candidate(candidate_pool, candidate, expected_side)
            if alternate is not None:
                selected.append(alternate)
                if len(selected) == 3:
                    break
                continue

        selected.append(candidate)
        if len(selected) == 3:
            break

    return selected, debug_pool


def _foot_contact_candidates(
    foot: np.ndarray,
    pelvis: np.ndarray,
    side: str,
    fps: float,
    body_scale: float,
    start_frame: int,
    tuning: AnalysisTuning,
) -> list[dict[str, int | float | str]]:
    foot_speed = normalized(speed(foot, fps), body_scale)
    foot_y = foot[:, 1]
    pelvis_velocity_x = normalized(signed_velocity(pelvis[:, 0], fps), body_scale)
    ground_level = float(np.max(foot_y[start_frame:])) if start_frame < len(foot_y) else float(np.max(foot_y))
    tolerance = tuning.contact_ground_tolerance_ratio * body_scale

    candidates: list[dict[str, int | float | str]] = []
    for frame_index in range(max(1, start_frame + 1), len(foot_y) - 1):
        if not (foot_y[frame_index] >= foot_y[frame_index - 1] and foot_y[frame_index] >= foot_y[frame_index + 1]):
            continue

        ground_proximity = 1.0 - min(1.0, max(0.0, (ground_level - foot_y[frame_index]) / max(tolerance, 1e-6)))
        speed_penalty = min(1.0, float(foot_speed[frame_index]) / tuning.contact_speed_threshold)
        forward_support = min(1.0, max(0.0, float(pelvis_velocity_x[frame_index])))
        candidate_score = 0.45 * ground_proximity + 0.35 * (1.0 - speed_penalty) + 0.20 * forward_support

        if candidate_score < tuning.contact_candidate_score_threshold:
            continue

        candidates.append(
            {
                "frame": frame_index,
                "side": side,
                "candidate_score": round(float(candidate_score), 4),
                "foot_speed": round(float(foot_speed[frame_index]), 4),
                "ground_proximity": round(float(ground_proximity), 4),
            }
        )

    return candidates


def _find_alternate_side_candidate(
    candidates: list[dict[str, int | float | str]],
    current_candidate: dict[str, int | float | str],
    expected_side: str,
) -> Optional[dict[str, int | float | str]]:
    current_frame = int(current_candidate["frame"])
    for candidate in candidates:
        candidate_frame = int(candidate["frame"])
        if candidate_frame < current_frame:
            continue
        if candidate["side"] == expected_side:
            return candidate
        if candidate_frame - current_frame > 4:
            return None
    return None
