from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.resume_content import ResumeContent


def create_resume_content(
    session: Session,
    *,
    resume_id: UUID,
) -> ResumeContent:
    resume_content = ResumeContent(
        resume_id=resume_id,
    )

    session.add(resume_content)
    session.flush()

    return resume_content


def get_resume_content_by_resume_id(
    session: Session,
    *,
    resume_id: UUID,
) -> ResumeContent | None:
    statement = select(ResumeContent).where(
        ResumeContent.resume_id == resume_id,
    )

    return session.scalar(statement)


def update_resume_content(
    session: Session,
    *,
    resume_content: ResumeContent,
    extracted_text: str | None,
    extraction_status: str,
    extraction_error: str | None,
    extractor_version: str | None,
    extracted_at: datetime | None,
) -> ResumeContent:
    resume_content.extracted_text = extracted_text
    resume_content.extraction_status = extraction_status
    resume_content.extraction_error = extraction_error
    resume_content.extractor_version = extractor_version
    resume_content.extracted_at = extracted_at

    session.flush()

    return resume_content