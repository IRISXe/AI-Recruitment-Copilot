import logging
from uuid import UUID

from fastapi import status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.models.resume import Resume
from app.repositories.candidate_repository import (
    get_candidate_by_id as get_candidate_by_id_record,
)
from app.repositories.resume_repository import (
    create_resume as create_resume_record,
    delete_resume as delete_resume_record,
    get_primary_resume_by_candidate_id as get_primary_resume_record,
    get_resume_by_id as get_resume_by_id_record,
    list_resumes as list_resumes_records,
    update_resume as update_resume_record,
)
from app.schemas.resume import ResumeCreate, ResumeUpdate


logger = logging.getLogger(__name__)


def create_resume(
    session: Session,
    payload: ResumeCreate,
) -> Resume:
    try:
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

        if payload.is_primary:
            existing_primary_resume = get_primary_resume_record(
                session,
                payload.candidate_id,
            )

            if existing_primary_resume is not None:
                update_resume_record(
                    session,
                    resume=existing_primary_resume,
                    payload=ResumeUpdate(
                        is_primary=False,
                    ),
                )

        resume = create_resume_record(
            session,
            payload,
        )

        session.commit()
        session.refresh(resume)

        return resume

    except SQLAlchemyError as exc:
        session.rollback()

        logger.exception(
            "Database error while creating a resume."
        )

        raise AppException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="resume_creation_failed",
            message="The resume could not be created.",
        ) from exc


def get_resume_by_id(
    session: Session,
    resume_id: UUID,
) -> Resume:
    try:
        resume = get_resume_by_id_record(
            session,
            resume_id,
        )

    except SQLAlchemyError as exc:
        session.rollback()

        logger.exception(
            "Database error while retrieving a resume."
        )

        raise AppException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="resume_retrieval_failed",
            message="The resume could not be retrieved.",
        ) from exc

    if resume is None:
        raise AppException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="resume_not_found",
            message="The requested resume does not exist.",
        )

    return resume


def list_resumes(
    session: Session,
    *,
    offset: int,
    limit: int,
    candidate_id: UUID | None = None,
) -> list[Resume]:
    try:
        return list_resumes_records(
            session,
            offset=offset,
            limit=limit,
            candidate_id=candidate_id,
        )

    except SQLAlchemyError as exc:
        session.rollback()

        logger.exception(
            "Database error while listing resumes."
        )

        raise AppException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="resume_listing_failed",
            message="The resumes could not be retrieved.",
        ) from exc


def update_resume(
    session: Session,
    *,
    resume_id: UUID,
    payload: ResumeUpdate,
) -> Resume:
    try:
        resume = get_resume_by_id_record(
            session,
            resume_id,
        )

        if resume is None:
            raise AppException(
                status_code=status.HTTP_404_NOT_FOUND,
                code="resume_not_found",
                message="The requested resume does not exist.",
            )

        if payload.is_primary is True:
            existing_primary_resume = get_primary_resume_record(
                session,
                resume.candidate_id,
            )

            if (
                existing_primary_resume is not None
                and existing_primary_resume.id != resume.id
            ):
                update_resume_record(
                    session,
                    resume=existing_primary_resume,
                    payload=ResumeUpdate(
                        is_primary=False,
                    ),
                )

        updated_resume = update_resume_record(
            session,
            resume=resume,
            payload=payload,
        )

        session.commit()
        session.refresh(updated_resume)

        return updated_resume

    except SQLAlchemyError as exc:
        session.rollback()

        logger.exception(
            "Database error while updating a resume."
        )

        raise AppException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="resume_update_failed",
            message="The resume could not be updated.",
        ) from exc


def delete_resume(
    session: Session,
    *,
    resume_id: UUID,
) -> None:
    try:
        resume = get_resume_by_id_record(
            session,
            resume_id,
        )

        if resume is None:
            raise AppException(
                status_code=status.HTTP_404_NOT_FOUND,
                code="resume_not_found",
                message="The requested resume does not exist.",
            )

        delete_resume_record(
            session,
            resume=resume,
        )

        session.commit()

    except SQLAlchemyError as exc:
        session.rollback()

        logger.exception(
            "Database error while deleting a resume."
        )

        raise AppException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="resume_deletion_failed",
            message="The resume could not be deleted.",
        ) from exc