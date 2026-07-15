from uuid import uuid4

from sqlalchemy.orm import Session

from app.models.candidate import Candidate
from app.repositories.candidate_repository import get_candidate_by_id


def test_get_candidate_by_id_returns_candidate_or_none(
    db_session: Session,
) -> None:
    candidate = Candidate(
        full_name="Harsha Vardhan",
        email="harsha@example.com",
        phone="+91 9876543210",
        current_location="Hyderabad",
        current_role="Backend Developer",
        total_experience_months=18,
        skills=["Python", "FastAPI", "PostgreSQL"],
    )

    db_session.add(candidate)
    db_session.flush()

    existing_candidate = get_candidate_by_id(
        session=db_session,
        candidate_id=candidate.id,
    )

    missing_candidate = get_candidate_by_id(
        session=db_session,
        candidate_id=uuid4(),
    )

    assert existing_candidate is not None
    assert existing_candidate.id == candidate.id
    assert existing_candidate.email == "harsha@example.com"
    assert missing_candidate is None