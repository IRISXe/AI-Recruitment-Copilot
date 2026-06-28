from fastapi import FastAPI

from app.api.routes.health import router as health_router

app = FastAPI(
    title="AI Recruitment Copilot API",
    description="Backend API for the AI Recruitment Copilot application.",
    version="0.1.0",
)

app.include_router(health_router)


@app.get("/", tags=["Root"])
async def root() -> dict[str, str]:
    return {
        "message": "AI Recruitment Copilot API is running",
    }