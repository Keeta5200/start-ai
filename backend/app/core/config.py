import os
from functools import lru_cache
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "START AI API"
    api_v1_str: str = "/api/v1"
    process_role: str = "web"
    enable_embedded_worker: bool = True
    port: int = 8080
    secret_key: str = "change-me"
    access_token_expire_minutes: int = 43200
    database_url: str = "postgresql+asyncpg://startai:startai@localhost:5432/startai"
    storage_bucket: str = "start-ai-local"
    storage_endpoint: str = "http://localhost:9000"
    storage_access_key: str = "local"
    storage_secret_key: str = "local"
    mock_storage_dir: str = "./uploads"
    internal_backend_base_url: str = "http://backend.railway.internal:8080"
    internal_worker_token: str | None = None
    worker_use_internal_api: bool = False
    worker_download_timeout_seconds: int = 180
    internal_api_timeout_seconds: int = 60
    analysis_worker_poll_interval_seconds: int = 5
    analysis_processing_stale_seconds: int = 300
    analysis_queue_rescue_seconds: int = 20
    analysis_abandoned_seconds: int = 7200
    analysis_worker_nice: int = 10
    cors_origins: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ]
    cors_origin_regex: str = r"^https?://((localhost|127\.0\.0\.1|192\.168\.\d+\.\d+|10\.\d+\.\d+\.\d+|172\.(1[6-9]|2\d|3[0-1])\.\d+\.\d+)(:\d+)?|[a-z0-9-]+\.up\.railway\.app)$"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        if isinstance(value, str) and value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql+asyncpg://", 1)
        if isinstance(value, str) and value.startswith("postgresql://") and "+asyncpg" not in value:
            return value.replace("postgresql://", "postgresql+asyncpg://", 1)
        return value

    @field_validator("mock_storage_dir", mode="before")
    @classmethod
    def normalize_mock_storage_dir(cls, value: str) -> str:
        if isinstance(value, str) and value and value != "./uploads":
            return value
        if os.getenv("RAILWAY_ENVIRONMENT"):
            return "/tmp/start-ai/uploads"
        return value

    @field_validator("enable_embedded_worker", mode="after")
    @classmethod
    def disable_embedded_worker_for_remote_mode(cls, value: bool, info) -> bool:
        process_role = info.data.get("process_role")
        worker_use_internal_api = info.data.get("worker_use_internal_api")
        if process_role == "web" and worker_use_internal_api:
            return False
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
