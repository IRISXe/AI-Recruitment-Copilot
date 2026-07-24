from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.job_requirement_profile import (
    JobRequirementProfileResponse,
)
from app.services.job_requirement_profile_service import (
    get_job_requirement_profile as get_profile_service,
    parse_job_requirement_profile as parse_profile_service,
)


router = APIRouter(
    prefix="/jobs",
    tags=["Job Requirement Profiles"],
)


@router.post(
    "/{job_id}/parse-requirements",
    response_model=JobRequirementProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Parse structured Job requirements",
    description=(
        "Parse a Job description into structured requirements. "
        "When the existing completed profile is current, it is "
        "returned without reparsing unless force is true."
    ),
)
def parse_job_requirement_profile(
    job_id: UUID,
    force: bool = Query(
        default=False,
        description=(
            "Reparse the Job description even when the stored "
            "requirement profile is already current."
        ),
    ),
    session: Session = Depends(get_db),
) -> JobRequirementProfileResponse:
    profile = parse_profile_service(
        session,
        job_id=job_id,
        force=force,
    )

    return JobRequirementProfileResponse.model_validate(
        profile
    )


@router.get(
    "/{job_id}/requirement-profile",
    response_model=JobRequirementProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Get structured Job requirements",
    description=(
        "Retrieve the currently stored structured requirement "
        "profile for a Job."
    ),
)
def get_job_requirement_profile(
    job_id: UUID,
    session: Session = Depends(get_db),
) -> JobRequirementProfileResponse:
    profile = get_profile_service(
        session,
        job_id,
    )

    return JobRequirementProfileResponse.model_validate(
        profile
    )