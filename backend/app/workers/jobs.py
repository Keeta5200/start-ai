from __future__ import annotations

import asyncio
import json
import logging
from urllib.request import Request, urlopen

from app.core.config import get_settings
from app.db.init_db import init_db
from app.services.analysis_service import (
    analyze_video_file,
    claim_next_analysis_job,
    requeue_stale_analyses,
    run_analysis_job,
)
from app.services.storage_service import delete_local_file, ensure_local_mock_storage_path

settings = get_settings()
logger = logging.getLogger(__name__)


async def run_analysis_worker() -> None:
    if settings.worker_use_internal_api:
        await run_remote_analysis_worker()
        return

    await init_db()
    logger.info("START AI worker is online")

    while True:
        recovered_count = await requeue_stale_analyses()
        if recovered_count:
            logger.info("Re-queued %s stale analysis jobs", recovered_count)

        analysis_id = await claim_next_analysis_job()
        if analysis_id is None:
            await asyncio.sleep(settings.analysis_worker_poll_interval_seconds)
            continue

        logger.info("Worker claimed analysis %s", analysis_id)
        try:
            await run_analysis_job(analysis_id)
        except Exception:
            logger.exception("Worker failed while processing analysis %s", analysis_id)
            await asyncio.sleep(1)


async def run_remote_analysis_worker() -> None:
    logger.info("START AI worker is online (remote job mode)")

    while True:
        job = await asyncio.to_thread(_claim_remote_job)
        if job is None:
            await asyncio.sleep(settings.analysis_worker_poll_interval_seconds)
            continue

        analysis_id = job["analysis_id"]
        logger.info("Remote worker claimed analysis %s", analysis_id)
        video_path = None
        try:
            video_path = await asyncio.to_thread(
                ensure_local_mock_storage_path,
                job["video_storage_key"],
            )
            result_payload = await asyncio.to_thread(
                analyze_video_file,
                video_path,
            )
            await asyncio.to_thread(
                _post_internal_json,
                f"/analyses/internal/jobs/{analysis_id}/complete",
                {"result_payload": result_payload},
            )
        except Exception as exc:
            logger.exception("Remote worker failed while processing analysis %s", analysis_id)
            await asyncio.to_thread(
                _post_internal_json,
                f"/analyses/internal/jobs/{analysis_id}/failed",
                {"error": str(exc)},
            )
            await asyncio.sleep(1)
        finally:
            if video_path is not None:
                await asyncio.to_thread(delete_local_file, video_path)


def _claim_remote_job() -> dict | None:
    payload = _post_internal_json("/analyses/internal/jobs/claim", {})
    return payload.get("job")


def _post_internal_json(path: str, payload: dict) -> dict:
    base_url = settings.internal_backend_base_url.rstrip("/")
    body = json.dumps(payload).encode("utf-8")
    request = Request(
        f"{base_url}{settings.api_v1_str}{path}",
        data=body,
        method="POST",
        headers={
            "content-type": "application/json",
            "x-start-ai-internal-token": settings.internal_worker_token or settings.secret_key,
        },
    )
    with urlopen(request, timeout=settings.internal_api_timeout_seconds) as response:
        raw = response.read().decode("utf-8")
    if not raw:
        return {}
    return json.loads(raw)
