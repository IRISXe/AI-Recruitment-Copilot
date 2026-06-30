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