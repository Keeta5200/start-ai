from __future__ import annotations

import asyncio
import logging
import multiprocessing as mp
import os

import uvicorn

from app.core.config import get_settings
from app.workers.jobs import run_analysis_worker

settings = get_settings()


def _run_embedded_worker() -> None:
    logging.basicConfig(level=logging.INFO)
    if settings.analysis_worker_nice and hasattr(os, "nice"):
        try:
            os.nice(settings.analysis_worker_nice)
        except OSError:
            logging.getLogger(__name__).warning("Unable to lower worker priority with os.nice")
    asyncio.run(run_analysis_worker())


def main() -> None:
    logging.basicConfig(level=logging.INFO)

    if settings.process_role == "worker":
        asyncio.run(run_analysis_worker())
        return

    worker_process: mp.Process | None = None
    if settings.enable_embedded_worker:
        worker_process = mp.Process(
            target=_run_embedded_worker,
            name="start-ai-analysis-worker",
            daemon=True,
        )
        worker_process.start()

    try:
        uvicorn.run(
            "app.main:app",
            host="0.0.0.0",
            port=settings.port,
            reload=False,
        )
    finally:
        if worker_process and worker_process.is_alive():
            worker_process.terminate()
            worker_process.join(timeout=10)


if __name__ == "__main__":
    main()
