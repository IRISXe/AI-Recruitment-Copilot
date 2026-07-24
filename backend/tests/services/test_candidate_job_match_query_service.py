from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.models.candidate import Candidate
from app.models.candidate_job_match import CandidateJobMatch
from app.models.job import Job
from app.services.candidate_job_match_query_service import (
    get_candidate_job_match_by_id,
    list_candidate_job_matches,
    list_candidate_matches_for_job,
    list_job_matches_for_candidate,
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


def test_get_candidate_job_match_by_id_returns_match() -> None:
    session = MagicMock(spec=Session)
    match_id = uuid4()

    candidate_job_match = MagicMock(
        spec=CandidateJobMatch
    )

    with patch(
        "app.services.candidate_job_match_query_service."
        "get_match_record",
        return_value=candidate_job_match,
    ) as get_match:
        result = get_candidate_job_match_by_id(
            session,
            match_id,
        )

    get_match.assert_called_once_with(
        session,
        match_id,
    )

    session.rollback.assert_not_called()

    assert result is candidate_job_match


def test_get_candidate_job_match_by_id_raises_not_found(
) -> None:
    session = MagicMock(spec=Session)
    match_id = uuid4()

    with patch(
        "app.services.candidate_job_match_query_service."
        "get_match_record",
        return_value=None,
    ):
        with pytest.raises(AppException) as exc_info:
            get_candidate_job_match_by_id(
                session,
                match_id,
            )

    session.rollback.assert_not_called()

    assert_app_exception(
        exc_info.value,
        expected_status=status.HTTP_404_NOT_FOUND,
        expected_code="candidate_job_match_not_found",
        expected_message=(
            "The requested Candidate-Job match does not exist."
        ),
    )


def test_get_candidate_job_match_by_id_rolls_back_database_error(
) -> None:
    session = MagicMock(spec=Session)
    match_id = uuid4()

    with patch(
        "app.services.candidate_job_match_query_service."
        "get_match_record",
        side_effect=SQLAlchemyError("database failure"),
    ):
        with pytest.raises(AppException) as exc_info:
            get_candidate_job_match_by_id(
                session,
                match_id,
            )

    session.rollback.assert_called_once_with()

    assert_app_exception(
        exc_info.value,
        expected_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        expected_code="candidate_job_match_retrieval_failed",
        expected_message=(
            "The Candidate-Job match could not be retrieved."
        ),
    )


def test_list_candidate_job_matches_passes_filters() -> None:
    session = MagicMock(spec=Session)

    candidate_id = uuid4()
    job_id = uuid4()

    matches = [
        MagicMock(spec=CandidateJobMatch),
    ]

    with patch(
        "app.services.candidate_job_match_query_service."
        "list_match_records",
        return_value=matches,
    ) as list_records:
        result = list_candidate_job_matches(
            session,
            offset=5,
            limit=10,
            candidate_id=candidate_id,
            job_id=job_id,
            minimum_score=70.0,
            minimum_confidence=60.0,
            recommendation="good_match",
            sort_by="confidence_score",
            sort_order="asc",
        )

    list_records.assert_called_once_with(
        session,
        offset=5,
        limit=10,
        candidate_id=candidate_id,
        job_id=job_id,
        minimum_score=70.0,
        minimum_confidence=60.0,
        recommendation="good_match",
        sort_by="confidence_score",
        sort_order="asc",
    )

    session.rollback.assert_not_called()

    assert result is matches


def test_list_candidate_job_matches_rolls_back_database_error(
) -> None:
    session = MagicMock(spec=Session)

    with patch(
        "app.services.candidate_job_match_query_service."
        "list_match_records",
        side_effect=SQLAlchemyError("database failure"),
    ):
        with pytest.raises(AppException) as exc_info:
            list_candidate_job_matches(
                session,
                offset=0,
                limit=20,
            )

    session.rollback.assert_called_once_with()

    assert_app_exception(
        exc_info.value,
        expected_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        expected_code="candidate_job_match_listing_failed",
        expected_message=(
            "The Candidate-Job matches could not be retrieved."
        ),
    )


def test_list_candidate_matches_for_job_returns_ranked_matches(
) -> None:
    session = MagicMock(spec=Session)
    job_id = uuid4()

    job = MagicMock(spec=Job)

    matches = [
        MagicMock(spec=CandidateJobMatch),
    ]

    with (
        patch(
            "app.services.candidate_job_match_query_service."
            "get_job_record",
            return_value=job,
        ) as get_job,
        patch(
            "app.services.candidate_job_match_query_service."
            "list_match_records",
            return_value=matches,
        ) as list_records,
    ):
        result = list_candidate_matches_for_job(
            session,
            job_id=job_id,
            offset=0,
            limit=20,
            minimum_score=75.0,
            minimum_confidence=65.0,
            recommendation="strong_match",
        )

    get_job.assert_called_once_with(
        session,
        job_id,
    )

    list_records.assert_called_once_with(
        session,
        offset=0,
        limit=20,
        job_id=job_id,
        minimum_score=75.0,
        minimum_confidence=65.0,
        recommendation="strong_match",
        sort_by="overall_score",
        sort_order="desc",
    )

    session.rollback.assert_not_called()

    assert result is matches


def test_list_candidate_matches_for_job_requires_job() -> None:
    session = MagicMock(spec=Session)
    job_id = uuid4()

    with (
        patch(
            "app.services.candidate_job_match_query_service."
            "get_job_record",
            return_value=None,
        ),
        patch(
            "app.services.candidate_job_match_query_service."
            "list_match_records",
        ) as list_records,
    ):
        with pytest.raises(AppException) as exc_info:
            list_candidate_matches_for_job(
                session,
                job_id=job_id,
                offset=0,
                limit=20,
            )

    list_records.assert_not_called()
    session.rollback.assert_not_called()

    assert_app_exception(
        exc_info.value,
        expected_status=status.HTTP_404_NOT_FOUND,
        expected_code="job_not_found",
        expected_message="The requested job does not exist.",
    )


def test_list_candidate_matches_for_job_rolls_back_database_error(
) -> None:
    session = MagicMock(spec=Session)
    job_id = uuid4()

    with patch(
        "app.services.candidate_job_match_query_service."
        "get_job_record",
        side_effect=SQLAlchemyError("database failure"),
    ):
        with pytest.raises(AppException) as exc_info:
            list_candidate_matches_for_job(
                session,
                job_id=job_id,
                offset=0,
                limit=20,
            )

    session.rollback.assert_called_once_with()

    assert_app_exception(
        exc_info.value,
        expected_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        expected_code="candidate_job_match_listing_failed",
        expected_message=(
            "The Candidate-Job matches could not be retrieved."
        ),
    )


def test_list_job_matches_for_candidate_returns_ranked_matches(
) -> None:
    session = MagicMock(spec=Session)
    candidate_id = uuid4()

    candidate = MagicMock(spec=Candidate)

    matches = [
        MagicMock(spec=CandidateJobMatch),
    ]

    with (
        patch(
            "app.services.candidate_job_match_query_service."
            "get_candidate_record",
            return_value=candidate,
        ) as get_candidate,
        patch(
            "app.services.candidate_job_match_query_service."
            "list_match_records",
            return_value=matches,
        ) as list_records,
    ):
        result = list_job_matches_for_candidate(
            session,
            candidate_id=candidate_id,
            offset=0,
            limit=20,
        )

    get_candidate.assert_called_once_with(
        session,
        candidate_id,
    )

    list_records.assert_called_once_with(
        session,
        offset=0,
        limit=20,
        candidate_id=candidate_id,
        minimum_score=None,
        minimum_confidence=None,
        recommendation=None,
        sort_by="overall_score",
        sort_order="desc",
    )

    session.rollback.assert_not_called()

    assert result is matches


def test_list_job_matches_for_candidate_requires_candidate(
) -> None:
    session = MagicMock(spec=Session)
    candidate_id = uuid4()

    with (
        patch(
            "app.services.candidate_job_match_query_service."
            "get_candidate_record",
            return_value=None,
        ),
        patch(
            "app.services.candidate_job_match_query_service."
            "list_match_records",
        ) as list_records,
    ):
        with pytest.raises(AppException) as exc_info:
            list_job_matches_for_candidate(
                session,
                candidate_id=candidate_id,
                offset=0,
                limit=20,
            )

    list_records.assert_not_called()
    session.rollback.assert_not_called()

    assert_app_exception(
        exc_info.value,
        expected_status=status.HTTP_404_NOT_FOUND,
        expected_code="candidate_not_found",
        expected_message=(
            "The requested candidate does not exist."
        ),
    )


def test_list_job_matches_for_candidate_rolls_back_database_error(
) -> None:
    session = MagicMock(spec=Session)
    candidate_id = uuid4()

    with patch(
        "app.services.candidate_job_match_query_service."
        "get_candidate_record",
        side_effect=SQLAlchemyError("database failure"),
    ):
        with pytest.raises(AppException) as exc_info:
            list_job_matches_for_candidate(
                session,
                candidate_id=candidate_id,
                offset=0,
                limit=20,
            )

    session.rollback.assert_called_once_with()

    assert_app_exception(
        exc_info.value,
        expected_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        expected_code="candidate_job_match_listing_failed",
        expected_message=(
            "The Candidate-Job matches could not be retrieved."
        ),
    )