from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.job import (
    JobCreate,
    JobResponse,
    JobUpdate,
    JobValidationRequest,
    JobValidationResponse,
)
from app.services.job_service import (
    create_job as create_job_service,
    delete_job as delete_job_service,
    get_job_by_id as get_job_by_id_service,
    list_jobs as list_jobs_service,
    update_job as update_job_service,
)


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


@router.get(
    "",
    response_model=list[JobResponse],
    status_code=status.HTTP_200_OK,
    summary="List jobs",
)
def list_jobs(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    session: Session = Depends(get_db),
) -> list[JobResponse]:
    jobs = list_jobs_service(
        session,
        offset=offset,
        limit=limit,
    )

    return [
        JobResponse.model_validate(job)
        for job in jobs
    ]


@router.get(
    "/{job_id}",
    response_model=JobResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a job by ID",
)
def get_job_by_id(
    job_id: UUID,
    session: Session = Depends(get_db),
) -> JobResponse:
    job = get_job_by_id_service(session, job_id)

    return JobResponse.model_validate(job)


@router.patch(
    "/{job_id}",
    response_model=JobResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a job",
)
def update_job(
    job_id: UUID,
    payload: JobUpdate,
    session: Session = Depends(get_db),
) -> JobResponse:
    job = update_job_service(
        session,
        job_id=job_id,
        payload=payload,
    )

    return JobResponse.model_validate(job)


@router.delete(
    "/{job_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a job",
)
def delete_job(
    job_id: UUID,
    session: Session = Depends(get_db),
) -> Response:
    delete_job_service(
        session,
        job_id=job_id,
    )

    return Response(
        status_code=status.HTTP_204_NO_CONTENT,
    )