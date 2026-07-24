from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.candidate_job_match import CandidateJobMatch
from app.schemas.candidate_job_match import (
    CandidateJobMatchCreate,
    CandidateJobMatchUpdate,
)


def create_candidate_job_match(
    session: Session,
    payload: CandidateJobMatchCreate,
) -> CandidateJobMatch:
    match = CandidateJobMatch(
        **payload.model_dump()
    )

    session.add(match)
    session.flush()

    return match


def get_candidate_job_match_by_id(
    session: Session,
    match_id: UUID,
) -> CandidateJobMatch | None:
    return session.get(
        CandidateJobMatch,
        match_id,
    )


def get_candidate_job_match_by_candidate_and_job(
    session: Session,
    *,
    candidate_id: UUID,
    job_id: UUID,
) -> CandidateJobMatch | None:
    statement = select(CandidateJobMatch).where(
        CandidateJobMatch.candidate_id == candidate_id,
        CandidateJobMatch.job_id == job_id,
    )

    return session.scalar(statement)


def update_candidate_job_match(
    session: Session,
    *,
    match: CandidateJobMatch,
    payload: CandidateJobMatchUpdate,
) -> CandidateJobMatch:
    update_data = payload.model_dump()

    for field_name, value in update_data.items():
        setattr(
            match,
            field_name,
            value,
        )

    session.flush()

    return match


def delete_candidate_job_match(
    session: Session,
    *,
    match: CandidateJobMatch,
) -> None:
    session.delete(match)
    session.flush()