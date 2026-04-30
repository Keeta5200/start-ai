from pathlib import Path
from unicodedata import normalize
from urllib.parse import quote
from urllib.request import Request, urlopen
from uuid import uuid4

from fastapi import UploadFile

from app.core.config import get_settings


MAX_STORAGE_KEY_LENGTH = 255
MAX_VIDEO_FILENAME_LENGTH = 255


def normalize_video_filename(filename: str | None) -> str:
    raw_name = normalize("NFKC", (filename or "uploaded-video").strip()) or "uploaded-video"
    if len(raw_name) <= MAX_VIDEO_FILENAME_LENGTH:
        return raw_name

    suffix = Path(raw_name).suffix
    if suffix and len(suffix) < MAX_VIDEO_FILENAME_LENGTH:
        stem_limit = MAX_VIDEO_FILENAME_LENGTH - len(suffix)
        return f"{raw_name[:stem_limit]}{suffix}"

    return raw_name[:MAX_VIDEO_FILENAME_LENGTH]


def build_storage_key(filename: str | None) -> str:
    safe_name = normalize_video_filename(filename)
    suffix = Path(safe_name).suffix
    unique_prefix = str(uuid4())

    if suffix:
        remaining = MAX_STORAGE_KEY_LENGTH - len(unique_prefix) - 1
        trimmed_suffix = suffix[:remaining]
        return f"{unique_prefix}-{trimmed_suffix}"

    return unique_prefix


async def save_upload_to_mock_storage(file: UploadFile) -> tuple[str, str]:
    settings = get_settings()
    storage_dir = Path(settings.mock_storage_dir)
    storage_dir.mkdir(parents=True, exist_ok=True)

    storage_key = build_storage_key(file.filename)
    target_path = storage_dir / storage_key

    chunk_size = 1024 * 1024
    with target_path.open("wb") as handle:
        while True:
            chunk = await file.read(chunk_size)
            if not chunk:
                break
            handle.write(chunk)

    return storage_key, str(target_path)


def iter_mock_storage_dirs() -> list[Path]:
    settings = get_settings()
    directories = [Path(settings.mock_storage_dir)]
    legacy_dir = Path("./uploads")
    if legacy_dir not in directories:
        directories.append(legacy_dir)
    return directories


def resolve_mock_storage_path(storage_key: str) -> Path:
    settings = get_settings()
    return Path(settings.mock_storage_dir) / storage_key


def locate_mock_storage_path(storage_key: str) -> Path:
    target_path = resolve_mock_storage_path(storage_key)
    if target_path.exists():
        return target_path

    legacy_path = Path("./uploads") / storage_key
    if legacy_path.exists():
        return legacy_path

    return target_path


def ensure_local_mock_storage_path(storage_key: str) -> Path:
    settings = get_settings()
    target_path = locate_mock_storage_path(storage_key)
    if target_path.exists():
        return target_path

    target_path.parent.mkdir(parents=True, exist_ok=True)

    internal_token = settings.internal_worker_token or settings.secret_key
    if not settings.internal_backend_base_url or not internal_token:
        raise FileNotFoundError(f"Upload asset {storage_key} is not available locally")

    encoded_key = quote(storage_key, safe="")
    source_url = f"{settings.internal_backend_base_url.rstrip('/')}/api/v1/uploads/internal/{encoded_key}"
    request = Request(
        source_url,
        headers={
            "x-start-ai-internal-token": internal_token,
            "x-start-ai-release-after-read": "1",
        },
        method="GET",
    )
    with urlopen(request, timeout=settings.worker_download_timeout_seconds) as response:
        target_path.write_bytes(response.read())

    return target_path


def delete_mock_storage_file(storage_key: str) -> bool:
    removed = False
    for directory in iter_mock_storage_dirs():
        target_path = directory / storage_key
        if not target_path.exists():
            continue
        try:
            target_path.unlink()
            removed = True
        except FileNotFoundError:
            continue
    return removed


def delete_mock_storage_path(path: str | Path | None) -> bool:
    if path is None:
        return False
    target_path = Path(path)
    if not target_path.exists():
        return False
    try:
        target_path.unlink()
        return True
    except FileNotFoundError:
        return False


def delete_local_file(path: str | Path | None) -> bool:
    if path is None:
        return False
    target_path = Path(path)
    if not target_path.exists():
        return False
    try:
        target_path.unlink()
        return True
    except FileNotFoundError:
        return False
