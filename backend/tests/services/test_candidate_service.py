from unittest.mock import MagicMock, patch

import pytest
from fastapi import status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.models.candidate import Candidate
from app.schemas.candidate import CandidateCreate
from app.services.candidate_service import create_candidate


def build_create_payload() -> CandidateCreate:
    return CandidateCreate(
        full_name="Harsha Vardhan",
        email="harsha@example.com",
        phone="+91 9876543210",
        current_location="Hyderabad",
        current_role="Backend Developer",
        total_experience_months=18,
        skills=["Python", "FastAPI", "PostgreSQL"],
    )


def assert_app_exception(
    exception: AppException,
    *,
    expected_status: int,
    expected_code: str,
    expected_message: str,
) -> None:
    assert exception.status_code == expected_status
    assert exception.code == expected_code
    assert exception.message == expected_message


def test_create_candidate_commits_refreshes_and_returns_candidate() -> None:
    session = MagicMock(spec=Session)
    candidate = MagicMock(spec=Candidate)
    payload = build_create_payload()

    with patch(
        "app.services.candidate_service.create_candidate_record",
        return_value=candidate,
    ) as create_record:
        result = create_candidate(
            session=session,
            payload=payload,
        )

    create_record.assert_called_once_with(session, payload)
    session.commit.assert_called_once_with()
    session.refresh.assert_called_once_with(candidate)
    session.rollback.assert_not_called()

    assert result is candidate


def test_create_candidate_rolls_back_database_error() -> None:
    session = MagicMock(spec=Session)
    payload = build_create_payload()

    with patch(
        "app.services.candidate_service.create_candidate_record",
        side_effect=SQLAlchemyError("database failure"),
    ):
        with pytest.raises(AppException) as exc_info:
            create_candidate(
                session=session,
                payload=payload,
            )

    session.rollback.assert_called_once_with()
    session.commit.assert_not_called()
    session.refresh.assert_not_called()

    assert_app_exception(
        exc_info.value,
        expected_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        expected_code="candidate_creation_failed",
        expected_message="The candidate could not be created.",
    )
