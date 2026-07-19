from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

from sqlalchemy.orm import Session

from app.parsing.resume_parser import PARSER_VERSION
from app.schemas.resume_profile import ResumeProfileData
from app.services.resume_profile_service import (
    calculate_source_text_sha256,
    parse_resume_profile,
)


def _completed_content(text: str = "Harsha Vardhan") -> SimpleNamespace:
    return SimpleNamespace(
        extraction_status="completed",
        extracted_text=text,
    )


def _completed_profile(text: str = "Harsha Vardhan") -> SimpleNamespace:
    return SimpleNamespace(
        parsing_status="completed",
        source_text_sha256=calculate_source_text_sha256(text),
        parser_version=PARSER_VERSION,
        profile_data={"full_name": "Harsha Vardhan"},
    )


def test_same_hash_and_parser_version_returns_existing_profile() -> None:
    session = MagicMock(spec=Session)
    resume_id = uuid4()
    existing_profile = _completed_profile()

    with patch(
        "app.services.resume_profile_service.get_resume_by_id_record",
        return_value=SimpleNamespace(id=resume_id),
    ), patch(
        "app.services.resume_profile_service.get_resume_content_record",
        return_value=_completed_content(),
    ), patch(
        "app.services.resume_profile_service.get_resume_profile_record",
        return_value=existing_profile,
    ), patch(
        "app.services.resume_profile_service.parse_resume_text",
    ) as parser:
        result = parse_resume_profile(
            session,
            resume_id=resume_id,
            force=False,
        )

    assert result is existing_profile
    parser.assert_not_called()
    session.commit.assert_not_called()
    session.refresh.assert_not_called()


def test_force_true_reparses_same_source() -> None:
    session = MagicMock(spec=Session)
    resume_id = uuid4()
    existing_profile = _completed_profile()
    parsed_data = ResumeProfileData(full_name="Harsha Vardhan")

    with patch(
        "app.services.resume_profile_service.get_resume_by_id_record",
        return_value=SimpleNamespace(id=resume_id),
    ), patch(
        "app.services.resume_profile_service.get_resume_content_record",
        return_value=_completed_content(),
    ), patch(
        "app.services.resume_profile_service.get_resume_profile_record",
        return_value=existing_profile,
    ), patch(
        "app.services.resume_profile_service.parse_resume_text",
        return_value=parsed_data,
    ) as parser, patch(
        "app.services.resume_profile_service.update_resume_profile_record",
        return_value=existing_profile,
    ) as update_record:
        result = parse_resume_profile(
            session,
            resume_id=resume_id,
            force=True,
        )

    assert result is existing_profile
    parser.assert_called_once_with("Harsha Vardhan")
    assert update_record.call_count == 2
    session.commit.assert_called_once_with()
    session.refresh.assert_called_once_with(existing_profile)


def test_source_hash_change_reparses_without_force() -> None:
    session = MagicMock(spec=Session)
    resume_id = uuid4()
    existing_profile = _completed_profile("Old content")
    parsed_data = ResumeProfileData(full_name="Updated Name")

    with patch(
        "app.services.resume_profile_service.get_resume_by_id_record",
        return_value=SimpleNamespace(id=resume_id),
    ), patch(
        "app.services.resume_profile_service.get_resume_content_record",
        return_value=_completed_content("Updated content"),
    ), patch(
        "app.services.resume_profile_service.get_resume_profile_record",
        return_value=existing_profile,
    ), patch(
        "app.services.resume_profile_service.parse_resume_text",
        return_value=parsed_data,
    ) as parser, patch(
        "app.services.resume_profile_service.update_resume_profile_record",
        return_value=existing_profile,
    ):
        parse_resume_profile(
            session,
            resume_id=resume_id,
        )

    parser.assert_called_once_with("Updated content")
    session.commit.assert_called_once_with()


def test_failed_profile_is_reparsed() -> None:
    session = MagicMock(spec=Session)
    resume_id = uuid4()
    failed_profile = _completed_profile()
    failed_profile.parsing_status = "failed"
    parsed_data = ResumeProfileData(full_name="Harsha Vardhan")

    with patch(
        "app.services.resume_profile_service.get_resume_by_id_record",
        return_value=SimpleNamespace(id=resume_id),
    ), patch(
        "app.services.resume_profile_service.get_resume_content_record",
        return_value=_completed_content(),
    ), patch(
        "app.services.resume_profile_service.get_resume_profile_record",
        return_value=failed_profile,
    ), patch(
        "app.services.resume_profile_service.parse_resume_text",
        return_value=parsed_data,
    ) as parser, patch(
        "app.services.resume_profile_service.update_resume_profile_record",
        return_value=failed_profile,
    ):
        parse_resume_profile(
            session,
            resume_id=resume_id,
        )

    parser.assert_called_once()
    session.commit.assert_called_once_with()