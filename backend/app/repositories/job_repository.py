from uuid import UUID

from sqlalchemy.orm import Session

from app.models.job import Job
from app.schemas.job import JobCreate


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