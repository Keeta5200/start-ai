import logging
from pathlib import Path
from secrets import compare_digest

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    Header,
    HTTPException,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.db.session import get_db
from app.models.user import User
from app.schemas.upload import UploadResponse
from app.services.analysis_service import (
    cleanup_terminal_analysis_assets,
    is_disk_full_error,
    recover_storage_capacity,
    schedule_analysis_rescue_watchdog,
)
from app.services.video_service import create_analysis_from_upload
from app.services.storage_service import locate_mock_storage_path

router = APIRouter()
settings = get_settings()
logger = logging.getLogger(__name__)


@router.post("/video", response_model=UploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_video(
    file: UploadFile = File(...),
    step_count: int = Form(3),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UploadResponse:
    await recover_storage_capacity()
    await cleanup_terminal_analysis_assets()
    try:
        analysis = await create_analysis_from_upload(
            db=db,
            file=file,
            user=current_user,
            step_count=step_count,
        )
    except OSError as exc:
        if not is_disk_full_error(exc):
            raise
        await recover_storage_capacity(force=True)
        await file.seek(0)
        analysis = await create_analysis_from_upload(
            db=db,
            file=file,
            user=current_user,
            step_count=step_count,
        )
    analysis.status = "queued"
    await db.commit()
    try:
        schedule_analysis_rescue_watchdog(analysis.id)
    except Exception:
        logger.exception(
            "Failed to schedule rescue watchdog for analysis %s after upload",
            analysis.id,
        )
    return UploadResponse(analysis_id=str(analysis.id), status="queued")


@router.get("/internal/{storage_key:path}", include_in_schema=False)
async def read_internal_upload(
    storage_key: str,
    background_tasks: BackgroundTasks,
    x_start_ai_internal_token: str | None = Header(default=None),
    x_start_ai_release_after_read: str | None = Header(default=None),
) -> FileResponse:
    expected_token = settings.internal_worker_token or settings.secret_key
    if not x_start_ai_internal_token or not compare_digest(x_start_ai_internal_token, expected_token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid internal token")

    target_path = locate_mock_storage_path(storage_key)
    if not target_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Upload asset not found")

    media_type = _guess_media_type(target_path)
    release_after_read = str(x_start_ai_release_after_read or "").lower() in {"1", "true", "yes"}
    if release_after_read:
        background_tasks.add_task(_release_storage_key_after_read, storage_key)

    return FileResponse(
        target_path,
        media_type=media_type,
        filename=target_path.name,
        background=background_tasks,
    )


def _release_storage_key_after_read(storage_key: str) -> None:
    locate_mock_storage_path(storage_key)
    from app.services.storage_service import delete_mock_storage_file

    delete_mock_storage_file(storage_key)


def _guess_media_type(target_path: Path) -> str:
    suffix = target_path.suffix.lower()
    if suffix == ".mp4":
        return "video/mp4"
    if suffix == ".mov":
        return "video/quicktime"
    return "application/octet-stream"
