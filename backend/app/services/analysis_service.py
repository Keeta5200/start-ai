from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Union
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analysis import Analysis
from app.services.analysis import (
    DEFAULT_ANALYSIS_TUNING,
    detect_sprint_events,
    extract_pose_sequence,
    score_sprint_start,
)
from app.services.analysis.benchmark_data import apply_benchmark_events, get_benchmark_reference
from app.services.analysis.config import AnalysisTuning
from app.services.analysis.kinematics import build_motion_series
from app.services.analysis.pose import summarize_pose_quality
from app.services.analysis.render import render_key_frames
from app.services.feedback_service import build_feedback_payload
from app.db.session import SessionLocal
from app.services.storage_service import resolve_mock_storage_path


EMPTY_SCORE_MAP = {
    "start_posture": 0.0,
    "push_direction": 0.0,
    "first_step_landing": 0.0,
    "ground_contact": 0.0,
    "forward_com": 0.0,
    "arm_leg_coordination": 0.0,
}


async def queue_placeholder_analysis(db: AsyncSession, analysis_id: Union[str, UUID]) -> None:
    analysis = await db.get(Analysis, _normalize_analysis_id(analysis_id))
    if not analysis:
        return

    analysis.status = "processing"
    await db.commit()


def _normalize_analysis_id(analysis_id: Union[str, UUID]) -> UUID:
    return analysis_id if isinstance(analysis_id, UUID) else UUID(str(analysis_id))


async def run_analysis_job(analysis_id: Union[str, UUID]) -> None:
    normalized_id = _normalize_analysis_id(analysis_id)

    async with SessionLocal() as db:
        analysis = await db.get(Analysis, normalized_id)
        if not analysis:
            return
        analysis.status = "processing"
        video_path = resolve_mock_storage_path(analysis.video_storage_key)
        await db.commit()

    try:
        result_payload = await asyncio.to_thread(
            analyze_video_file,
            video_path,
        )
        async with SessionLocal() as db:
            analysis = await db.get(Analysis, normalized_id)
            if not analysis:
                return
            analysis.status = "completed"
            analysis.result_payload = result_payload
            analysis.score = result_payload["final_score"]
            await db.commit()
    except Exception as exc:
        async with SessionLocal() as db:
            analysis = await db.get(Analysis, normalized_id)
            if not analysis:
                return
            analysis.status = "failed"
            analysis.result_payload = {
                "final_score": 0.0,
                "scores": EMPTY_SCORE_MAP,
                "score_details": {},
                "feedback": {
                    "primary_diagnosis": "解析失敗",
                    "summary": "動画を正常に解析できませんでした。動画の長さや写り方を確認してください。",
                    "strengths": [],
                    "priorities": [],
                    "coaching_cues": [],
                },
                "debug_metrics": {
                    "error": str(exc),
                },
                "deduction_reasons": {
                    "pipeline": [str(exc)],
                },
            }
            analysis.score = 0.0
            await db.commit()


def analyze_video_file(
    video_path: Union[str, Path],
    debug: bool = True,
    tuning: AnalysisTuning = DEFAULT_ANALYSIS_TUNING,
) -> dict:
    sequence = extract_pose_sequence(video_path, tuning)
    if len(sequence.frames) < tuning.minimum_frames_required:
        raise ValueError("Video is too short for sprint-start analysis.")

    pose_quality = summarize_pose_quality(sequence, tuning)
    detected_events = detect_sprint_events(sequence, tuning)
    benchmark_reference = get_benchmark_reference(Path(video_path).name)
    events = apply_benchmark_events(detected_events, benchmark_reference)
    score_bundle = score_sprint_start(
        sequence,
        events,
        tuning,
        benchmark_reference=benchmark_reference,
    )
    motion = build_motion_series(sequence, tuning)
    pipeline_debug = _build_pipeline_debug(sequence, motion, events, pose_quality, tuning)
    feedback = build_feedback_payload(
        score_bundle.scores,
        score_bundle.score_details,
        score_bundle.primary_diagnosis,
    )
    try:
        key_frame_images = render_key_frames(video_path, sequence, events)
    except Exception:
        key_frame_images = {}

    result = {
        "final_score": score_bundle.final_score,
        "scores": score_bundle.scores,
        "score_details": score_bundle.score_details,
        "primary_diagnosis": score_bundle.primary_diagnosis,
        "feedback": feedback,
        "debug_metrics": {
            "video": {
                "fps": round(sequence.fps, 3),
                "frame_count": sequence.frame_count,
                "width": sequence.width,
                "height": sequence.height,
            },
            "pipeline_metrics": pipeline_debug,
            "warnings": pose_quality["warnings"],
            "benchmark_reference": (
                {
                    "filename": benchmark_reference.filename,
                    "push_direction": benchmark_reference.push_direction,
                    "ground_contact": benchmark_reference.ground_contact,
                    "first_step_switch": benchmark_reference.first_step_switch,
                    "rhythm_stability": benchmark_reference.rhythm_stability,
                    "teacher_note": benchmark_reference.teacher_note,
                }
                if benchmark_reference
                else None
            ),
            **score_bundle.debug_metrics,
        },
        "deduction_reasons": score_bundle.deduction_reasons,
        "key_frame_images": key_frame_images,
    }
    if not debug:
        result["debug_metrics"] = {"warnings": pose_quality["warnings"]}
    return result


def _build_pipeline_debug(sequence, motion, events, pose_quality: dict, tuning: AnalysisTuning) -> dict:
    start_frame = events.movement_initiation_frame or 0
    first_contact_frame = events.first_ground_contact_frame or min(len(sequence.frames) - 1, start_frame + 1)
    third_contact_frame = events.third_step_contact_frame or first_contact_frame

    pelvis_horizontal_displacement = motion.direction * (
        motion.pelvis[first_contact_frame][0] - motion.pelvis[start_frame][0]
    )
    pelvis_vertical_displacement = -(motion.pelvis[first_contact_frame][1] - motion.pelvis[start_frame][1])
    first_side = events.contact_legs.get("first")
    if first_side == "left":
        first_foot_series = motion.left_foot
    else:
        first_foot_series = motion.right_foot
    first_step_foot_vs_pelvis = motion.direction * (
        first_foot_series[first_contact_frame][0] - motion.pelvis[first_contact_frame][0]
    )

    contact_durations = {}
    for label, frame, side in [
        ("first", events.first_ground_contact_frame, events.contact_legs.get("first")),
        ("second", events.second_step_contact_frame, events.contact_legs.get("second")),
        ("third", events.third_step_contact_frame, events.contact_legs.get("third")),
    ]:
        if frame is None or side is None:
            contact_durations[label] = None
            continue
        foot = motion.left_foot if side == "left" else motion.right_foot
        contact_durations[label] = round(
            _estimate_contact_duration_debug(frame, foot[:, 1], tuning), 4
        )

    benchmark_alignment = None
    raw_detected_events = events.debug.get("raw_detected_events")
    benchmark_reference = events.debug.get("benchmark_reference")
    if isinstance(raw_detected_events, dict) and isinstance(benchmark_reference, dict):
        deltas = {}
        within_tolerance = {}
        frame_key_pairs = [
            ("set_position_frame", "set_frame"),
            ("movement_initiation_frame", "movement_frame"),
            ("first_ground_contact_frame", "first_contact_frame"),
            ("second_step_contact_frame", "second_contact_frame"),
            ("third_step_contact_frame", "third_contact_frame"),
        ]
        for detected_key, reference_key in frame_key_pairs:
            detected_value = raw_detected_events.get(detected_key)
            reference_value = benchmark_reference.get(reference_key)
            if isinstance(detected_value, int) and isinstance(reference_value, int):
                delta = int(detected_value) - int(reference_value)
                deltas[detected_key] = delta
                within_tolerance[detected_key] = abs(delta) <= tuning.benchmark_event_tolerance_frames
            else:
                deltas[detected_key] = None
                within_tolerance[detected_key] = False
        benchmark_alignment = {
            "event_frame_deltas": deltas,
            "within_tolerance": within_tolerance,
            "tolerance_frames": tuning.benchmark_event_tolerance_frames,
        }

    return {
        "detected_set_frame": events.set_position_frame,
        "movement_initiation_frame": events.movement_initiation_frame,
        "first_contact_frame": events.first_ground_contact_frame,
        "second_contact_frame": events.second_step_contact_frame,
        "third_contact_frame": events.third_step_contact_frame,
        "pelvis_horizontal_displacement": round(float(pelvis_horizontal_displacement), 4),
        "pelvis_vertical_displacement": round(float(pelvis_vertical_displacement), 4),
        "horizontal_vertical_ratio": round(
            float(pelvis_horizontal_displacement / max(pelvis_vertical_displacement, 1e-6)), 4
        ),
        "first_step_foot_position_vs_pelvis": round(float(first_step_foot_vs_pelvis), 4),
        "contact_duration_estimates": contact_durations,
        "pose_quality": pose_quality,
        "analysis_window_frames": {
            "start": start_frame,
            "end": third_contact_frame,
        },
        "benchmark_event_alignment": benchmark_alignment,
    }


def _estimate_contact_duration_debug(
    contact_frame: int,
    foot_y,
    tuning: AnalysisTuning,
) -> float:
    padding = tuning.debug_contact_window_padding
    ground_level = max(foot_y[max(0, contact_frame - padding) : min(len(foot_y), contact_frame + padding + 1)])
    threshold = tuning.contact_ground_tolerance_ratio * 0.10
    left = contact_frame
    while left > 0 and ground_level - foot_y[left] <= threshold:
        left -= 1
    right = contact_frame
    while right < len(foot_y) - 1 and ground_level - foot_y[right] <= threshold:
        right += 1
    return float(right - left)
