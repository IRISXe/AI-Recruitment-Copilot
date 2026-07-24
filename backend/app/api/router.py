from fastapi import APIRouter

from app.api.routes.applications import (
    router as applications_router,
)
from app.api.routes.candidate_evaluations import (
    router as candidate_evaluations_router,
)
from app.api.routes.candidate_job_matches import (
    router as candidate_job_matches_router,
)
from app.api.routes.candidates import (
    router as candidates_router,
)
from app.api.routes.health import (
    router as health_router,
)
from app.api.routes.job_requirement_profiles import (
    router as job_requirement_profiles_router,
)
from app.api.routes.jobs import (
    router as jobs_router,
)
from app.api.routes.resumes import (
    router as resumes_router,
)
from app.core.config import get_settings


settings = get_settings()

api_router = APIRouter(
    prefix=settings.api_prefix
)

api_router.include_router(health_router)
api_router.include_router(jobs_router)
api_router.include_router(job_requirement_profiles_router)
api_router.include_router(candidates_router)
api_router.include_router(candidate_evaluations_router)
api_router.include_router(applications_router)
api_router.include_router(resumes_router)
api_router.include_router(candidate_job_matches_router)