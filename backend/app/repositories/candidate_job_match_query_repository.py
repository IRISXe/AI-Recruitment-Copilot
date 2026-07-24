from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.candidate_job_match import CandidateJobMatch
from app.schemas.candidate_job_match import (
    CandidateJobMatchRecommendation,
)
from app.schemas.candidate_job_match_query import (
    CandidateJobMatchSortBy,
    CandidateJobMatchSortOrder,
)


SORT_COLUMNS = {
    "overall_score": CandidateJobMatch.overall_score,
    "confidence_score": CandidateJobMatch.confidence_score,
    "matched_at": CandidateJobMatch.matched_at,
    "created_at": CandidateJobMatch.created_at,
}


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
    statement = select(CandidateJobMatch)

    if candidate_id is not None:
        statement = statement.where(
            CandidateJobMatch.candidate_id == candidate_id
        )

    if job_id is not None:
        statement = statement.where(
            CandidateJobMatch.job_id == job_id
        )

    if minimum_score is not None:
        statement = statement.where(
            CandidateJobMatch.overall_score >= minimum_score
        )

    if minimum_confidence is not None:
        statement = statement.where(
            CandidateJobMatch.confidence_score
            >= minimum_confidence
        )

    if recommendation is not None:
        statement = statement.where(
            CandidateJobMatch.recommendation == recommendation
        )

    sort_column = SORT_COLUMNS[sort_by]

    if sort_order == "asc":
        primary_order = sort_column.asc()
    else:
        primary_order = sort_column.desc()

    statement = (
        statement.order_by(
            primary_order,
            CandidateJobMatch.id.asc(),
        )
        .offset(offset)
        .limit(limit)
    )

    return list(
        session.scalars(statement).all()
    )