from unittest.mock import ANY, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.models.resume import Resume
from app.models.resume_content import ResumeContent
from app.models.resume_profile import ResumeProfile
from app.parsing.resume_parser import ResumeParsingError
from app.schemas.resume_profile import ResumeProfileData
from app.services.resume_profile_service import (
    calculate_source_text_sha256,
    get_resume_profile,
    parse_resume_profile,
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


def test_calculate_source_text_sha256_returns_stable_hash() -> None:
    result = calculate_source_text_sha256(
        "resume text"
    )

    assert result == (
        "a8722f53a5b1d3ed2e23f2ecddc927aa"
        "6015a3da6274a3ae4754c40aa232e13f"
    )
    assert len(result) == 64


def test_get_resume_profile_returns_existing_profile() -> None:
    session = MagicMock(spec=Session)
    resume_id = uuid4()

    resume = MagicMock(spec=Resume)
    resume_profile = MagicMock(spec=ResumeProfile)

    with (
        patch(
            "app.services.resume_profile_service."
            "get_resume_by_id_record",
            return_value=resume,
        ) as get_resume,
        patch(
            "app.services.resume_profile_service."
            "get_resume_profile_record",
            return_value=resume_profile,
        ) as get_profile,
    ):
        result = get_resume_profile(
            session=session,
            resume_id=resume_id,
        )

    get_resume.assert_called_once_with(
        session,
        resume_id,
    )
    get_profile.assert_called_once_with(
        session,
        resume_id=resume_id,
    )

    session.rollback.assert_not_called()

    assert result is resume_profile


def test_get_resume_profile_raises_when_resume_does_not_exist(
) -> None:
    session = MagicMock(spec=Session)
    resume_id = uuid4()

    with patch(
        "app.services.resume_profile_service."
        "get_resume_by_id_record",
        return_value=None,
    ):
        with pytest.raises(AppException) as exc_info:
            get_resume_profile(
                session=session,
                resume_id=resume_id,
            )

    session.rollback.assert_not_called()

    assert_app_exception(
        exc_info.value,
        expected_status=status.HTTP_404_NOT_FOUND,
        expected_code="resume_not_found",
        expected_message="The requested resume does not exist.",
    )


def test_get_resume_profile_raises_when_profile_does_not_exist(
) -> None:
    session = MagicMock(spec=Session)
    resume_id = uuid4()

    with (
        patch(
            "app.services.resume_profile_service."
            "get_resume_by_id_record",
            return_value=MagicMock(spec=Resume),
        ),
        patch(
            "app.services.resume_profile_service."
            "get_resume_profile_record",
            return_value=None,
        ),
    ):
        with pytest.raises(AppException) as exc_info:
            get_resume_profile(
                session=session,
                resume_id=resume_id,
            )

    session.rollback.assert_not_called()

    assert_app_exception(
        exc_info.value,
        expected_status=status.HTTP_404_NOT_FOUND,
        expected_code="resume_profile_not_found",
        expected_message=(
            "A structured profile is not available "
            "for this resume."
        ),
    )


def test_get_resume_profile_rolls_back_database_error() -> None:
    session = MagicMock(spec=Session)
    resume_id = uuid4()

    with patch(
        "app.services.resume_profile_service."
        "get_resume_by_id_record",
        side_effect=SQLAlchemyError("database failure"),
    ):
        with pytest.raises(AppException) as exc_info:
            get_resume_profile(
                session=session,
                resume_id=resume_id,
            )

    session.rollback.assert_called_once_with()

    assert_app_exception(
        exc_info.value,
        expected_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        expected_code="resume_profile_retrieval_failed",
        expected_message=(
            "The structured Resume profile "
            "could not be retrieved."
        ),
    )


def test_parse_resume_profile_creates_completed_profile() -> None:
    session = MagicMock(spec=Session)
    resume_id = uuid4()

    resume = MagicMock(spec=Resume)

    resume_content = MagicMock(spec=ResumeContent)
    resume_content.extraction_status = "completed"
    resume_content.extracted_text = """
    Harsha Vardhan
    harsha@example.com
    +91 98765 43210

    Skills
    Python, FastAPI, PostgreSQL
    """

    pending_profile = MagicMock(spec=ResumeProfile)
    completed_profile = MagicMock(spec=ResumeProfile)

    profile_data = ResumeProfileData(
        full_name="Harsha Vardhan",
        email="harsha@example.com",
        phone="+919876543210",
        skills=[
            "FastAPI",
            "PostgreSQL",
            "Python",
        ],
    )

    expected_hash = calculate_source_text_sha256(
        resume_content.extracted_text
    )

    with (
        patch(
            "app.services.resume_profile_service."
            "get_resume_by_id_record",
            return_value=resume,
        ) as get_resume,
        patch(
            "app.services.resume_profile_service."
            "get_resume_content_record",
            return_value=resume_content,
        ) as get_content,
        patch(
            "app.services.resume_profile_service."
            "get_resume_profile_record",
            return_value=None,
        ) as get_profile,
        patch(
            "app.services.resume_profile_service."
            "create_resume_profile_record",
            return_value=pending_profile,
        ) as create_profile,
        patch(
            "app.services.resume_profile_service."
            "parse_resume_text",
            return_value=profile_data,
        ) as parse_text,
        patch(
            "app.services.resume_profile_service."
            "update_resume_profile_record",
            return_value=completed_profile,
        ) as update_profile,
    ):
        result = parse_resume_profile(
            session=session,
            resume_id=resume_id,
        )

    get_resume.assert_called_once_with(
        session,
        resume_id,
    )
    get_content.assert_called_once_with(
        session,
        resume_id=resume_id,
    )
    get_profile.assert_called_once_with(
        session,
        resume_id=resume_id,
    )
    create_profile.assert_called_once_with(
        session,
        resume_id=resume_id,
    )
    parse_text.assert_called_once_with(
        resume_content.extracted_text
    )

    update_profile.assert_called_once_with(
        session,
        resume_profile=pending_profile,
        profile_data=profile_data.model_dump(
            mode="json",
        ),
        parsing_status="completed",
        parsing_error=None,
        parser_version="rule-based-v1",
        source_text_sha256=expected_hash,
        parsed_at=ANY,
    )

    session.commit.assert_called_once_with()
    session.refresh.assert_called_once_with(
        completed_profile
    )
    session.rollback.assert_not_called()

    assert result is completed_profile


def test_parse_resume_profile_resets_existing_profile_before_parsing(
) -> None:
    session = MagicMock(spec=Session)
    resume_id = uuid4()

    resume_content = MagicMock(spec=ResumeContent)
    resume_content.extraction_status = "completed"
    resume_content.extracted_text = (
        "Harsha Vardhan\nPython FastAPI"
    )

    existing_profile = MagicMock(spec=ResumeProfile)
    pending_profile = MagicMock(spec=ResumeProfile)
    completed_profile = MagicMock(spec=ResumeProfile)

    profile_data = ResumeProfileData(
        full_name="Harsha Vardhan",
        skills=[
            "FastAPI",
            "Python",
        ],
    )

    expected_hash = calculate_source_text_sha256(
        resume_content.extracted_text
    )

    with (
        patch(
            "app.services.resume_profile_service."
            "get_resume_by_id_record",
            return_value=MagicMock(spec=Resume),
        ),
        patch(
            "app.services.resume_profile_service."
            "get_resume_content_record",
            return_value=resume_content,
        ),
        patch(
            "app.services.resume_profile_service."
            "get_resume_profile_record",
            return_value=existing_profile,
        ),
        patch(
            "app.services.resume_profile_service."
            "update_resume_profile_record",
            side_effect=[
                pending_profile,
                completed_profile,
            ],
        ) as update_profile,
        patch(
            "app.services.resume_profile_service."
            "parse_resume_text",
            return_value=profile_data,
        ),
    ):
        result = parse_resume_profile(
            session=session,
            resume_id=resume_id,
        )

    assert update_profile.call_count == 2

    first_call = update_profile.call_args_list[0]

    assert first_call.kwargs == {
        "resume_profile": existing_profile,
        "profile_data": None,
        "parsing_status": "pending",
        "parsing_error": None,
        "parser_version": None,
        "source_text_sha256": expected_hash,
        "parsed_at": None,
    }
    assert first_call.args == (
        session,
    )

    session.commit.assert_called_once_with()
    session.refresh.assert_called_once_with(
        completed_profile
    )

    assert result is completed_profile


def test_parse_resume_profile_requires_extracted_content() -> None:
    session = MagicMock(spec=Session)
    resume_id = uuid4()

    with (
        patch(
            "app.services.resume_profile_service."
            "get_resume_by_id_record",
            return_value=MagicMock(spec=Resume),
        ),
        patch(
            "app.services.resume_profile_service."
            "get_resume_content_record",
            return_value=None,
        ),
    ):
        with pytest.raises(AppException) as exc_info:
            parse_resume_profile(
                session=session,
                resume_id=resume_id,
            )

    session.commit.assert_not_called()
    session.rollback.assert_not_called()

    assert_app_exception(
        exc_info.value,
        expected_status=status.HTTP_404_NOT_FOUND,
        expected_code="resume_content_not_found",
        expected_message=(
            "Extracted content is not available "
            "for this resume."
        ),
    )


def test_parse_resume_profile_requires_completed_extraction(
) -> None:
    session = MagicMock(spec=Session)
    resume_id = uuid4()

    resume_content = MagicMock(spec=ResumeContent)
    resume_content.extraction_status = "pending"
    resume_content.extracted_text = None

    with (
        patch(
            "app.services.resume_profile_service."
            "get_resume_by_id_record",
            return_value=MagicMock(spec=Resume),
        ),
        patch(
            "app.services.resume_profile_service."
            "get_resume_content_record",
            return_value=resume_content,
        ),
    ):
        with pytest.raises(AppException) as exc_info:
            parse_resume_profile(
                session=session,
                resume_id=resume_id,
            )

    session.commit.assert_not_called()
    session.rollback.assert_not_called()

    assert_app_exception(
        exc_info.value,
        expected_status=status.HTTP_409_CONFLICT,
        expected_code="resume_content_not_ready",
        expected_message=(
            "Resume extraction must be completed "
            "before parsing."
        ),
    )


@pytest.mark.parametrize(
    "extracted_text",
    [
        None,
        "",
        " \n\t ",
    ],
)
def test_parse_resume_profile_rejects_empty_extracted_content(
    extracted_text: str | None,
) -> None:
    session = MagicMock(spec=Session)
    resume_id = uuid4()

    resume_content = MagicMock(spec=ResumeContent)
    resume_content.extraction_status = "completed"
    resume_content.extracted_text = extracted_text

    with (
        patch(
            "app.services.resume_profile_service."
            "get_resume_by_id_record",
            return_value=MagicMock(spec=Resume),
        ),
        patch(
            "app.services.resume_profile_service."
            "get_resume_content_record",
            return_value=resume_content,
        ),
    ):
        with pytest.raises(AppException) as exc_info:
            parse_resume_profile(
                session=session,
                resume_id=resume_id,
            )

    session.commit.assert_not_called()
    session.rollback.assert_not_called()

    assert_app_exception(
        exc_info.value,
        expected_status=status.HTTP_422_UNPROCESSABLE_CONTENT,
        expected_code="resume_content_empty",
        expected_message=(
            "The extracted Resume content is empty."
        ),
    )


def test_parse_resume_profile_persists_failed_parsing_result(
) -> None:
    session = MagicMock(spec=Session)
    resume_id = uuid4()

    resume_content = MagicMock(spec=ResumeContent)
    resume_content.extraction_status = "completed"
    resume_content.extracted_text = "Resume text"

    pending_profile = MagicMock(spec=ResumeProfile)
    failed_profile = MagicMock(spec=ResumeProfile)

    expected_hash = calculate_source_text_sha256(
        resume_content.extracted_text
    )

    with (
        patch(
            "app.services.resume_profile_service."
            "get_resume_by_id_record",
            return_value=MagicMock(spec=Resume),
        ),
        patch(
            "app.services.resume_profile_service."
            "get_resume_content_record",
            return_value=resume_content,
        ),
        patch(
            "app.services.resume_profile_service."
            "get_resume_profile_record",
            return_value=None,
        ),
        patch(
            "app.services.resume_profile_service."
            "create_resume_profile_record",
            return_value=pending_profile,
        ),
        patch(
            "app.services.resume_profile_service."
            "parse_resume_text",
            side_effect=ResumeParsingError(
                "Resume parsing failed."
            ),
        ),
        patch(
            "app.services.resume_profile_service."
            "update_resume_profile_record",
            return_value=failed_profile,
        ) as update_profile,
    ):
        with pytest.raises(AppException) as exc_info:
            parse_resume_profile(
                session=session,
                resume_id=resume_id,
            )

    update_profile.assert_called_once_with(
        session,
        resume_profile=pending_profile,
        profile_data=None,
        parsing_status="failed",
        parsing_error="Resume parsing failed.",
        parser_version="rule-based-v1",
        source_text_sha256=expected_hash,
        parsed_at=ANY,
    )

    session.commit.assert_called_once_with()
    session.refresh.assert_called_once_with(
        failed_profile
    )
    session.rollback.assert_not_called()

    assert_app_exception(
        exc_info.value,
        expected_status=status.HTTP_422_UNPROCESSABLE_CONTENT,
        expected_code="resume_parsing_failed",
        expected_message=(
            "The Resume could not be parsed "
            "into a structured profile."
        ),
    )


def test_parse_resume_profile_rolls_back_database_error() -> None:
    session = MagicMock(spec=Session)
    resume_id = uuid4()

    with patch(
        "app.services.resume_profile_service."
        "get_resume_by_id_record",
        side_effect=SQLAlchemyError("database failure"),
    ):
        with pytest.raises(AppException) as exc_info:
            parse_resume_profile(
                session=session,
                resume_id=resume_id,
            )

    session.rollback.assert_called_once_with()
    session.commit.assert_not_called()

    assert_app_exception(
        exc_info.value,
        expected_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        expected_code="resume_profile_persistence_failed",
        expected_message=(
            "The structured Resume profile "
            "could not be saved."
        ),
    )