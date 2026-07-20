from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

from sqlalchemy.orm import Session

from app.parsing.job_description_parser import PARSER_VERSION
from app.schemas.job_requirement_profile import (
    JobRequirementProfileData,
)
from app.services.job_requirement_profile_service import (
    calculate_source_description_sha256,
    parse_job_requirement_profile,
)


def _job(
    description: str = (
        "Backend Engineer role requiring Python and "
        "FastAPI experience."
    ),
) -> SimpleNamespace:
    return SimpleNamespace(
        description=description,
    )


def _completed_profile(
    description: str = (
        "Backend Engineer role requiring Python and "
        "FastAPI experience."
    ),
) -> SimpleNamespace:
    return SimpleNamespace(
        parsing_status="completed",
        source_description_sha256=(
            calculate_source_description_sha256(
                description
            )
        ),
        parser_version=PARSER_VERSION,
        profile_data={
            "job_title": "Backend Engineer",
            "required_skills": [
                "Python",
                "FastAPI",
            ],
        },
    )


def _parsed_data() -> JobRequirementProfileData:
    return JobRequirementProfileData(
        job_title="Backend Engineer",
        required_skills=[
            "Python",
            "FastAPI",
        ],
        confidence=0.5,
    )


def test_same_hash_and_parser_version_returns_existing_profile() -> None:
    session = MagicMock(spec=Session)
    job_id = uuid4()
    existing_profile = _completed_profile()

    with (
        patch(
            "app.services.job_requirement_profile_service."
            "get_job_by_id_record",
            return_value=_job(),
        ),
        patch(
            "app.services.job_requirement_profile_service."
            "get_profile_record",
            return_value=existing_profile,
        ),
        patch(
            "app.services.job_requirement_profile_service."
            "parse_job_description",
        ) as parser,
        patch(
            "app.services.job_requirement_profile_service."
            "update_profile_record",
        ) as update_record,
    ):
        result = parse_job_requirement_profile(
            session,
            job_id=job_id,
            force=False,
        )

    assert result is existing_profile

    parser.assert_not_called()
    update_record.assert_not_called()

    session.commit.assert_not_called()
    session.refresh.assert_not_called()
    session.rollback.assert_not_called()


def test_force_true_reparses_same_description() -> None:
    session = MagicMock(spec=Session)
    job_id = uuid4()
    existing_profile = _completed_profile()
    parsed_data = _parsed_data()

    with (
        patch(
            "app.services.job_requirement_profile_service."
            "get_job_by_id_record",
            return_value=_job(),
        ),
        patch(
            "app.services.job_requirement_profile_service."
            "get_profile_record",
            return_value=existing_profile,
        ),
        patch(
            "app.services.job_requirement_profile_service."
            "parse_job_description",
            return_value=parsed_data,
        ) as parser,
        patch(
            "app.services.job_requirement_profile_service."
            "update_profile_record",
            return_value=existing_profile,
        ) as update_record,
    ):
        result = parse_job_requirement_profile(
            session,
            job_id=job_id,
            force=True,
        )

    assert result is existing_profile

    parser.assert_called_once_with(
        _job().description
    )
    assert update_record.call_count == 2

    session.commit.assert_called_once_with()
    session.refresh.assert_called_once_with(
        existing_profile
    )


def test_description_hash_change_reparses_without_force() -> None:
    session = MagicMock(spec=Session)
    job_id = uuid4()

    old_description = (
        "Old Backend Engineer description using Python."
    )
    updated_description = (
        "Updated Backend Engineer description using "
        "Python, FastAPI, PostgreSQL, and Docker."
    )

    existing_profile = _completed_profile(
        old_description
    )
    parsed_data = _parsed_data()

    with (
        patch(
            "app.services.job_requirement_profile_service."
            "get_job_by_id_record",
            return_value=_job(updated_description),
        ),
        patch(
            "app.services.job_requirement_profile_service."
            "get_profile_record",
            return_value=existing_profile,
        ),
        patch(
            "app.services.job_requirement_profile_service."
            "parse_job_description",
            return_value=parsed_data,
        ) as parser,
        patch(
            "app.services.job_requirement_profile_service."
            "update_profile_record",
            return_value=existing_profile,
        ),
    ):
        parse_job_requirement_profile(
            session,
            job_id=job_id,
        )

    parser.assert_called_once_with(
        updated_description
    )
    session.commit.assert_called_once_with()
    session.refresh.assert_called_once_with(
        existing_profile
    )


def test_failed_profile_is_reparsed() -> None:
    session = MagicMock(spec=Session)
    job_id = uuid4()

    failed_profile = _completed_profile()
    failed_profile.parsing_status = "failed"

    parsed_data = _parsed_data()

    with (
        patch(
            "app.services.job_requirement_profile_service."
            "get_job_by_id_record",
            return_value=_job(),
        ),
        patch(
            "app.services.job_requirement_profile_service."
            "get_profile_record",
            return_value=failed_profile,
        ),
        patch(
            "app.services.job_requirement_profile_service."
            "parse_job_description",
            return_value=parsed_data,
        ) as parser,
        patch(
            "app.services.job_requirement_profile_service."
            "update_profile_record",
            return_value=failed_profile,
        ),
    ):
        parse_job_requirement_profile(
            session,
            job_id=job_id,
        )

    parser.assert_called_once()
    session.commit.assert_called_once_with()
    session.refresh.assert_called_once_with(
        failed_profile
    )


def test_parser_version_change_reparses_without_force() -> None:
    session = MagicMock(spec=Session)
    job_id = uuid4()

    existing_profile = _completed_profile()
    existing_profile.parser_version = "job-rule-based-v0"

    parsed_data = _parsed_data()

    with (
        patch(
            "app.services.job_requirement_profile_service."
            "get_job_by_id_record",
            return_value=_job(),
        ),
        patch(
            "app.services.job_requirement_profile_service."
            "get_profile_record",
            return_value=existing_profile,
        ),
        patch(
            "app.services.job_requirement_profile_service."
            "parse_job_description",
            return_value=parsed_data,
        ) as parser,
        patch(
            "app.services.job_requirement_profile_service."
            "update_profile_record",
            return_value=existing_profile,
        ),
    ):
        parse_job_requirement_profile(
            session,
            job_id=job_id,
            force=False,
        )

    parser.assert_called_once()
    session.commit.assert_called_once_with()
    session.refresh.assert_called_once_with(
        existing_profile
    )