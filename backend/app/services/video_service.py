from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analysis import Analysis
from app.models.user import User
from app.services.storage_service import (
    normalize_video_filename,
    save_upload_to_mock_storage,
)


async def create_analysis_from_upload(
    db: AsyncSession, file: UploadFile, user: User, step_count: int = 3
) -> Analysis:
    storage_key, _ = await save_upload_to_mock_storage(file)
    safe_video_filename = normalize_video_filename(file.filename)

    analysis = Analysis(
        user_id=user.id,
        video_filename=safe_video_filename,
        video_storage_key=storage_key,
        status="uploaded",
        step_count=step_count,
        score=0,
    )

    db.add(analysis)
    await db.commit()
    await db.refresh(analysis)
    return analysis
