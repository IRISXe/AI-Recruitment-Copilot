from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.job import Job
from app.schemas.job import JobCreate, JobUpdate


def create_job(
    session: Session,
    payload: JobCreate,
) -> Job:
    job = Job(**payload.model_dump())

    session.add(job)
    session.flush()

    return job


def get_job_by_id(
    session: Session,
    job_id: UUID,
) -> Job | None:
    return session.get(Job, job_id)


def list_jobs(
    session: Session,
    *,
    offset: int,
    limit: int,
) -> list[Job]:
    statement = (
        select(Job)
        .order_by(Job.created_at.desc())
        .offset(offset)
        .limit(limit)
    )

    return list(session.scalars(statement).all())


def update_job(
    session: Session,
    *,
    job: Job,
    payload: JobUpdate,
) -> Job:
    update_data = payload.model_dump(exclude_unset=True)

    for field_name, value in update_data.items():
        setattr(job, field_name, value)

    session.flush()

    return job
