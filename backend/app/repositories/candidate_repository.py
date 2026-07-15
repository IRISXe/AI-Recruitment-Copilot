from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.candidate import Candidate
from app.schemas.candidate import CandidateCreate, CandidateUpdate


def create_candidate(
    session: Session,
    payload: CandidateCreate,
) -> Candidate:
    candidate = Candidate(**payload.model_dump())

    session.add(candidate)
    session.flush()

    return candidate


def get_candidate_by_id(
    session: Session,
    candidate_id: UUID,
) -> Candidate | None:
    return session.get(Candidate, candidate_id)


def list_candidates(
    session: Session,
    *,
    offset: int,
    limit: int,
) -> list[Candidate]:
    statement = (
        select(Candidate)
        .order_by(Candidate.created_at.desc())
        .offset(offset)
        .limit(limit)
    )

    return list(session.scalars(statement).all())


def update_candidate(
    session: Session,
    *,
    candidate: Candidate,
    payload: CandidateUpdate,
) -> Candidate:
    update_data = payload.model_dump(exclude_unset=True)

    for field_name, value in update_data.items():
        setattr(candidate, field_name, value)

    session.flush()

    return candidate


def delete_candidate(
    session: Session,
    *,
    candidate: Candidate,
) -> None:
    session.delete(candidate)
    session.flush()