from fastapi import APIRouter

from app.api.routes import analyses, auth, health, uploads

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(uploads.router, prefix="/uploads", tags=["uploads"])
api_router.include_router(analyses.router, prefix="/analyses", tags=["analyses"])
