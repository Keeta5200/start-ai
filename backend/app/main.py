from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import get_settings
from app.db.init_db import init_db
from app.services.analysis_service import (
    cleanup_terminal_analysis_assets,
    expire_abandoned_analyses,
    requeue_stale_analyses,
)

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    await init_db()
    await expire_abandoned_analyses()
    await cleanup_terminal_analysis_assets()
    await requeue_stale_analyses()
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=settings.cors_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.api_v1_str)


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "START AI API is running"}
