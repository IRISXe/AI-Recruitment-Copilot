import logging
from uuid import UUID

from fastapi import status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.models.candidate_job_match import CandidateJobMatch
from app.repositories.candidate_job_match_query_repository import (
    list_candidate_job_matches as list_match_records,
)
from app.repositories.candidate_job_match_repository import (
    get_candidate_job_match_by_id as get_match_record,
)
from app.repositories.candidate_repository import (
    get_candidate_by_id as get_candidate_record,
)
from app.repositories.job_repository import (
    get_job_by_id as get_job_record,
)
from app.schemas.candidate_job_match import (
    CandidateJobMatchRecommendation,
)
from app.schemas.candidate_job_match_query import (
    CandidateJobMatchSortBy,
    CandidateJobMatchSortOrder,
)


logger = logging.getLogger(__name__)


def get_candidate_job_match_by_id(
    session: Session,
    match_id: UUID,
) -> CandidateJobMatch:
    try:
        candidate_job_match = get_match_record(
            session,
            match_id,
        )
    except SQLAlchemyError as exc:
        session.rollback()

        logger.exception(
            "Database error while retrieving a Candidate-Job match."
        )

        raise AppException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="candidate_job_match_retrieval_failed",
            message=(
                "The Candidate-Job match could not be retrieved."
            ),
        ) from exc

    if candidate_job_match is None:
        raise AppException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="candidate_job_match_not_found",
            message=(
                "The requested Candidate-Job match does not exist."
            ),
        )

    return candidate_job_match


def list_candidate_job_matches(
    session: Session,
    *,
    offset: int,
    limit: int,
    candidate_id: UUID | None = None,
    job_id: UUID | None = None,
    minimum_score: float | None = None,
    minimum_confidence: float | None = None,
    recommendation: CandidateJobMatchRecommendation | None = None,
    sort_by: CandidateJobMatchSortBy = "overall_score",
    sort_order: CandidateJobMatchSortOrder = "desc",
) -> list[CandidateJobMatch]:
    try:
        return list_match_records(
            session,
            offset=offset,
            limit=limit,
            candidate_id=candidate_id,
            job_id=job_id,
            minimum_score=minimum_score,
            minimum_confidence=minimum_confidence,
            recommendation=recommendation,
            sort_by=sort_by,
            sort_order=sort_order,
        )
    except SQLAlchemyError as exc:
        session.rollback()

        logger.exception(
            "Database error while listing Candidate-Job matches."
        )

        raise AppException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="candidate_job_match_listing_failed",
            message=(
                "The Candidate-Job matches could not be retrieved."
            ),
        ) from exc


def list_candidate_matches_for_job(
    session: Session,
    *,
    job_id: UUID,
    offset: int,
    limit: int,
    minimum_score: float | None = None,
    minimum_confidence: float | None = None,
    recommendation: CandidateJobMatchRecommendation | None = None,
    sort_by: CandidateJobMatchSortBy = "overall_score",
    sort_order: CandidateJobMatchSortOrder = "desc",
) -> list[CandidateJobMatch]:
    try:
        job = get_job_record(
            session,
            job_id,
        )

        if job is None:
            raise AppException(
                status_code=status.HTTP_404_NOT_FOUND,
                code="job_not_found",
                message="The requested job does not exist.",
            )

        return list_match_records(
            session,
            offset=offset,
            limit=limit,
            job_id=job_id,
            minimum_score=minimum_score,
            minimum_confidence=minimum_confidence,
            recommendation=recommendation,
            sort_by=sort_by,
            sort_order=sort_order,
        )

    except AppException:
        raise

    except SQLAlchemyError as exc:
        session.rollback()

        logger.exception(
            "Database error while listing Candidate matches for a Job."
        )

        raise AppException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="candidate_job_match_listing_failed",
            message=(
                "The Candidate-Job matches could not be retrieved."
            ),
        ) from exc


def list_job_matches_for_candidate(
    session: Session,
    *,
    candidate_id: UUID,
    offset: int,
    limit: int,
    minimum_score: float | None = None,
    minimum_confidence: float | None = None,
    recommendation: CandidateJobMatchRecommendation | None = None,
    sort_by: CandidateJobMatchSortBy = "overall_score",
    sort_order: CandidateJobMatchSortOrder = "desc",
) -> list[CandidateJobMatch]:
    try:
        candidate = get_candidate_record(
            session,
            candidate_id,
        )

        if candidate is None:
            raise AppException(
                status_code=status.HTTP_404_NOT_FOUND,
                code="candidate_not_found",
                message=(
                    "The requested candidate does not exist."
                ),
            )

        return list_match_records(
            session,
            offset=offset,
            limit=limit,
            candidate_id=candidate_id,
            minimum_score=minimum_score,
            minimum_confidence=minimum_confidence,
            recommendation=recommendation,
            sort_by=sort_by,
            sort_order=sort_order,
        )

    except AppException:
        raise

    except SQLAlchemyError as exc:
        session.rollback()

        logger.exception(
            "Database error while listing Job matches for a Candidate."
        )

        raise AppException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="candidate_job_match_listing_failed",
            message=(
                "The Candidate-Job matches could not be retrieved."
            ),
        ) from exc