from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.models.resume import Resume
from app.models.resume_content import ResumeContent
from app.services.resume_content_service import (
    get_resume_content,
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


def test_get_resume_content_returns_existing_content() -> None:
    session = MagicMock(spec=Session)
    resume = MagicMock(spec=Resume)
    resume_content = MagicMock(spec=ResumeContent)
    resume_id = uuid4()

    with patch(
        "app.services.resume_content_service."
        "get_resume_by_id_record",
        return_value=resume,
    ) as get_resume_record:
        with patch(
            "app.services.resume_content_service."
            "get_resume_content_record",
            return_value=resume_content,
        ) as get_content_record:
            result = get_resume_content(
                session=session,
                resume_id=resume_id,
            )

    get_resume_record.assert_called_once_with(
        session,
        resume_id,
    )

    get_content_record.assert_called_once_with(
        session,
        resume_id=resume_id,
    )

    session.commit.assert_not_called()
    session.rollback.assert_not_called()
    session.refresh.assert_not_called()

    assert result is resume_content


def test_get_resume_content_raises_when_resume_missing() -> None:
    session = MagicMock(spec=Session)
    resume_id = uuid4()

    with patch(
        "app.services.resume_content_service."
        "get_resume_by_id_record",
        return_value=None,
    ) as get_resume_record:
        with patch(
            "app.services.resume_content_service."
            "get_resume_content_record",
        ) as get_content_record:
            with pytest.raises(AppException) as exc_info:
                get_resume_content(
                    session=session,
                    resume_id=resume_id,
                )

    get_resume_record.assert_called_once_with(
        session,
        resume_id,
    )
    get_content_record.assert_not_called()

    session.commit.assert_not_called()
    session.rollback.assert_not_called()
    session.refresh.assert_not_called()

    assert_app_exception(
        exc_info.value,
        expected_status=status.HTTP_404_NOT_FOUND,
        expected_code="resume_not_found",
        expected_message=(
            "The requested resume does not exist."
        ),
    )


def test_get_resume_content_raises_when_content_missing() -> None:
    session = MagicMock(spec=Session)
    resume = MagicMock(spec=Resume)
    resume_id = uuid4()

    with patch(
        "app.services.resume_content_service."
        "get_resume_by_id_record",
        return_value=resume,
    ):
        with patch(
            "app.services.resume_content_service."
            "get_resume_content_record",
            return_value=None,
        ) as get_content_record:
            with pytest.raises(AppException) as exc_info:
                get_resume_content(
                    session=session,
                    resume_id=resume_id,
                )

    get_content_record.assert_called_once_with(
        session,
        resume_id=resume_id,
    )

    session.commit.assert_not_called()
    session.rollback.assert_not_called()
    session.refresh.assert_not_called()

    assert_app_exception(
        exc_info.value,
        expected_status=status.HTTP_404_NOT_FOUND,
        expected_code="resume_content_not_found",
        expected_message=(
            "Extracted content is not available "
            "for this resume."
        ),
    )


def test_get_resume_content_rolls_back_resume_lookup_error() -> None:
    session = MagicMock(spec=Session)
    resume_id = uuid4()

    with patch(
        "app.services.resume_content_service."
        "get_resume_by_id_record",
        side_effect=SQLAlchemyError(
            "database failure"
        ),
    ):
        with pytest.raises(AppException) as exc_info:
            get_resume_content(
                session=session,
                resume_id=resume_id,
            )

    session.rollback.assert_called_once_with()
    session.commit.assert_not_called()
    session.refresh.assert_not_called()

    assert_app_exception(
        exc_info.value,
        expected_status=(
            status.HTTP_500_INTERNAL_SERVER_ERROR
        ),
        expected_code="resume_content_retrieval_failed",
        expected_message=(
            "The extracted Resume content "
            "could not be retrieved."
        ),
    )


def test_get_resume_content_rolls_back_content_lookup_error() -> None:
    session = MagicMock(spec=Session)
    resume = MagicMock(spec=Resume)
    resume_id = uuid4()

    with patch(
        "app.services.resume_content_service."
        "get_resume_by_id_record",
        return_value=resume,
    ):
        with patch(
            "app.services.resume_content_service."
            "get_resume_content_record",
            side_effect=SQLAlchemyError(
                "database failure"
            ),
        ):
            with pytest.raises(AppException) as exc_info:
                get_resume_content(
                    session=session,
                    resume_id=resume_id,
                )

    session.rollback.assert_called_once_with()
    session.commit.assert_not_called()
    session.refresh.assert_not_called()

    assert_app_exception(
        exc_info.value,
        expected_status=(
            status.HTTP_500_INTERNAL_SERVER_ERROR
        ),
        expected_code="resume_content_retrieval_failed",
        expected_message=(
            "The extracted Resume content "
            "could not be retrieved."
        ),
    )