from fastapi import APIRouter

from app.api.routes.health import router as health_router
from app.core.config import get_settings

settings = get_settings()

api_router = APIRouter(prefix=settings.api_prefix)

api_router.include_router(health_router)