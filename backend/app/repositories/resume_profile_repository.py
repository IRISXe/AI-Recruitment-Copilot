from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.resume_profile import ResumeProfile
from app.schemas.resume_profile import ResumeParsingStatus


def create_resume_profile(
    session: Session,
    *,
    resume_id: UUID,
) -> ResumeProfile:
    resume_profile = ResumeProfile(
        resume_id=resume_id,
        profile_data=None,
        parsing_status="pending",
        parsing_error=None,
        parser_version=None,
        source_text_sha256=None,
        parsed_at=None,
    )

    session.add(resume_profile)
    session.flush()

    return resume_profile


def get_resume_profile_by_resume_id(
    session: Session,
    *,
    resume_id: UUID,
) -> ResumeProfile | None:
    statement = select(ResumeProfile).where(
        ResumeProfile.resume_id == resume_id
    )

    return session.scalar(statement)


def update_resume_profile(
    session: Session,
    *,
    resume_profile: ResumeProfile,
    profile_data: dict[str, object] | None,
    parsing_status: ResumeParsingStatus,
    parsing_error: str | None,
    parser_version: str | None,
    source_text_sha256: str | None,
    parsed_at: datetime | None,
) -> ResumeProfile:
    resume_profile.profile_data = profile_data
    resume_profile.parsing_status = parsing_status
    resume_profile.parsing_error = parsing_error
    resume_profile.parser_version = parser_version
    resume_profile.source_text_sha256 = source_text_sha256
    resume_profile.parsed_at = parsed_at

    session.flush()

    return resume_profile