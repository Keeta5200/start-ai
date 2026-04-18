import asyncio
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.analysis import Analysis
from app.models.user import User
from app.schemas.analysis import AnalysisDetailResponse, AnalysisListItem
from app.services.analysis_service import analyze_video_file
from app.services.storage_service import resolve_mock_storage_path

router = APIRouter()


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
    return [AnalysisListItem.model_validate(item) for item in result.all()]


@router.get("/{analysis_id}", response_model=AnalysisDetailResponse)
async def get_analysis(
    analysis_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AnalysisDetailResponse:
    analysis = await db.get(Analysis, analysis_id)
    if not analysis or analysis.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")
    return AnalysisDetailResponse.model_validate(analysis)


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
        "feedback": analysis.result_payload.get("feedback", {}),
        "debug_metrics": analysis.result_payload.get("debug_metrics", {}),
        "deduction_reasons": analysis.result_payload.get("deduction_reasons", {}),
    }
