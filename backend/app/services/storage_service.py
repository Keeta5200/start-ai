from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from app.core.config import get_settings


async def save_upload_to_mock_storage(file: UploadFile) -> tuple[str, str]:
    settings = get_settings()
    storage_dir = Path(settings.mock_storage_dir)
    storage_dir.mkdir(parents=True, exist_ok=True)

    storage_key = f"{uuid4()}-{file.filename}"
    target_path = storage_dir / storage_key

    content = await file.read()
    target_path.write_bytes(content)

    return storage_key, str(target_path)


def resolve_mock_storage_path(storage_key: str) -> Path:
    settings = get_settings()
    return Path(settings.mock_storage_dir) / storage_key
