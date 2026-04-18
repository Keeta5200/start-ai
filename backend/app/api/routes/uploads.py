import asyncio

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.upload import UploadResponse
from app.services.analysis_service import run_analysis_job
from app.services.video_service import create_analysis_from_upload

router = APIRouter()


@router.post("/video", response_model=UploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_video(
    file: UploadFile = File(...),
    step_count: int = Form(3),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UploadResponse:
    analysis = await create_analysis_from_upload(
        db=db,
        file=file,
        user=current_user,
        step_count=step_count,
    )
    analysis.status = "queued"
    await db.commit()
    asyncio.create_task(run_analysis_job(analysis.id))
    return UploadResponse(analysis_id=str(analysis.id), status="queued")
