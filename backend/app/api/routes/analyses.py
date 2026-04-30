import asyncio
from secrets import compare_digest
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.db.session import get_db
from app.models.analysis import Analysis
from app.models.user import User
from app.schemas.analysis import AnalysisDetailResponse, AnalysisListItem
from app.services.analysis_service import (
    analyze_video_file,
    ensure_analysis_job_scheduled,
    claim_next_analysis_payload,
    complete_analysis_job,
    fail_analysis_job,
    requeue_stale_analyses,
)
from app.services.feedback_service import ensure_feedback_payload
from app.services.storage_service import resolve_mock_storage_path

router = APIRouter()
settings = get_settings()


class InternalAnalysisCompleteRequest(BaseModel):
    result_payload: dict


class InternalAnalysisFailedRequest(BaseModel):
    error: str


def _assert_internal_token(token: str | None) -> None:
    expected = settings.internal_worker_token or settings.secret_key
    if not token or not compare_digest(token, expected):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid internal token")


@router.get("", response_model=list[AnalysisListItem])
async def list_analyses(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[AnalysisListItem]:
    result = await db.scalars(
        select(Analysis)
        .where(Analysis.user_id == current_user.id)
        .order_by(desc(Analysis.created_at))
    )
    analyses = result.all()
    for analysis in analyses:
        ensure_analysis_job_scheduled(analysis)
    return [AnalysisListItem.model_validate(item) for item in analyses]


@router.get("/{analysis_id}", response_model=AnalysisDetailResponse)
async def get_analysis(
    analysis_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AnalysisDetailResponse:
    analysis = await db.get(Analysis, analysis_id)
    if not analysis or analysis.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")
    ensure_analysis_job_scheduled(analysis)
    response_payload = None
    if analysis.result_payload is not None:
        response_payload = dict(analysis.result_payload)
        response_payload["feedback"] = ensure_feedback_payload(
            response_payload.get("feedback"),
            response_payload.get("primary_diagnosis"),
        )

    return AnalysisDetailResponse(
        id=analysis.id,
        status=analysis.status,
        score=analysis.score,
        video_filename=analysis.video_filename,
        created_at=analysis.created_at,
        step_count=analysis.step_count,
        result_payload=response_payload,
    )


@router.get("/{analysis_id}/debug")
async def get_analysis_debug(
    analysis_id: UUID,
    recompute: bool = False,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    analysis = await db.get(Analysis, analysis_id)
    if not analysis or analysis.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")

    if recompute:
        return await asyncio.to_thread(
            analyze_video_file,
            resolve_mock_storage_path(analysis.video_storage_key),
            True,
        )

    if analysis.result_payload is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Analysis result is not available yet.",
        )

    return {
        "final_score": analysis.result_payload.get("final_score"),
        "scores": analysis.result_payload.get("scores", {}),
        "score_details": analysis.result_payload.get("score_details", {}),
        "primary_diagnosis": analysis.result_payload.get("primary_diagnosis"),
        "feedback": ensure_feedback_payload(
            analysis.result_payload.get("feedback", {}),
            analysis.result_payload.get("primary_diagnosis"),
        ),
        "debug_metrics": analysis.result_payload.get("debug_metrics", {}),
        "deduction_reasons": analysis.result_payload.get("deduction_reasons", {}),
    }


@router.post("/internal/jobs/claim", include_in_schema=False)
async def claim_internal_analysis_job(
    x_start_ai_internal_token: str | None = Header(default=None),
) -> dict:
    _assert_internal_token(x_start_ai_internal_token)
    await requeue_stale_analyses()
    payload = await claim_next_analysis_payload()
    return {"job": payload}


@router.post("/internal/jobs/{analysis_id}/complete", include_in_schema=False)
async def complete_internal_analysis_job(
    analysis_id: UUID,
    body: InternalAnalysisCompleteRequest,
    x_start_ai_internal_token: str | None = Header(default=None),
) -> dict:
    _assert_internal_token(x_start_ai_internal_token)
    updated = await complete_analysis_job(analysis_id, body.result_payload)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")
    return {"ok": True}


@router.post("/internal/jobs/{analysis_id}/failed", include_in_schema=False)
async def fail_internal_analysis_job(
    analysis_id: UUID,
    body: InternalAnalysisFailedRequest,
    x_start_ai_internal_token: str | None = Header(default=None),
) -> dict:
    _assert_internal_token(x_start_ai_internal_token)
    updated = await fail_analysis_job(analysis_id, body.error)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")
    return {"ok": True}
