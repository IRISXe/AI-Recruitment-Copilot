from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.job_requirement_profile import JobRequirementProfile
from app.schemas.job_requirement_profile import (
    JobRequirementParsingStatus,
)


def create_job_requirement_profile(
    session: Session,
    *,
    job_id: UUID,
) -> JobRequirementProfile:
    profile = JobRequirementProfile(
        job_id=job_id,
        profile_data=None,
        parsing_status="pending",
        parsing_error=None,
        parser_version=None,
        source_description_sha256=None,
        parsed_at=None,
    )

    session.add(profile)
    session.flush()

    return profile


def get_job_requirement_profile_by_job_id(
    session: Session,
    *,
    job_id: UUID,
) -> JobRequirementProfile | None:
    statement = select(JobRequirementProfile).where(
        JobRequirementProfile.job_id == job_id
    )

    return session.scalar(statement)


def update_job_requirement_profile(
    session: Session,
    *,
    profile: JobRequirementProfile,
    profile_data: dict[str, object] | None,
    parsing_status: JobRequirementParsingStatus,
    parsing_error: str | None,
    parser_version: str | None,
    source_description_sha256: str | None,
    parsed_at: datetime | None,
) -> JobRequirementProfile:
    profile.profile_data = profile_data
    profile.parsing_status = parsing_status
    profile.parsing_error = parsing_error
    profile.parser_version = parser_version
    profile.source_description_sha256 = source_description_sha256
    profile.parsed_at = parsed_at

    session.flush()

    return profile