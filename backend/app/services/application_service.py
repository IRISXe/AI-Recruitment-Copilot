import logging
from uuid import UUID

from fastapi import status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.models.application import Application
from app.repositories.application_repository import (
    create_application as create_application_record,
    delete_application as delete_application_record,
    get_application_by_id as get_application_by_id_record,
    get_application_by_job_and_candidate as get_duplicate_application_record,
    list_applications as list_applications_records,
    update_application as update_application_record,
)
from app.repositories.candidate_repository import (
    get_candidate_by_id as get_candidate_by_id_record,
)
from app.repositories.job_repository import (
    get_job_by_id as get_job_by_id_record,
)
from app.schemas.application import ApplicationCreate, ApplicationUpdate


logger = logging.getLogger(__name__)


def create_application(
    session: Session,
    payload: ApplicationCreate,
) -> Application:
    try:
        job = get_job_by_id_record(
            session,
            payload.job_id,
        )

        if job is None:
            raise AppException(
                status_code=status.HTTP_404_NOT_FOUND,
                code="job_not_found",
                message="The requested job does not exist.",
            )

        candidate = get_candidate_by_id_record(
            session,
            payload.candidate_id,
        )

        if candidate is None:
            raise AppException(
                status_code=status.HTTP_404_NOT_FOUND,
                code="candidate_not_found",
                message="The requested candidate does not exist.",
            )

        existing_application = get_duplicate_application_record(
            session,
            job_id=payload.job_id,
            candidate_id=payload.candidate_id,
        )

        if existing_application is not None:
            raise AppException(
                status_code=status.HTTP_409_CONFLICT,
                code="application_already_exists",
                message=(
                    "This candidate has already applied to this job."
                ),
            )

        application = create_application_record(
            session,
            payload,
        )

        session.commit()
        session.refresh(application)

        return application

    except SQLAlchemyError as exc:
        session.rollback()

        logger.exception(
            "Database error while creating an application."
        )

        raise AppException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="application_creation_failed",
            message="The application could not be created.",
        ) from exc


def get_application_by_id(
    session: Session,
    application_id: UUID,
) -> Application:
    try:
        application = get_application_by_id_record(
            session,
            application_id,
        )

    except SQLAlchemyError as exc:
        session.rollback()

        logger.exception(
            "Database error while retrieving an application."
        )

        raise AppException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="application_retrieval_failed",
            message="The application could not be retrieved.",
        ) from exc

    if application is None:
        raise AppException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="application_not_found",
            message="The requested application does not exist.",
        )

    return application


def list_applications(
    session: Session,
    *,
    offset: int,
    limit: int,
) -> list[Application]:
    try:
        return list_applications_records(
            session,
            offset=offset,
            limit=limit,
        )

    except SQLAlchemyError as exc:
        session.rollback()

        logger.exception(
            "Database error while listing applications."
        )

        raise AppException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="application_listing_failed",
            message="The applications could not be retrieved.",
        ) from exc


def update_application(
    session: Session,
    *,
    application_id: UUID,
    payload: ApplicationUpdate,
) -> Application:
    try:
        application = get_application_by_id_record(
            session,
            application_id,
        )

        if application is None:
            raise AppException(
                status_code=status.HTTP_404_NOT_FOUND,
                code="application_not_found",
                message="The requested application does not exist.",
            )

        updated_application = update_application_record(
            session,
            application=application,
            payload=payload,
        )

        session.commit()
        session.refresh(updated_application)

        return updated_application

    except SQLAlchemyError as exc:
        session.rollback()

        logger.exception(
            "Database error while updating an application."
        )

        raise AppException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="application_update_failed",
            message="The application could not be updated.",
        ) from exc


def delete_application(
    session: Session,
    *,
    application_id: UUID,
) -> None:
    try:
        application = get_application_by_id_record(
            session,
            application_id,
        )

        if application is None:
            raise AppException(
                status_code=status.HTTP_404_NOT_FOUND,
                code="application_not_found",
                message="The requested application does not exist.",
            )

        delete_application_record(
            session,
            application=application,
        )

        session.commit()

    except SQLAlchemyError as exc:
        session.rollback()

        logger.exception(
            "Database error while deleting an application."
        )

        raise AppException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="application_deletion_failed",
            message="The application could not be deleted.",
        ) from exc