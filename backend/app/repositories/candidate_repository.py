from uuid import UUID

from sqlalchemy.orm import Session

from app.models.candidate import Candidate
from app.schemas.candidate import CandidateCreate


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