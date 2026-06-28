from fastapi import APIRouter

router = APIRouter(tags=["Health"])


@router.get("/health", summary="Check API health")
async def health_check() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "AI Recruitment Copilot API",
        "environment": "development",
    }