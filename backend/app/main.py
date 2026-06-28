from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError

from app.api.router import api_router
from app.core.config import get_settings
from app.core.exception_handlers import (
    app_exception_handler,
    not_found_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from app.core.exceptions import AppException

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description="Backend API for the AI Recruitment Copilot application.",
    version=settings.app_version,
    debug=settings.debug,
)

app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(
    RequestValidationError,
    validation_exception_handler,
)
app.add_exception_handler(404, not_found_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

app.include_router(api_router)


@app.get("/", tags=["Root"])
async def root() -> dict[str, str]:
    return {
        "message": f"{settings.app_name} is running",
        "environment": settings.environment,
    }