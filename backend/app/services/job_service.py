import logging
from uuid import UUID

from fastapi import status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.models.job import Job
from app.repositories.job_repository import (
    create_job as create_job_record,
    delete_job as delete_job_record,
    get_job_by_id as get_job_by_id_record,
    list_jobs as list_jobs_records,
    update_job as update_job_record,
)
from app.schemas.job import JobCreate, JobUpdate


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


def get_job_by_id(
    session: Session,
    job_id: UUID,
) -> Job:
    try:
        job = get_job_by_id_record(session, job_id)
    except SQLAlchemyError as exc:
        session.rollback()

        logger.exception(
            "Database error while retrieving a job."
        )

        raise AppException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="job_retrieval_failed",
            message="The job could not be retrieved.",
        ) from exc

    if job is None:
        raise AppException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="job_not_found",
            message="The requested job does not exist.",
        )

    return job


def list_jobs(
    session: Session,
    *,
    offset: int,
    limit: int,
) -> list[Job]:
    try:
        return list_jobs_records(
            session,
            offset=offset,
            limit=limit,
        )
    except SQLAlchemyError as exc:
        session.rollback()

        logger.exception(
            "Database error while listing jobs."
        )

        raise AppException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="job_listing_failed",
            message="The jobs could not be retrieved.",
        ) from exc


def update_job(
    session: Session,
    *,
    job_id: UUID,
    payload: JobUpdate,
) -> Job:
    try:
        job = get_job_by_id_record(session, job_id)

        if job is None:
            raise AppException(
                status_code=status.HTTP_404_NOT_FOUND,
                code="job_not_found",
                message="The requested job does not exist.",
            )

        updated_job = update_job_record(
            session,
            job=job,
            payload=payload,
        )

        session.commit()
        session.refresh(updated_job)

        return updated_job
    except SQLAlchemyError as exc:
        session.rollback()

        logger.exception(
            "Database error while updating a job."
        )

        raise AppException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="job_update_failed",
            message="The job could not be updated.",
        ) from exc


def delete_job(
    session: Session,
    *,
    job_id: UUID,
) -> None:
    try:
        job = get_job_by_id_record(session, job_id)

        if job is None:
            raise AppException(
                status_code=status.HTTP_404_NOT_FOUND,
                code="job_not_found",
                message="The requested job does not exist.",
            )

        delete_job_record(
            session,
            job=job,
        )

        session.commit()
    except SQLAlchemyError as exc:
        session.rollback()

        logger.exception(
            "Database error while deleting a job."
        )

        raise AppException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="job_deletion_failed",
            message="The job could not be deleted.",
        ) from exc