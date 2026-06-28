from fastapi import APIRouter, status

from app.schemas.job import (
    JobValidationRequest,
    JobValidationResponse,
)

router = APIRouter(prefix="/jobs", tags=["Jobs"])


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