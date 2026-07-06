import logging

from fastapi import status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.models.candidate import Candidate
from app.repositories.candidate_repository import (
    create_candidate as create_candidate_record,
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