from __future__ import annotations

import asyncio
import copy
import logging
from errno import ENOSPC
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Union
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
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
from app.services.storage_service import (
    delete_mock_storage_file,
    ensure_local_mock_storage_path,
    iter_mock_storage_dirs,
)


EMPTY_SCORE_MAP = {
    "start_posture": 0.0,
    "push_direction": 0.0,
    "first_step_landing": 0.0,
    "ground_contact": 0.0,
    "forward_com": 0.0,
    "arm_leg_coordination": 0.0,
}

logger = logging.getLogger(__name__)
settings = get_settings()
ACTIVE_ANALYSIS_TASKS: set[UUID] = set()
ACTIVE_ANALYSIS_WATCHDOGS: set[UUID] = set()


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
    storage_key: str | None = None

    async with SessionLocal() as db:
        analysis = await db.get(Analysis, normalized_id)
        if not analysis:
            logger.warning("Analysis %s not found while starting job", normalized_id)
            return
        storage_key = analysis.video_storage_key
        analysis.status = "processing"
        await db.commit()
        logger.info("Analysis %s moved to processing for %s", normalized_id, analysis.video_filename)

    try:
        video_path = await asyncio.to_thread(
            ensure_local_mock_storage_path,
            analysis.video_storage_key,
        )
        result_payload = await asyncio.to_thread(
            analyze_video_file,
            video_path,
        )
        await complete_analysis_job(normalized_id, result_payload)
    except Exception as exc:
        logger.exception("Analysis %s failed", normalized_id)
        await fail_analysis_job(normalized_id, str(exc))
    finally:
        if storage_key:
            await asyncio.to_thread(delete_mock_storage_file, storage_key)


def _normalize_timestamp(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def analysis_needs_rescue(analysis: Analysis) -> bool:
    if analysis.result_payload is not None or analysis.status in {"completed", "failed"}:
        return False

    now = datetime.now(timezone.utc)
    updated_at = _normalize_timestamp(analysis.updated_at) or now
    created_at = _normalize_timestamp(analysis.created_at) or now

    if analysis.status in {"uploaded", "queued"}:
        queue_age = now - max(updated_at, created_at)
        return queue_age >= timedelta(seconds=settings.analysis_queue_rescue_seconds)

    if analysis.status == "processing":
        processing_age = now - updated_at
        return processing_age >= timedelta(seconds=settings.analysis_processing_stale_seconds)

    return False


async def _run_locally_scheduled_analysis(analysis_id: UUID) -> None:
    try:
        await run_analysis_job(analysis_id)
    finally:
        ACTIVE_ANALYSIS_TASKS.discard(analysis_id)


def ensure_analysis_job_scheduled(analysis: Analysis) -> bool:
    normalized_id = _normalize_analysis_id(analysis.id)
    if normalized_id in ACTIVE_ANALYSIS_TASKS:
        return False
    if not analysis_needs_rescue(analysis):
        return False

    ACTIVE_ANALYSIS_TASKS.add(normalized_id)
    asyncio.create_task(_run_locally_scheduled_analysis(normalized_id))
    logger.warning(
        "Scheduled local rescue for analysis %s with status %s",
        normalized_id,
        analysis.status,
    )
    return True


async def _run_analysis_rescue_watchdog(analysis_id: UUID) -> None:
    try:
        await asyncio.sleep(settings.analysis_queue_rescue_seconds)
        async with SessionLocal() as db:
            analysis = await db.get(Analysis, analysis_id)
            if not analysis:
                return
            ensure_analysis_job_scheduled(analysis)
    finally:
        ACTIVE_ANALYSIS_WATCHDOGS.discard(analysis_id)


def schedule_analysis_rescue_watchdog(analysis_id: Union[str, UUID]) -> bool:
    normalized_id = _normalize_analysis_id(analysis_id)
    if normalized_id in ACTIVE_ANALYSIS_WATCHDOGS:
        return False

    ACTIVE_ANALYSIS_WATCHDOGS.add(normalized_id)
    asyncio.create_task(_run_analysis_rescue_watchdog(normalized_id))
    return True


async def claim_next_analysis_job() -> UUID | None:
    async with SessionLocal() as db:
        result = await db.scalars(
            select(Analysis)
            .where(
                Analysis.status.in_(("uploaded", "queued")),
                Analysis.result_payload.is_(None),
            )
            .order_by(Analysis.created_at.desc())
            .limit(1)
        )
        analysis = result.first()
        if analysis is None:
            return None

        analysis.status = "processing"
        await db.commit()
        await db.refresh(analysis)
        return analysis.id


async def claim_next_analysis_payload() -> dict | None:
    async with SessionLocal() as db:
        result = await db.scalars(
            select(Analysis)
            .where(
                Analysis.status.in_(("uploaded", "queued")),
                Analysis.result_payload.is_(None),
            )
            .order_by(Analysis.created_at.desc())
            .limit(1)
        )
        analysis = result.first()
        if analysis is None:
            return None

        analysis.status = "processing"
        await db.commit()
        await db.refresh(analysis)
        return {
            "analysis_id": str(analysis.id),
            "video_filename": analysis.video_filename,
            "video_storage_key": analysis.video_storage_key,
            "step_count": analysis.step_count,
        }


async def requeue_stale_analyses() -> int:
    async with SessionLocal() as db:
        result = await db.scalars(
            select(Analysis)
            .where(
                Analysis.status == "processing",
                Analysis.result_payload.is_(None),
            )
            .order_by(Analysis.updated_at.asc())
        )
        processing_analyses = result.all()

        recovered_count = 0
        stale_cutoff = datetime.now(timezone.utc) - timedelta(
            seconds=settings.analysis_processing_stale_seconds
        )
        for analysis in processing_analyses:
            updated_at = analysis.updated_at
            if updated_at.tzinfo is None:
                updated_at = updated_at.replace(tzinfo=timezone.utc)
            if updated_at >= stale_cutoff:
                continue

            logger.warning(
                "Re-queueing stale analysis %s last updated at %s",
                analysis.id,
                updated_at.isoformat(),
            )
            analysis.status = "queued"
            recovered_count += 1

        if recovered_count:
            await db.commit()

        return recovered_count


async def complete_analysis_job(
    analysis_id: Union[str, UUID],
    result_payload: dict,
) -> bool:
    normalized_id = _normalize_analysis_id(analysis_id)
    storage_key: str | None = None
    async with SessionLocal() as db:
        analysis = await db.get(Analysis, normalized_id)
        if not analysis:
            return False
        storage_key = analysis.video_storage_key
        analysis.status = "completed"
        analysis.result_payload = result_payload
        analysis.score = float(result_payload.get("final_score") or 0.0)
        await db.commit()
        logger.info("Analysis %s completed with score %.2f", normalized_id, analysis.score)
    if storage_key:
        await asyncio.to_thread(delete_mock_storage_file, storage_key)
    return True


async def fail_analysis_job(
    analysis_id: Union[str, UUID],
    error: str,
) -> bool:
    normalized_id = _normalize_analysis_id(analysis_id)
    storage_key: str | None = None
    async with SessionLocal() as db:
        analysis = await db.get(Analysis, normalized_id)
        if not analysis:
            return False
        storage_key = analysis.video_storage_key
        analysis.status = "failed"
        analysis.result_payload = build_failed_result_payload(error)
        analysis.score = 0.0
        await db.commit()
        logger.warning("Analysis %s marked failed: %s", normalized_id, error)
    if storage_key:
        await asyncio.to_thread(delete_mock_storage_file, storage_key)
    return True


async def expire_abandoned_analyses() -> int:
    now = datetime.now(timezone.utc)
    abandoned_cutoff = now - timedelta(seconds=settings.analysis_abandoned_seconds)

    async with SessionLocal() as db:
        result = await db.scalars(
            select(Analysis)
            .where(
                Analysis.status.in_(("uploaded", "queued", "processing")),
                Analysis.result_payload.is_(None),
            )
            .order_by(Analysis.updated_at.asc())
        )
        candidates = result.all()

        expired_analyses: list[Analysis] = []
        storage_keys: list[str] = []

        for analysis in candidates:
            updated_at = _normalize_timestamp(analysis.updated_at)
            created_at = _normalize_timestamp(analysis.created_at)
            reference_time = updated_at or created_at or now
            if reference_time >= abandoned_cutoff:
                continue

            analysis.status = "failed"
            analysis.result_payload = build_failed_result_payload(
                "解析が長時間停止したため終了しました。もう一度アップロードしてください。"
            )
            analysis.score = 0.0
            expired_analyses.append(analysis)
            storage_keys.append(analysis.video_storage_key)

        if not expired_analyses:
            return 0

        await db.commit()

    removed_count = 0
    for storage_key in storage_keys:
        removed_count += int(await asyncio.to_thread(delete_mock_storage_file, storage_key))

    logger.warning(
        "Expired %s abandoned analyses and removed %s upload assets",
        len(expired_analyses),
        removed_count,
    )
    return len(expired_analyses)


async def cleanup_terminal_analysis_assets() -> int:
    async with SessionLocal() as db:
        active_keys_result = await db.scalars(
            select(Analysis.video_storage_key).where(
                Analysis.status.in_(("uploaded", "queued", "processing"))
            )
        )
        active_keys = set(active_keys_result.all())

    removed_count = 0
    for storage_dir in iter_mock_storage_dirs():
        if not storage_dir.exists():
            continue
        for candidate in storage_dir.iterdir():
            if not candidate.is_file():
                continue
            if candidate.name in active_keys:
                continue
            try:
                candidate.unlink()
                removed_count += 1
            except FileNotFoundError:
                continue

    if removed_count:
        logger.warning("Cleaned up %s stored upload assets", removed_count)

    return removed_count


async def purge_all_mock_storage_assets() -> int:
    removed_count = 0
    for storage_dir in iter_mock_storage_dirs():
        if not storage_dir.exists():
            continue
        for candidate in storage_dir.iterdir():
            if not candidate.is_file():
                continue
            try:
                candidate.unlink()
                removed_count += 1
            except FileNotFoundError:
                continue

    if removed_count:
        logger.warning("Purged %s upload assets from storage", removed_count)

    return removed_count


async def force_recover_oldest_active_analyses(limit: int | None = None) -> int:
    async with SessionLocal() as db:
        query = (
            select(Analysis)
            .where(
                Analysis.status.in_(("uploaded", "queued", "processing")),
                Analysis.result_payload.is_(None),
            )
            .order_by(Analysis.updated_at.asc(), Analysis.created_at.asc())
        )
        if limit is not None:
            query = query.limit(limit)
        result = await db.scalars(query)
        candidates = result.all()

        if not candidates:
            return 0

        storage_keys: list[str] = []
        for analysis in candidates:
            analysis.status = "failed"
            analysis.result_payload = build_failed_result_payload(
                "保存領域の回復を優先するため、長時間待機していた解析を終了しました。必要であればもう一度アップロードしてください。"
            )
            analysis.score = 0.0
            storage_keys.append(analysis.video_storage_key)

        await db.commit()

    removed_count = 0
    for storage_key in storage_keys:
        removed_count += int(await asyncio.to_thread(delete_mock_storage_file, storage_key))

    logger.warning(
        "Force-expired %s active analyses and removed %s upload assets",
        len(candidates),
        removed_count,
    )
    return len(candidates)


async def recover_storage_capacity(force: bool = False) -> int:
    expired_count = await expire_abandoned_analyses()
    removed_count = await cleanup_terminal_analysis_assets()
    force_expired_count = 0
    purged_count = 0
    if force:
        force_expired_count = await force_recover_oldest_active_analyses(limit=None)
        purged_count = await purge_all_mock_storage_assets()
    logger.warning(
        "Storage recovery executed: %s analyses expired, %s orphaned assets removed, %s active analyses force-expired, %s assets fully purged",
        expired_count,
        removed_count,
        force_expired_count,
        purged_count,
    )
    return expired_count + removed_count + force_expired_count + purged_count


def is_disk_full_error(error: BaseException) -> bool:
    return isinstance(error, OSError) and getattr(error, "errno", None) == ENOSPC


def build_failed_result_payload(error: Exception | str) -> dict:
    message = str(error)
    return {
        "final_score": 0.0,
        "scores": copy.deepcopy(EMPTY_SCORE_MAP),
        "score_details": {},
        "feedback": {
            "primary_diagnosis": "解析失敗",
            "summary": "動画を正常に解析できませんでした。動画の長さや写り方を確認してください。",
            "strengths": [],
            "priorities": [],
            "coaching_cues": [],
            "practice_recommendations": [],
        },
        "debug_metrics": {
            "error": message,
        },
        "deduction_reasons": {
            "pipeline": [message],
        },
    }


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
