import logging
from uuid import UUID

from fastapi import status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.models.candidate import Candidate
from app.repositories.candidate_repository import (
    create_candidate as create_candidate_record,
    get_candidate_by_id as get_candidate_by_id_record,
)
from app.schemas.candidate import CandidateCreate


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