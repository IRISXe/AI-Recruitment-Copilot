import logging
from uuid import UUID

from fastapi import status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.models.candidate import Candidate
from app.repositories.candidate_repository import (
    create_candidate as create_candidate_record,
    delete_candidate as delete_candidate_record,
    get_candidate_by_id as get_candidate_by_id_record,
    list_candidates as list_candidates_records,
    update_candidate as update_candidate_record,
)
from app.schemas.candidate import CandidateCreate, CandidateUpdate


logger = logging.getLogger(__name__)


def create_candidate(
    session: Session,
    payload: CandidateCreate,
) -> Candidate:
    try:
        candidate = create_candidate_record(
            session,
            payload,
        )

        session.commit()
        session.refresh(candidate)

        return candidate
    except SQLAlchemyError as exc:
        session.rollback()

        logger.exception(
            "Database error while creating a candidate."
        )

        raise AppException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="candidate_creation_failed",
            message="The candidate could not be created.",
        ) from exc


def get_candidate_by_id(
    session: Session,
    candidate_id: UUID,
) -> Candidate:
    try:
        candidate = get_candidate_by_id_record(
            session,
            candidate_id,
        )
    except SQLAlchemyError as exc:
        session.rollback()

        logger.exception(
            "Database error while retrieving a candidate."
        )

        raise AppException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="candidate_retrieval_failed",
            message="The candidate could not be retrieved.",
        ) from exc

    if candidate is None:
        raise AppException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="candidate_not_found",
            message="The requested candidate does not exist.",
        )

    return candidate


def list_candidates(
    session: Session,
    *,
    offset: int,
    limit: int,
) -> list[Candidate]:
    try:
        return list_candidates_records(
            session,
            offset=offset,
            limit=limit,
        )
    except SQLAlchemyError as exc:
        session.rollback()

        logger.exception(
            "Database error while listing candidates."
        )

        raise AppException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="candidate_listing_failed",
            message="The candidates could not be retrieved.",
        ) from exc


def update_candidate(
    session: Session,
    *,
    candidate_id: UUID,
    payload: CandidateUpdate,
) -> Candidate:
    try:
        candidate = get_candidate_by_id_record(
            session,
            candidate_id,
        )

        if candidate is None:
            raise AppException(
                status_code=status.HTTP_404_NOT_FOUND,
                code="candidate_not_found",
                message="The requested candidate does not exist.",
            )

        updated_candidate = update_candidate_record(
            session,
            candidate=candidate,
            payload=payload,
        )

        session.commit()
        session.refresh(updated_candidate)

        return updated_candidate
    except SQLAlchemyError as exc:
        session.rollback()

        logger.exception(
            "Database error while updating a candidate."
        )

        raise AppException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="candidate_update_failed",
            message="The candidate could not be updated.",
        ) from exc


def delete_candidate(
    session: Session,
    *,
    candidate_id: UUID,
) -> None:
    try:
        candidate = get_candidate_by_id_record(
            session,
            candidate_id,
        )

        if candidate is None:
            raise AppException(
                status_code=status.HTTP_404_NOT_FOUND,
                code="candidate_not_found",
                message="The requested candidate does not exist.",
            )

        delete_candidate_record(
            session,
            candidate=candidate,
        )

        session.commit()
    except SQLAlchemyError as exc:
        session.rollback()

        logger.exception(
            "Database error while deleting a candidate."
        )

        raise AppException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="candidate_deletion_failed",
            message="The candidate could not be deleted.",
        ) from exc