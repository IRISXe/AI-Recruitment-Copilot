from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.resume import Resume
from app.schemas.resume import ResumeCreate, ResumeUpdate


def create_resume(
    session: Session,
    payload: ResumeCreate,
) -> Resume:
    resume = Resume(**payload.model_dump())

    session.add(resume)
    session.flush()

    return resume


def get_resume_by_id(
    session: Session,
    resume_id: UUID,
) -> Resume | None:
    return session.get(Resume, resume_id)


def list_resumes(
    session: Session,
    *,
    offset: int,
    limit: int,
    candidate_id: UUID | None = None,
) -> list[Resume]:
    statement = select(Resume)

    if candidate_id is not None:
        statement = statement.where(
            Resume.candidate_id == candidate_id,
        )

    statement = (
        statement
        .order_by(Resume.created_at.desc())
        .offset(offset)
        .limit(limit)
    )

    return list(session.scalars(statement).all())


def get_primary_resume_by_candidate_id(
    session: Session,
    candidate_id: UUID,
) -> Resume | None:
    statement = select(Resume).where(
        Resume.candidate_id == candidate_id,
        Resume.is_primary.is_(True),
    )

    return session.scalar(statement)


def update_resume(
    session: Session,
    *,
    resume: Resume,
    payload: ResumeUpdate,
) -> Resume:
    update_data = payload.model_dump(exclude_unset=True)

    for field_name, value in update_data.items():
        setattr(resume, field_name, value)

    session.flush()

    return resume


def delete_resume(
    session: Session,
    *,
    resume: Resume,
) -> None:
    session.delete(resume)
    session.flush()