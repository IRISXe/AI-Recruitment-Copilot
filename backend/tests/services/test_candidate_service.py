from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.models.candidate import Candidate
from app.schemas.candidate import CandidateCreate, CandidateUpdate
from app.services.candidate_service import (
    create_candidate,
    get_candidate_by_id,
    list_candidates,
    update_candidate,
)


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


def test_get_candidate_by_id_returns_existing_candidate() -> None:
    session = MagicMock(spec=Session)
    candidate = MagicMock(spec=Candidate)
    candidate_id = uuid4()

    with patch(
        "app.services.candidate_service.get_candidate_by_id_record",
        return_value=candidate,
    ) as get_record:
        result = get_candidate_by_id(
            session=session,
            candidate_id=candidate_id,
        )

    get_record.assert_called_once_with(session, candidate_id)
    session.rollback.assert_not_called()

    assert result is candidate


def test_get_candidate_by_id_raises_not_found() -> None:
    session = MagicMock(spec=Session)
    candidate_id = uuid4()

    with patch(
        "app.services.candidate_service.get_candidate_by_id_record",
        return_value=None,
    ):
        with pytest.raises(AppException) as exc_info:
            get_candidate_by_id(
                session=session,
                candidate_id=candidate_id,
            )

    session.rollback.assert_not_called()

    assert_app_exception(
        exc_info.value,
        expected_status=status.HTTP_404_NOT_FOUND,
        expected_code="candidate_not_found",
        expected_message="The requested candidate does not exist.",
    )


def test_get_candidate_by_id_rolls_back_database_error() -> None:
    session = MagicMock(spec=Session)
    candidate_id = uuid4()

    with patch(
        "app.services.candidate_service.get_candidate_by_id_record",
        side_effect=SQLAlchemyError("database failure"),
    ):
        with pytest.raises(AppException) as exc_info:
            get_candidate_by_id(
                session=session,
                candidate_id=candidate_id,
            )

    session.rollback.assert_called_once_with()

    assert_app_exception(
        exc_info.value,
        expected_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        expected_code="candidate_retrieval_failed",
        expected_message="The candidate could not be retrieved.",
    )


def test_list_candidates_returns_repository_results() -> None:
    session = MagicMock(spec=Session)
    candidates = [
        MagicMock(spec=Candidate),
        MagicMock(spec=Candidate),
    ]

    with patch(
        "app.services.candidate_service.list_candidates_records",
        return_value=candidates,
    ) as list_records:
        result = list_candidates(
            session=session,
            offset=10,
            limit=20,
        )

    list_records.assert_called_once_with(
        session,
        offset=10,
        limit=20,
    )
    session.rollback.assert_not_called()

    assert result is candidates


def test_list_candidates_rolls_back_database_error() -> None:
    session = MagicMock(spec=Session)

    with patch(
        "app.services.candidate_service.list_candidates_records",
        side_effect=SQLAlchemyError("database failure"),
    ):
        with pytest.raises(AppException) as exc_info:
            list_candidates(
                session=session,
                offset=0,
                limit=20,
            )

    session.rollback.assert_called_once_with()

    assert_app_exception(
        exc_info.value,
        expected_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        expected_code="candidate_listing_failed",
        expected_message="The candidates could not be retrieved.",
    )


def test_update_candidate_commits_refreshes_and_returns_candidate() -> None:
    session = MagicMock(spec=Session)
    candidate_id = uuid4()
    candidate = MagicMock(spec=Candidate)
    updated_candidate = MagicMock(spec=Candidate)
    payload = CandidateUpdate(
        current_role="Senior Backend Developer",
    )

    with patch(
        "app.services.candidate_service.get_candidate_by_id_record",
        return_value=candidate,
    ) as get_record:
        with patch(
            "app.services.candidate_service.update_candidate_record",
            return_value=updated_candidate,
        ) as update_record:
            result = update_candidate(
                session=session,
                candidate_id=candidate_id,
                payload=payload,
            )

    get_record.assert_called_once_with(session, candidate_id)
    update_record.assert_called_once_with(
        session,
        candidate=candidate,
        payload=payload,
    )
    session.commit.assert_called_once_with()
    session.refresh.assert_called_once_with(updated_candidate)
    session.rollback.assert_not_called()

    assert result is updated_candidate


def test_update_candidate_raises_not_found() -> None:
    session = MagicMock(spec=Session)
    candidate_id = uuid4()
    payload = CandidateUpdate(
        current_role="Senior Backend Developer",
    )

    with patch(
        "app.services.candidate_service.get_candidate_by_id_record",
        return_value=None,
    ) as get_record:
        with patch(
            "app.services.candidate_service.update_candidate_record",
        ) as update_record:
            with pytest.raises(AppException) as exc_info:
                update_candidate(
                    session=session,
                    candidate_id=candidate_id,
                    payload=payload,
                )

    get_record.assert_called_once_with(session, candidate_id)
    update_record.assert_not_called()
    session.commit.assert_not_called()
    session.refresh.assert_not_called()
    session.rollback.assert_not_called()

    assert_app_exception(
        exc_info.value,
        expected_status=status.HTTP_404_NOT_FOUND,
        expected_code="candidate_not_found",
        expected_message="The requested candidate does not exist.",
    )


def test_update_candidate_rolls_back_database_error() -> None:
    session = MagicMock(spec=Session)
    candidate_id = uuid4()
    candidate = MagicMock(spec=Candidate)
    payload = CandidateUpdate(
        current_role="Senior Backend Developer",
    )

    with patch(
        "app.services.candidate_service.get_candidate_by_id_record",
        return_value=candidate,
    ):
        with patch(
            "app.services.candidate_service.update_candidate_record",
            side_effect=SQLAlchemyError("database failure"),
        ):
            with pytest.raises(AppException) as exc_info:
                update_candidate(
                    session=session,
                    candidate_id=candidate_id,
                    payload=payload,
                )

    session.rollback.assert_called_once_with()
    session.commit.assert_not_called()
    session.refresh.assert_not_called()

    assert_app_exception(
        exc_info.value,
        expected_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        expected_code="candidate_update_failed",
        expected_message="The candidate could not be updated.",
    )