from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.job import (
    JobCreate,
    JobResponse,
    JobValidationRequest,
    JobValidationResponse,
)
from app.services.job_service import create_job as create_job_service


router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.post(
    "",
    response_model=JobResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a job",
)
def create_job(
    payload: JobCreate,
    session: Session = Depends(get_db),
) -> JobResponse:
    job = create_job_service(session, payload)

    return JobResponse.model_validate(job)


@router.post(
    "/validate",
    response_model=JobValidationResponse,
    status_code=status.HTTP_200_OK,
    summary="Validate job information",
)
async def validate_job(
    payload: JobValidationRequest,
) -> JobValidationResponse:
    return JobValidationResponse(
        message="Job information is valid.",
        job=payload,
    )