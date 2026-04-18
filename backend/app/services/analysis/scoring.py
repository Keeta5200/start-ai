from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from app.services.analysis.benchmark_data import BenchmarkReference
from app.services.analysis.config import AnalysisTuning, DEFAULT_ANALYSIS_TUNING
from app.services.analysis.events import SprintEvents
from app.services.analysis.kinematics import MotionSeries, build_motion_series, normalized, signed_velocity, speed
from app.services.analysis.pose import PoseSequence


@dataclass(frozen=True)
class ScoreBundle:
    final_score: float
    scores: dict[str, float]
    score_details: dict[str, dict[str, float | dict | list[str] | str]]
    deduction_reasons: dict[str, list[str]]
    debug_metrics: dict[str, float | int | str | dict | list]
    primary_diagnosis: str


CORE_SCORE_WEIGHTS = {
    "ground_contact": 0.40,
    "push_direction": 0.25,
    "first_step_landing": 0.20,
    "forward_com": 0.15,
}


def score_sprint_start(
    sequence: PoseSequence,
    events: SprintEvents,
    tuning: AnalysisTuning = DEFAULT_ANALYSIS_TUNING,
    benchmark_reference: BenchmarkReference | None = None,
) -> ScoreBundle:
    motion = build_motion_series(sequence, tuning)

    start_posture, start_detail = start_posture_score(sequence, motion, events, tuning)
    push_direction, push_detail = push_direction_score(sequence, motion, events, tuning)
    first_step_landing, first_step_detail = first_step_landing_score(sequence, motion, events, tuning)
    ground_contact, ground_detail = ground_contact_score(sequence, motion, events, tuning)
    forward_com, forward_detail = forward_com_score(sequence, motion, events, tuning)
    arm_leg_coordination, coordination_detail = arm_leg_coordination_score(
        sequence, motion, events, tuning
    )

    scores = {
        "start_posture": round(start_posture, 2),
        "push_direction": round(push_direction, 2),
        "first_step_landing": round(first_step_landing, 2),
        "ground_contact": round(ground_contact, 2),
        "forward_com": round(forward_com, 2),
        "arm_leg_coordination": round(arm_leg_coordination, 2),
    }
    final_score = _weighted_final_score(scores, tuning)
    score_details = {
        "start_posture": start_detail,
        "push_direction": push_detail,
        "first_step_landing": first_step_detail,
        "ground_contact": ground_detail,
        "forward_com": forward_detail,
        "arm_leg_coordination": coordination_detail,
    }
    deduction_reasons = {
        key: list(detail.get("deduction_reasons", []))
        for key, detail in score_details.items()
    }
    if benchmark_reference is not None:
        scores, score_details = _apply_benchmark_score_calibration(
            scores=scores,
            score_details=score_details,
            benchmark_reference=benchmark_reference,
            tuning=tuning,
        )
        deduction_reasons = {
            key: list(detail.get("deduction_reasons", []))
            for key, detail in score_details.items()
        }

    final_score = _weighted_final_score(scores, tuning)
    score_bands = {key: interpret_score_band(value) for key, value in scores.items()}
    primary_diagnosis = derive_primary_diagnosis(
        scores,
        deduction_reasons,
        events,
        benchmark_reference=benchmark_reference,
    )

    return ScoreBundle(
        final_score=final_score,
        scores=scores,
        score_details=score_details,
        deduction_reasons=deduction_reasons,
        primary_diagnosis=primary_diagnosis,
        debug_metrics={
            "motion_direction": "right" if motion.direction > 0 else "left",
            "body_scale": round(motion.body_scale, 4),
            "visibility_ratio": round(motion.visibility_ratio, 4),
            "score_bands": {
                **score_bands,
                "final_score": interpret_score_band(final_score),
            },
            "threshold_summary": build_threshold_summary(tuning),
            "events": {
                "set_position_frame": events.set_position_frame,
                "movement_initiation_frame": events.movement_initiation_frame,
                "first_ground_contact_frame": events.first_ground_contact_frame,
                "second_step_contact_frame": events.second_step_contact_frame,
                "third_step_contact_frame": events.third_step_contact_frame,
                "contact_legs": events.contact_legs,
            },
            "event_detection": events.debug,
            "score_metrics": {
                "start_posture": start_detail.get("measurements", {}),
                "push_direction": push_detail.get("measurements", {}),
                "first_step_landing": first_step_detail.get("measurements", {}),
                "ground_contact": ground_detail.get("measurements", {}),
                "forward_com": forward_detail.get("measurements", {}),
                "arm_leg_coordination": coordination_detail.get("measurements", {}),
            },
            "benchmark_alignment": _build_benchmark_alignment(score_details, benchmark_reference),
            "benchmark_calibration_applied": benchmark_reference is not None,
            "final_score_weights": CORE_SCORE_WEIGHTS,
            "supplementary_scores": {
                "start_posture": scores["start_posture"],
                "arm_leg_coordination": scores["arm_leg_coordination"],
            },
        },
    )


def start_posture_score(
    sequence: PoseSequence,
    motion: MotionSeries,
    events: SprintEvents,
    tuning: AnalysisTuning,
) -> tuple[float, dict[str, float | dict | list[str] | str]]:
    set_frame = events.set_position_frame or 0
    pelvis = motion.pelvis[set_frame]
    shoulders = motion.shoulders[set_frame]
    left_foot = motion.left_foot[set_frame]
    right_foot = motion.right_foot[set_frame]

    torso_forward_lean = motion.direction * (shoulders[0] - pelvis[0])
    hip_height_above_feet = np.mean([left_foot[1], right_foot[1]]) - pelvis[1]

    lean_component = _closeness_score(
        normalized(torso_forward_lean, motion.body_scale),
        tuning.ideal_set_lean_ratio,
        tolerance=tuning.start_posture_lean_tolerance,
    )
    hip_component = _closeness_score(
        normalized(hip_height_above_feet, motion.body_scale),
        tuning.ideal_set_hip_height_ratio,
        tolerance=tuning.start_posture_hip_tolerance,
    )
    confidence_component = motion.visibility_ratio

    raw_score = 10.0 * (0.45 * lean_component + 0.35 * hip_component + 0.20 * confidence_component)
    score = _blend_with_visibility(raw_score, motion.visibility_ratio)
    measurements = {
        "torso_forward_lean_ratio": round(float(normalized(torso_forward_lean, motion.body_scale)), 4),
        "hip_height_ratio": round(float(normalized(hip_height_above_feet, motion.body_scale)), 4),
        "visibility_ratio": round(float(motion.visibility_ratio), 4),
    }
    checks = [
        _make_check(
            "torso_forward_lean_ratio",
            measurements["torso_forward_lean_ratio"],
            tuning.ideal_set_lean_ratio,
            "target",
            abs(measurements["torso_forward_lean_ratio"] - tuning.ideal_set_lean_ratio) <= tuning.start_posture_lean_tolerance,
            "penalty" if abs(measurements["torso_forward_lean_ratio"] - tuning.ideal_set_lean_ratio) > tuning.start_posture_lean_tolerance else "pass",
        ),
        _make_check(
            "hip_height_ratio",
            measurements["hip_height_ratio"],
            tuning.ideal_set_hip_height_ratio,
            "target",
            abs(measurements["hip_height_ratio"] - tuning.ideal_set_hip_height_ratio) <= tuning.start_posture_hip_tolerance,
            "penalty" if abs(measurements["hip_height_ratio"] - tuning.ideal_set_hip_height_ratio) > tuning.start_posture_hip_tolerance else "pass",
        ),
        _make_check(
            "visibility_ratio",
            measurements["visibility_ratio"],
            tuning.warning_visibility_ratio,
            ">=",
            measurements["visibility_ratio"] >= tuning.warning_visibility_ratio,
            "penalty" if measurements["visibility_ratio"] < tuning.warning_visibility_ratio else "pass",
        ),
    ]
    deductions = _collect_deductions(
        [
            (lean_component < 0.75, "Set posture does not show strong forward projection readiness."),
            (hip_component < 0.75, "Hip height in set position looks less prepared for an aggressive drive."),
            (motion.visibility_ratio < tuning.warning_visibility_ratio, "Pose confidence reduced start-posture certainty."),
        ]
    )
    return score, _score_detail(score, measurements, deductions, checks)


def push_direction_score(
    sequence: PoseSequence,
    motion: MotionSeries,
    events: SprintEvents,
    tuning: AnalysisTuning,
) -> tuple[float, dict[str, float | dict | list[str] | str]]:
    start = events.movement_initiation_frame or 0
    preferred_end = min(len(sequence.frames) - 1, start + tuning.push_direction_window_frames)
    if events.first_ground_contact_frame is not None:
        end = min(len(sequence.frames) - 1, max(events.first_ground_contact_frame, preferred_end))
    else:
        end = preferred_end
    end = max(start + 1, end)

    pelvis_window = motion.pelvis[start : end + 1]
    forward_projection = motion.direction * (pelvis_window[:, 0] - pelvis_window[0, 0])
    vertical_projection = pelvis_window[0, 1] - pelvis_window[:, 1]
    forward_progress = float(np.max(forward_projection))
    vertical_rise = max(0.0, float(np.max(vertical_projection)))

    progress_ratio = float(normalized(forward_progress, motion.body_scale))
    vertical_ratio = float(normalized(vertical_rise, motion.body_scale))
    direction_quality = progress_ratio / max(
        progress_ratio + tuning.push_direction_vertical_weight * vertical_ratio,
        1e-6,
    )
    forward_component = min(1.0, progress_ratio / tuning.strong_forward_progress_ratio)
    vertical_component = 1.0 - min(1.0, vertical_ratio / tuning.low_drive_vertical_rise_ratio)

    hv_ratio = progress_ratio / max(vertical_ratio, 1e-6)
    raw_score = 10.0 * (0.45 * direction_quality + 0.35 * forward_component + 0.20 * vertical_component)
    score = _blend_with_visibility(raw_score, motion.visibility_ratio)
    measurements = {
        "pelvis_forward_progress_ratio": round(progress_ratio, 4),
        "pelvis_vertical_rise_ratio": round(vertical_ratio, 4),
        "horizontal_vertical_ratio": round(float(hv_ratio), 4),
        "drive_direction_quality": round(float(direction_quality), 4),
    }
    checks = [
        _make_check(
            "pelvis_vertical_rise_ratio",
            measurements["pelvis_vertical_rise_ratio"],
            tuning.low_drive_vertical_rise_ratio,
            "<=",
            measurements["pelvis_vertical_rise_ratio"] <= tuning.low_drive_vertical_rise_ratio,
            "penalty" if measurements["pelvis_vertical_rise_ratio"] > tuning.low_drive_vertical_rise_ratio else "pass",
        ),
        _make_check(
            "pelvis_forward_progress_ratio",
            measurements["pelvis_forward_progress_ratio"],
            round(tuning.strong_forward_progress_ratio * 0.6, 4),
            ">=",
            measurements["pelvis_forward_progress_ratio"] >= tuning.strong_forward_progress_ratio * 0.6,
            "penalty" if measurements["pelvis_forward_progress_ratio"] < tuning.strong_forward_progress_ratio * 0.6 else "pass",
        ),
        _make_check(
            "drive_direction_quality",
            measurements["drive_direction_quality"],
            0.65,
            ">=",
            measurements["drive_direction_quality"] >= 0.65,
            "penalty" if measurements["drive_direction_quality"] < 0.65 else "pass",
        ),
    ]
    deductions = _collect_deductions(
        [
            (vertical_ratio > tuning.low_drive_vertical_rise_ratio, "Early drive rises too much vertically instead of projecting forward."),
            (progress_ratio < tuning.strong_forward_progress_ratio * 0.6, "Forward push out of set is limited."),
            (direction_quality < 0.65, "Horizontal force application is not dominating the early drive phase."),
        ]
    )
    return score, _score_detail(score, measurements, deductions, checks)


def first_step_landing_score(
    sequence: PoseSequence,
    motion: MotionSeries,
    events: SprintEvents,
    tuning: AnalysisTuning,
) -> tuple[float, dict[str, float | dict | list[str] | str]]:
    contact_frame = events.first_ground_contact_frame
    contact_side = events.contact_legs.get("first")
    if contact_frame is None or contact_side is None:
        deductions = ["First-step landing could not be identified reliably."]
        fallback_score = _event_unavailable_score(3.2, motion.visibility_ratio)
        return fallback_score, _score_detail(fallback_score, {"reason": "first_contact_unavailable"}, deductions, [])

    foot = motion.left_foot if contact_side == "left" else motion.right_foot
    foot_to_pelvis = motion.direction * (foot[contact_frame][0] - motion.pelvis[contact_frame][0])
    landing_ratio = float(normalized(foot_to_pelvis, motion.body_scale))
    switch_start = events.movement_initiation_frame or max(0, contact_frame - 6)
    switch_progress = motion.direction * (foot[contact_frame][0] - foot[switch_start][0])
    switch_progress_ratio = float(normalized(switch_progress, motion.body_scale))

    if landing_ratio <= tuning.first_step_under_pelvis_bonus_ratio:
        landing_quality = 1.0
    else:
        landing_quality = 1.0 - min(
            1.0,
            (landing_ratio - tuning.first_step_under_pelvis_bonus_ratio)
            / max(tuning.first_step_overreach_ratio, 1e-6),
        )

    switch_quality = _bounded_ratio(
        switch_progress_ratio,
        tuning.first_step_switch_min_ratio,
        tuning.first_step_switch_good_ratio,
    )
    raw_score = 10.0 * (0.7 * landing_quality + 0.3 * switch_quality)
    score = _blend_with_visibility(raw_score, motion.visibility_ratio)
    measurements = {
        "contact_side": contact_side,
        "foot_to_pelvis_ratio": round(landing_ratio, 4),
        "first_step_switch_ratio": round(switch_progress_ratio, 4),
    }
    checks = [
        _make_check(
            "foot_to_pelvis_ratio_bonus_zone",
            measurements["foot_to_pelvis_ratio"],
            tuning.first_step_under_pelvis_bonus_ratio,
            "<=",
            measurements["foot_to_pelvis_ratio"] <= tuning.first_step_under_pelvis_bonus_ratio,
            "pass" if measurements["foot_to_pelvis_ratio"] <= tuning.first_step_under_pelvis_bonus_ratio else "penalty",
        ),
        _make_check(
            "foot_to_pelvis_ratio_overreach_limit",
            measurements["foot_to_pelvis_ratio"],
            tuning.first_step_overreach_ratio,
            "<=",
            measurements["foot_to_pelvis_ratio"] <= tuning.first_step_overreach_ratio,
            "pass" if measurements["foot_to_pelvis_ratio"] <= tuning.first_step_overreach_ratio else "penalty",
        ),
        _make_check(
            "first_step_switch_ratio",
            measurements["first_step_switch_ratio"],
            tuning.first_step_switch_min_ratio,
            ">=",
            measurements["first_step_switch_ratio"] >= tuning.first_step_switch_min_ratio,
            "pass" if measurements["first_step_switch_ratio"] >= tuning.first_step_switch_min_ratio else "penalty",
        ),
    ]
    deductions = _collect_deductions(
        [
            (landing_ratio > tuning.first_step_overreach_ratio, "First step appears overreached relative to the pelvis, increasing braking risk."),
            (
                tuning.first_step_under_pelvis_bonus_ratio < landing_ratio <= tuning.first_step_overreach_ratio,
                "First step lands slightly ahead of the pelvis instead of under efficient projection.",
            ),
            (switch_progress_ratio < tuning.first_step_switch_min_ratio, "First-step switch does not come through fast enough and looks like it trails behind the body."),
        ]
    )
    return score, _score_detail(score, measurements, deductions, checks)


def ground_contact_score(
    sequence: PoseSequence,
    motion: MotionSeries,
    events: SprintEvents,
    tuning: AnalysisTuning,
) -> tuple[float, dict[str, float | dict | list[str] | str]]:
    contacts = [
        ("first", events.first_ground_contact_frame, events.contact_legs.get("first")),
        ("second", events.second_step_contact_frame, events.contact_legs.get("second")),
        ("third", events.third_step_contact_frame, events.contact_legs.get("third")),
    ]
    contact_metrics: list[dict[str, float | int | str]] = []
    contact_scores: list[float] = []

    for label, frame, side in contacts:
        if frame is None or side is None:
            continue
        foot = motion.left_foot if side == "left" else motion.right_foot
        duration = _estimate_contact_duration(frame, foot[:, 1], motion.body_scale, tuning)
        pelvis_progress = _pelvis_progress_during_contact(frame, motion, sequence.fps, duration, tuning)
        pelvis_rise = _pelvis_rise_during_contact(frame, motion, duration, tuning)
        impact_speed = float(normalized(speed(foot, sequence.fps)[frame], motion.body_scale))

        progress_component = min(1.0, pelvis_progress / tuning.ideal_contact_progress_ratio)
        duration_component = _contact_duration_component(duration, tuning)
        impact_component = 1.0 - min(1.0, impact_speed / tuning.excessive_impact_speed)
        vertical_component = 1.0 - min(1.0, pelvis_rise / tuning.low_drive_vertical_rise_ratio)

        contact_quality = (
            0.55 * progress_component
            + 0.20 * duration_component
            + 0.15 * impact_component
            + 0.10 * vertical_component
        )

        contact_metrics.append(
            {
                "label": label,
                "side": side,
                "frame": frame,
                "contact_duration_frames": round(duration, 3),
                "pelvis_progress_ratio": round(pelvis_progress, 4),
                "pelvis_rise_ratio": round(pelvis_rise, 4),
                "impact_speed_ratio": round(impact_speed, 4),
            }
        )
        contact_scores.append(10.0 * contact_quality)

    if not contact_scores:
        deductions = ["Ground-contact phases were not detected reliably enough to score propulsion."]
        fallback_score = _event_unavailable_score(2.8, motion.visibility_ratio)
        return fallback_score, _score_detail(fallback_score, {"reason": "contact_events_unavailable"}, deductions, [])

    mean_score = float(np.mean(contact_scores))
    score = _blend_with_visibility(mean_score, motion.visibility_ratio)
    mean_progress = float(np.mean([item["pelvis_progress_ratio"] for item in contact_metrics]))
    mean_duration = float(np.mean([item["contact_duration_frames"] for item in contact_metrics]))
    mean_impact = float(np.mean([item["impact_speed_ratio"] for item in contact_metrics]))
    deductions = _collect_deductions(
        [
            (mean_progress < tuning.ideal_contact_progress_ratio * 0.75, "Contacts are not producing enough forward pelvis progression."),
            (mean_duration < tuning.minimum_contact_duration_frames, "Ground contacts look too brief to load and push effectively."),
            (mean_duration > tuning.max_contact_duration_frames, "Ground contacts are lingering too long instead of pushing through cleanly."),
            (mean_impact > tuning.excessive_impact_speed * 0.8, "Foot strikes appear slappy or abrupt relative to forward payoff."),
        ]
    )
    checks = [
        _make_check(
            "mean_pelvis_progress_ratio",
            round(mean_progress, 4),
            round(tuning.ideal_contact_progress_ratio * 0.75, 4),
            ">=",
            mean_progress >= tuning.ideal_contact_progress_ratio * 0.75,
            "penalty" if mean_progress < tuning.ideal_contact_progress_ratio * 0.75 else "pass",
        ),
        _make_check(
            "mean_contact_duration_frames",
            round(mean_duration, 4),
            tuning.minimum_contact_duration_frames,
            ">=",
            mean_duration >= tuning.minimum_contact_duration_frames,
            "penalty" if mean_duration < tuning.minimum_contact_duration_frames else "pass",
        ),
        _make_check(
            "mean_contact_duration_frames_ceiling",
            round(mean_duration, 4),
            tuning.max_contact_duration_frames,
            "<=",
            mean_duration <= tuning.max_contact_duration_frames,
            "penalty" if mean_duration > tuning.max_contact_duration_frames else "pass",
        ),
        _make_check(
            "mean_impact_speed_ratio",
            round(mean_impact, 4),
            round(tuning.excessive_impact_speed * 0.8, 4),
            "<=",
            mean_impact <= tuning.excessive_impact_speed * 0.8,
            "penalty" if mean_impact > tuning.excessive_impact_speed * 0.8 else "pass",
        ),
    ]
    return score, _score_detail(
        score,
        {
            "contacts": contact_metrics,
            "mean_contact_quality": round(mean_score / 10.0, 4),
            "mean_contact_duration_frames": round(mean_duration, 4),
            "mean_pelvis_progress_ratio": round(mean_progress, 4),
            "mean_impact_speed_ratio": round(mean_impact, 4),
        },
        deductions,
        checks,
    )


def forward_com_score(
    sequence: PoseSequence,
    motion: MotionSeries,
    events: SprintEvents,
    tuning: AnalysisTuning,
) -> tuple[float, dict[str, float | dict | list[str] | str]]:
    start = events.movement_initiation_frame or 0
    end = events.third_step_contact_frame or len(sequence.frames) - 1
    end = max(start + 2, end)

    pelvis_segment = motion.pelvis[start : end + 1]
    pelvis_velocity = motion.direction * normalized(signed_velocity(pelvis_segment[:, 0], sequence.fps), motion.body_scale)
    positive_forward_ratio = float(np.mean(pelvis_velocity >= 0.0))

    vertical_series = pelvis_segment[:, 1]
    vertical_oscillation = float(normalized(np.max(vertical_series) - np.min(vertical_series), motion.body_scale))

    event_frames = [frame for frame in [events.first_ground_contact_frame, events.second_step_contact_frame, events.third_step_contact_frame] if frame is not None]
    step_progressions = _step_progressions(event_frames, motion)
    rhythm_variation = float(np.std(step_progressions) / max(np.mean(step_progressions), 1e-6)) if step_progressions else 0.0
    segment_third = max(1, len(pelvis_velocity) // 3)
    early_velocity = np.abs(pelvis_velocity[:segment_third])
    late_velocity = np.abs(pelvis_velocity[-segment_third:])
    rhythm_late_surge_ratio = float(
        np.mean(late_velocity) / max(np.mean(early_velocity), 1e-6)
    ) if len(pelvis_velocity) >= 6 else 1.0

    monotonic_component = min(1.0, positive_forward_ratio / tuning.min_forward_monotonic_ratio)
    bounce_component = 1.0 - min(1.0, vertical_oscillation / tuning.max_vertical_oscillation_ratio)
    rhythm_component = 1.0 - min(1.0, rhythm_variation)
    surge_component = 1.0 - min(1.0, max(0.0, rhythm_late_surge_ratio - 1.0) / max(tuning.rhythm_late_surge_soft_ceiling - 1.0, 1e-6))

    raw_score = 10.0 * (
        0.35 * monotonic_component
        + 0.25 * bounce_component
        + 0.20 * rhythm_component
        + 0.20 * surge_component
    )
    if len(event_frames) < 2:
        raw_score = 0.55 * raw_score + 0.45 * 4.0
    score = _blend_with_visibility(raw_score, motion.visibility_ratio)
    measurements = {
        "positive_forward_velocity_ratio": round(positive_forward_ratio, 4),
        "vertical_oscillation_ratio": round(vertical_oscillation, 4),
        "step_progression_variation": round(rhythm_variation, 4),
        "late_velocity_surge_ratio": round(rhythm_late_surge_ratio, 4),
    }
    checks = [
        _make_check(
            "vertical_oscillation_ratio",
            measurements["vertical_oscillation_ratio"],
            tuning.max_vertical_oscillation_ratio,
            "<=",
            measurements["vertical_oscillation_ratio"] <= tuning.max_vertical_oscillation_ratio,
            "penalty" if measurements["vertical_oscillation_ratio"] > tuning.max_vertical_oscillation_ratio else "pass",
        ),
        _make_check(
            "positive_forward_velocity_ratio",
            measurements["positive_forward_velocity_ratio"],
            tuning.min_forward_monotonic_ratio,
            ">=",
            measurements["positive_forward_velocity_ratio"] >= tuning.min_forward_monotonic_ratio,
            "penalty" if measurements["positive_forward_velocity_ratio"] < tuning.min_forward_monotonic_ratio else "pass",
        ),
        _make_check(
            "step_progression_variation",
            measurements["step_progression_variation"],
            0.45,
            "<=",
            measurements["step_progression_variation"] <= 0.45,
            "penalty" if measurements["step_progression_variation"] > 0.45 else "pass",
        ),
        _make_check(
            "late_velocity_surge_ratio",
            measurements["late_velocity_surge_ratio"],
            tuning.rhythm_late_surge_soft_ceiling,
            "<=",
            measurements["late_velocity_surge_ratio"] <= tuning.rhythm_late_surge_soft_ceiling,
            "penalty" if measurements["late_velocity_surge_ratio"] > tuning.rhythm_late_surge_soft_ceiling else "pass",
        ),
    ]
    deductions = _collect_deductions(
        [
            (vertical_oscillation > tuning.max_vertical_oscillation_ratio, "Pelvis shows too much vertical bounce across the first three steps."),
            (positive_forward_ratio < tuning.min_forward_monotonic_ratio, "Forward COM progression is not smooth enough frame to frame."),
            (rhythm_variation > 0.45, "Acceleration rhythm looks broken across the step sequence."),
            (rhythm_late_surge_ratio > tuning.rhythm_late_surge_soft_ceiling, "Pitch and turnover rise too abruptly later in the start instead of building progressively."),
            (len(event_frames) < 2, "Step-event coverage is incomplete, so forward progression confidence is limited."),
        ]
    )
    return score, _score_detail(score, measurements, deductions, checks)


def arm_leg_coordination_score(
    sequence: PoseSequence,
    motion: MotionSeries,
    events: SprintEvents,
    tuning: AnalysisTuning,
) -> tuple[float, dict[str, float | dict | list[str] | str]]:
    coordination_samples: list[float] = []
    coordination_debug: list[dict[str, float | int | str]] = []

    for label, frame, side in [
        ("first", events.first_ground_contact_frame, events.contact_legs.get("first")),
        ("second", events.second_step_contact_frame, events.contact_legs.get("second")),
        ("third", events.third_step_contact_frame, events.contact_legs.get("third")),
    ]:
        if frame is None or side is None:
            continue

        wrist_difference = motion.direction * (motion.right_wrist[frame][0] - motion.left_wrist[frame][0])
        expected_sign = 1.0 if side == "left" else -1.0
        timing_quality = 1.0 if np.sign(wrist_difference or expected_sign) == np.sign(expected_sign) else 0.0
        coordination_samples.append(timing_quality)
        coordination_debug.append(
            {
                "label": label,
                "side": side,
                "frame": frame,
                "wrist_difference": round(float(normalized(wrist_difference, motion.body_scale)), 4),
                "timing_quality": round(float(timing_quality), 4),
            }
        )

    arm_swing_range = motion.direction * (np.max(motion.right_wrist[:, 0] - motion.left_wrist[:, 0]) - np.min(motion.right_wrist[:, 0] - motion.left_wrist[:, 0]))
    arm_swing_ratio = abs(float(normalized(arm_swing_range, motion.body_scale)))
    swing_component = min(1.0, arm_swing_ratio / tuning.minimum_arm_swing_ratio)
    timing_component = float(np.mean(coordination_samples)) if coordination_samples else 0.5

    raw_score = 10.0 * (0.65 * timing_component + 0.35 * swing_component)
    if not coordination_samples:
        raw_score = 0.45 * raw_score + 0.55 * 4.2
    score = _blend_with_visibility(raw_score, motion.visibility_ratio)
    measurements = {
        "timing_samples": coordination_debug,
        "arm_swing_ratio": round(arm_swing_ratio, 4),
        "mean_timing_quality": round(timing_component, 4),
    }
    checks = [
        _make_check(
            "mean_timing_quality",
            measurements["mean_timing_quality"],
            0.67,
            ">=",
            measurements["mean_timing_quality"] >= 0.67,
            "penalty" if measurements["mean_timing_quality"] < 0.67 else "pass",
        ),
        _make_check(
            "arm_swing_ratio",
            measurements["arm_swing_ratio"],
            tuning.minimum_arm_swing_ratio,
            ">=",
            measurements["arm_swing_ratio"] >= tuning.minimum_arm_swing_ratio,
            "penalty" if measurements["arm_swing_ratio"] < tuning.minimum_arm_swing_ratio else "pass",
        ),
    ]
    deductions = _collect_deductions(
        [
            (timing_component < 0.67, "Arm timing looks out of sync with step contacts."),
            (arm_swing_ratio < tuning.minimum_arm_swing_ratio, "Arm action appears stiff or too small to support projection."),
            (not coordination_samples, "Arm-leg timing could not be validated from reliable step events."),
        ]
    )
    return score, _score_detail(score, measurements, deductions, checks)


def _pelvis_progress_during_contact(
    frame: int,
    motion: MotionSeries,
    fps: float,
    duration: float,
    tuning: AnalysisTuning,
) -> float:
    capped_duration = min(duration, tuning.max_contact_duration_frames)
    end = min(
        len(motion.pelvis) - 1,
        int(frame + max(2, min(tuning.contact_scan_window_frames, round(capped_duration) + 2))),
    )
    pelvis_window = motion.pelvis[frame : end + 1]
    if len(pelvis_window) == 0:
        return 0.0
    forward_projection = motion.direction * (pelvis_window[:, 0] - pelvis_window[0, 0])
    return float(normalized(np.max(forward_projection), motion.body_scale))


def _pelvis_rise_during_contact(
    frame: int,
    motion: MotionSeries,
    duration: float,
    tuning: AnalysisTuning,
) -> float:
    capped_duration = min(duration, tuning.max_contact_duration_frames)
    end = min(
        len(motion.pelvis) - 1,
        int(frame + max(2, min(tuning.contact_scan_window_frames, round(capped_duration) + 2))),
    )
    pelvis_window = motion.pelvis[frame : end + 1]
    if len(pelvis_window) == 0:
        return 0.0
    rise = max(0.0, pelvis_window[0, 1] - np.min(pelvis_window[:, 1]))
    return float(normalized(rise, motion.body_scale))


def _estimate_contact_duration(
    contact_frame: int,
    foot_y: np.ndarray,
    body_scale: float,
    tuning: AnalysisTuning,
) -> float:
    threshold = tuning.contact_ground_tolerance_ratio * body_scale
    left_bound = max(0, contact_frame - tuning.contact_scan_window_frames)
    right_bound = min(len(foot_y), contact_frame + tuning.contact_scan_window_frames + 1)
    ground_level = np.max(foot_y[left_bound:right_bound])

    left = contact_frame
    while left > left_bound and ground_level - foot_y[left] <= threshold:
        left -= 1

    right = contact_frame
    while right < right_bound - 1 and ground_level - foot_y[right] <= threshold:
        right += 1

    return float(min(right - left, tuning.max_contact_duration_frames))


def _step_progressions(event_frames: list[int], motion: MotionSeries) -> list[float]:
    if len(event_frames) < 2:
        return []
    progressions: list[float] = []
    for previous_frame, current_frame in zip(event_frames[:-1], event_frames[1:]):
        delta = motion.direction * (motion.pelvis[current_frame][0] - motion.pelvis[previous_frame][0])
        progressions.append(abs(float(normalized(delta, motion.body_scale))))
    return progressions


def _bounded_ratio(value: float, minimum: float, ideal: float) -> float:
    if value <= minimum:
        return max(0.0, value / max(minimum, 1e-6))
    if value >= ideal:
        return 1.0
    return (value - minimum) / max(ideal - minimum, 1e-6)


def _closeness_score(value: float, target: float, tolerance: float) -> float:
    return max(0.0, 1.0 - abs(value - target) / max(tolerance, 1e-6))


def _blend_with_visibility(score: float, visibility_ratio: float) -> float:
    # Low-confidence clips drift toward neutral rather than producing extreme scores from noisy landmarks.
    blended = score * visibility_ratio + 5.0 * (1.0 - visibility_ratio)
    return round(max(0.0, min(10.0, blended)), 2)


def _collect_deductions(rules: list[tuple[bool, str]]) -> list[str]:
    return [message for condition, message in rules if condition]


def _score_detail(
    score: float,
    measurements: dict[str, float | int | str | list | dict],
    deduction_reasons: list[str],
    threshold_checks: list[dict[str, float | str | bool]],
) -> dict[str, float | dict | list[str] | str]:
    return {
        "score": round(score, 2),
        "score_band": interpret_score_band(score),
        "measurements": measurements,
        "threshold_checks": threshold_checks,
        "deduction_reasons": deduction_reasons,
        "summary": "No major deductions." if not deduction_reasons else deduction_reasons[0],
    }


def interpret_score_band(score: float) -> str:
    if score >= 9.0:
        return "highest"
    if score >= 7.0:
        return "good"
    if score >= 5.0:
        return "average"
    return "needs improvement"


def derive_primary_diagnosis(
    scores: dict[str, float],
    deduction_reasons: dict[str, list[str]],
    events: SprintEvents,
    benchmark_reference: BenchmarkReference | None = None,
) -> str:
    missing_contact_count = sum(
        frame is None
        for frame in [
            events.first_ground_contact_frame,
            events.second_step_contact_frame,
            events.third_step_contact_frame,
        ]
    )
    if missing_contact_count >= 2:
        return "event detection unstable"

    if benchmark_reference is not None:
        benchmark_axis_targets = {
            "push_direction": benchmark_reference.push_direction,
            "ground_contact": benchmark_reference.ground_contact,
            "first_step_landing": benchmark_reference.first_step_switch,
            "forward_com": benchmark_reference.rhythm_stability,
        }
        weakest_axis = min(benchmark_axis_targets, key=benchmark_axis_targets.get)
        if benchmark_axis_targets[weakest_axis] <= 7.5:
            return {
                "push_direction": "vertical leakage",
                "ground_contact": "weak ground contact",
                "first_step_landing": "overreaching first step",
                "forward_com": "broken forward progression",
            }.get(weakest_axis, "balanced acceleration profile")

    priorities = [
        ("ground_contact", "weak ground contact"),
        ("push_direction", "vertical leakage"),
        ("first_step_landing", "overreaching first step"),
        ("forward_com", "broken forward progression"),
        ("arm_leg_coordination", "disconnected motion"),
        ("start_posture", "suboptimal set posture"),
    ]
    for key, fallback in priorities:
        if scores.get(key, 10.0) < 7.0:
            reasons = deduction_reasons.get(key, [])
            if reasons:
                first_reason = reasons[0].lower()
                if "could not be identified reliably" in first_reason or "not detected reliably enough" in first_reason:
                    return "event detection unstable"
                if "vertical" in first_reason:
                    return "vertical leakage"
                if "ground" in first_reason or "contact" in first_reason or "push" in first_reason:
                    return "weak ground contact"
                if "overreach" in first_reason or "braking" in first_reason:
                    return "overreaching first step"
                if "rhythm" in first_reason or "forward com" in first_reason or "progression" in first_reason:
                    return "broken forward progression"
                if "arm" in first_reason or "sync" in first_reason or "stiff" in first_reason:
                    return "disconnected motion"
            return fallback
    return "balanced acceleration profile"


def build_threshold_summary(tuning: AnalysisTuning) -> dict[str, dict[str, float]]:
    return {
        "benchmark": {
            "event_tolerance_frames": tuning.benchmark_event_tolerance_frames,
            "target_weight": tuning.benchmark_target_weight,
        },
        "pose_quality": {
            "warning_visibility_ratio": tuning.warning_visibility_ratio,
            "low_confidence_visibility_ratio": tuning.low_confidence_visibility_ratio,
            "low_detected_frame_ratio": tuning.low_detected_frame_ratio,
            "cut_off_frame_ratio_warning": tuning.cut_off_frame_ratio_warning,
        },
        "start_posture": {
            "ideal_set_lean_ratio": tuning.ideal_set_lean_ratio,
            "start_posture_lean_tolerance": tuning.start_posture_lean_tolerance,
            "ideal_set_hip_height_ratio": tuning.ideal_set_hip_height_ratio,
            "start_posture_hip_tolerance": tuning.start_posture_hip_tolerance,
        },
        "push_direction": {
            "low_drive_vertical_rise_ratio": tuning.low_drive_vertical_rise_ratio,
            "strong_forward_progress_ratio_soft_floor": round(tuning.strong_forward_progress_ratio * 0.6, 4),
            "drive_direction_quality_floor": 0.65,
            "push_direction_window_frames": tuning.push_direction_window_frames,
        },
        "first_step_landing": {
            "first_step_under_pelvis_bonus_ratio": tuning.first_step_under_pelvis_bonus_ratio,
            "first_step_overreach_ratio": tuning.first_step_overreach_ratio,
            "first_step_switch_min_ratio": tuning.first_step_switch_min_ratio,
            "first_step_switch_good_ratio": tuning.first_step_switch_good_ratio,
        },
        "ground_contact": {
            "ideal_contact_progress_ratio": tuning.ideal_contact_progress_ratio,
            "ground_contact_progress_soft_floor": round(tuning.ideal_contact_progress_ratio * 0.75, 4),
            "minimum_contact_duration_frames": tuning.minimum_contact_duration_frames,
            "maximum_contact_duration_frames": tuning.max_contact_duration_frames,
            "excessive_impact_speed_soft_ceiling": round(tuning.excessive_impact_speed * 0.8, 4),
        },
        "forward_com": {
            "max_vertical_oscillation_ratio": tuning.max_vertical_oscillation_ratio,
            "min_forward_monotonic_ratio": tuning.min_forward_monotonic_ratio,
            "step_progression_variation_ceiling": 0.45,
            "late_velocity_surge_soft_ceiling": tuning.rhythm_late_surge_soft_ceiling,
        },
        "arm_leg_coordination": {
            "minimum_arm_swing_ratio": tuning.minimum_arm_swing_ratio,
            "mean_timing_quality_floor": 0.67,
        },
    }


def _make_check(
    measurement: str,
    raw_measurement: float,
    threshold: float,
    operator: str,
    passed: bool,
    decision: str,
) -> dict[str, float | str | bool]:
    return {
        "measurement": measurement,
        "raw_measurement": round(float(raw_measurement), 4),
        "threshold": round(float(threshold), 4),
        "operator": operator,
        "passed": passed,
        "decision": decision,
    }


def _weighted_final_score(scores: dict[str, float], tuning: AnalysisTuning) -> float:
    weighted_total = 0.0
    for key, weight in CORE_SCORE_WEIGHTS.items():
        weighted_total += float(scores[key]) * float(weight)
    softened_total = weighted_total + float(tuning.final_score_bias)
    return round(max(0.0, min(10.0, softened_total)), 2)


def _event_unavailable_score(base_score: float, visibility_ratio: float) -> float:
    return _blend_with_visibility(base_score, visibility_ratio)


def _contact_duration_component(duration: float, tuning: AnalysisTuning) -> float:
    if duration < tuning.minimum_contact_duration_frames:
        return max(0.0, duration / max(tuning.minimum_contact_duration_frames, 1e-6))
    if duration <= tuning.ideal_contact_duration_frames:
        return 1.0
    if duration >= tuning.max_contact_duration_frames:
        return 0.35
    return 1.0 - 0.65 * (
        (duration - tuning.ideal_contact_duration_frames)
        / max(tuning.max_contact_duration_frames - tuning.ideal_contact_duration_frames, 1e-6)
    )


def _apply_benchmark_score_calibration(
    scores: dict[str, float],
    score_details: dict[str, dict[str, float | dict | list[str] | str]],
    benchmark_reference: BenchmarkReference,
    tuning: AnalysisTuning,
) -> tuple[dict[str, float], dict[str, dict[str, float | dict | list[str] | str]]]:
    targets = {
        "push_direction": benchmark_reference.push_direction,
        "ground_contact": benchmark_reference.ground_contact,
        "first_step_landing": benchmark_reference.first_step_switch,
        "forward_com": benchmark_reference.rhythm_stability,
    }

    calibrated_scores = dict(scores)
    calibrated_details = dict(score_details)
    target_weight = float(tuning.benchmark_target_weight)
    raw_weight = max(0.0, 1.0 - target_weight)

    for key, target in targets.items():
        raw_score = float(scores[key])
        calibrated = round(raw_weight * raw_score + target_weight * float(target), 2)
        calibrated_scores[key] = calibrated

        detail = dict(score_details[key])
        measurements = dict(detail.get("measurements", {}))
        measurements["benchmark_target_score"] = round(float(target), 2)
        measurements["benchmark_raw_score"] = round(raw_score, 2)
        measurements["benchmark_delta_before_calibration"] = round(raw_score - float(target), 2)
        measurements["benchmark_delta_after_calibration"] = round(calibrated - float(target), 2)
        measurements["benchmark_calibration_weight"] = round(target_weight, 2)
        detail["measurements"] = measurements
        detail["score"] = calibrated
        detail["score_band"] = interpret_score_band(calibrated)
        calibrated_details[key] = detail

    return calibrated_scores, calibrated_details


def _build_benchmark_alignment(
    score_details: dict[str, dict[str, float | dict | list[str] | str]],
    benchmark_reference: BenchmarkReference | None,
) -> dict[str, float | dict | str] | None:
    if benchmark_reference is None:
        return None

    axis_map = {
        "push_direction": "push_direction",
        "ground_contact": "ground_contact",
        "first_step_landing": "first_step_switch",
        "forward_com": "rhythm_stability",
    }
    axes: dict[str, dict[str, float]] = {}
    for score_key, benchmark_key in axis_map.items():
        measurements = score_details.get(score_key, {}).get("measurements", {})
        if not isinstance(measurements, dict):
            continue
        target = measurements.get("benchmark_target_score")
        raw_score = measurements.get("benchmark_raw_score")
        calibrated_score = measurements.get("benchmark_raw_score")
        if isinstance(score_details.get(score_key, {}), dict):
            calibrated_score = score_details[score_key].get("score")
        if isinstance(target, (int, float)) and isinstance(raw_score, (int, float)) and isinstance(calibrated_score, (int, float)):
            axes[benchmark_key] = {
                "target": round(float(target), 2),
                "raw_score": round(float(raw_score), 2),
                "calibrated_score": round(float(calibrated_score), 2),
                "raw_delta": round(float(raw_score) - float(target), 2),
                "calibrated_delta": round(float(calibrated_score) - float(target), 2),
            }

    return {
        "teacher_note": benchmark_reference.teacher_note,
        "axes": axes,
    }
