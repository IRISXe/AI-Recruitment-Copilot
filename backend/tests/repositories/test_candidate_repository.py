from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models.candidate import Candidate
from app.repositories.candidate_repository import (
    get_candidate_by_id,
    list_candidates,
)


def build_candidate(
    *,
    full_name: str = "Harsha Vardhan",
    email: str = "harsha@example.com",
) -> Candidate:
    return Candidate(
        full_name=full_name,
        email=email,
        phone="+91 9876543210",
        current_location="Hyderabad",
        current_role="Backend Developer",
        total_experience_months=18,
        skills=["Python", "FastAPI", "PostgreSQL"],
    )


def test_get_candidate_by_id_returns_candidate_or_none(
    db_session: Session,
) -> None:
    candidate = build_candidate()

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


def test_list_candidates_returns_newest_candidates_with_pagination(
    db_session: Session,
) -> None:
    first_candidate = build_candidate(
        full_name="First Candidate",
        email="first@example.com",
    )
    second_candidate = build_candidate(
        full_name="Second Candidate",
        email="second@example.com",
    )
    third_candidate = build_candidate(
        full_name="Third Candidate",
        email="third@example.com",
    )

    db_session.add_all(
        [
            first_candidate,
            second_candidate,
            third_candidate,
        ]
    )
    db_session.flush()

    first_candidate.created_at = datetime(
        9999,
        1,
        1,
        tzinfo=UTC,
    )
    second_candidate.created_at = datetime(
        9999,
        1,
        2,
        tzinfo=UTC,
    )
    third_candidate.created_at = datetime(
        9999,
        1,
        3,
        tzinfo=UTC,
    )

    db_session.flush()

    first_page = list_candidates(
        session=db_session,
        offset=0,
        limit=2,
    )

    second_page = list_candidates(
        session=db_session,
        offset=2,
        limit=1,
    )

    assert [candidate.id for candidate in first_page] == [
        third_candidate.id,
        second_candidate.id,
    ]

    assert [candidate.id for candidate in second_page] == [
        first_candidate.id,
    ]