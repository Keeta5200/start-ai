from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analysis import Analysis
from app.models.user import User
from app.services.storage_service import save_upload_to_mock_storage


async def create_analysis_from_upload(
    db: AsyncSession, file: UploadFile, user: User, step_count: int = 3
) -> Analysis:
    storage_key, _ = await save_upload_to_mock_storage(file)

    analysis = Analysis(
        user_id=user.id,
        video_filename=file.filename or "unknown-video",
        video_storage_key=storage_key,
        status="uploaded",
        step_count=step_count,
        score=0,
    )

    db.add(analysis)
    await db.commit()
    await db.refresh(analysis)
    return analysis
