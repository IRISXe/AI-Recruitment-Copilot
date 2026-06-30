import logging

from fastapi import status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.models.job import Job
from app.repositories.job_repository import create_job as create_job_record
from app.schemas.job import JobCreate


logger = logging.getLogger(__name__)


def create_job(
    session: Session,
    payload: JobCreate,
) -> Job:
    try:
        job = create_job_record(session, payload)

        session.commit()
        session.refresh(job)

        return job
    except SQLAlchemyError as exc:
        session.rollback()

        logger.exception(
            "Database error while creating a job."
        )

        raise AppException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="job_creation_failed",
            message="The job could not be created.",
        ) from exc