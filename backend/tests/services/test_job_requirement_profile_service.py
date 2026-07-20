from unittest.mock import ANY, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.models.job import Job
from app.models.job_requirement_profile import JobRequirementProfile
from app.parsing.job_description_parser import (
    JobDescriptionParsingError,
)
from app.schemas.job_requirement_profile import (
    JobRequirementProfileData,
)
from app.services.job_requirement_profile_service import (
    calculate_source_description_sha256,
    get_job_requirement_profile,
    parse_job_requirement_profile,
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


def test_calculate_source_description_sha256_returns_stable_hash() -> None:
    result = calculate_source_description_sha256(
        "Backend Engineer job description"
    )

    assert result == (
        "fd6b5a90ed0c6848df974c60a5421be0"
        "4af0f3237cf5ba9e561dc7ea9599a020"
    )
    assert len(result) == 64


def test_get_job_requirement_profile_returns_existing_profile() -> None:
    session = MagicMock(spec=Session)
    job_id = uuid4()

    job = MagicMock(spec=Job)
    profile = MagicMock(spec=JobRequirementProfile)

    with (
        patch(
            "app.services.job_requirement_profile_service."
            "get_job_by_id_record",
            return_value=job,
        ) as get_job,
        patch(
            "app.services.job_requirement_profile_service."
            "get_profile_record",
            return_value=profile,
        ) as get_profile,
    ):
        result = get_job_requirement_profile(
            session=session,
            job_id=job_id,
        )

    get_job.assert_called_once_with(
        session,
        job_id,
    )
    get_profile.assert_called_once_with(
        session,
        job_id=job_id,
    )

    session.rollback.assert_not_called()

    assert result is profile


def test_get_job_requirement_profile_raises_when_job_missing() -> None:
    session = MagicMock(spec=Session)
    job_id = uuid4()

    with patch(
        "app.services.job_requirement_profile_service."
        "get_job_by_id_record",
        return_value=None,
    ):
        with pytest.raises(AppException) as exc_info:
            get_job_requirement_profile(
                session=session,
                job_id=job_id,
            )

    session.rollback.assert_not_called()

    assert_app_exception(
        exc_info.value,
        expected_status=status.HTTP_404_NOT_FOUND,
        expected_code="job_not_found",
        expected_message="The requested job does not exist.",
    )


def test_get_job_requirement_profile_raises_when_profile_missing() -> None:
    session = MagicMock(spec=Session)
    job_id = uuid4()

    with (
        patch(
            "app.services.job_requirement_profile_service."
            "get_job_by_id_record",
            return_value=MagicMock(spec=Job),
        ),
        patch(
            "app.services.job_requirement_profile_service."
            "get_profile_record",
            return_value=None,
        ),
    ):
        with pytest.raises(AppException) as exc_info:
            get_job_requirement_profile(
                session=session,
                job_id=job_id,
            )

    session.rollback.assert_not_called()

    assert_app_exception(
        exc_info.value,
        expected_status=status.HTTP_404_NOT_FOUND,
        expected_code="job_requirement_profile_not_found",
        expected_message=(
            "A structured requirement profile is not "
            "available for this job."
        ),
    )


def test_get_job_requirement_profile_rolls_back_database_error() -> None:
    session = MagicMock(spec=Session)
    job_id = uuid4()

    with patch(
        "app.services.job_requirement_profile_service."
        "get_job_by_id_record",
        side_effect=SQLAlchemyError("database failure"),
    ):
        with pytest.raises(AppException) as exc_info:
            get_job_requirement_profile(
                session=session,
                job_id=job_id,
            )

    session.rollback.assert_called_once_with()

    assert_app_exception(
        exc_info.value,
        expected_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        expected_code="job_requirement_profile_retrieval_failed",
        expected_message=(
            "The structured job requirement profile "
            "could not be retrieved."
        ),
    )


def test_parse_job_requirement_profile_creates_completed_profile() -> None:
    session = MagicMock(spec=Session)
    job_id = uuid4()

    job = MagicMock(spec=Job)
    job.description = (
        "We are hiring a Backend Engineer with Python, "
        "FastAPI, PostgreSQL, and three years of experience."
    )

    pending_profile = MagicMock(spec=JobRequirementProfile)
    completed_profile = MagicMock(spec=JobRequirementProfile)

    profile_data = JobRequirementProfileData(
        job_title="Backend Engineer",
        required_skills=[
            "Python",
            "FastAPI",
            "PostgreSQL",
        ],
        minimum_experience_years=3,
        confidence=0.5,
    )

    expected_hash = calculate_source_description_sha256(
        job.description
    )

    with (
        patch(
            "app.services.job_requirement_profile_service."
            "get_job_by_id_record",
            return_value=job,
        ) as get_job,
        patch(
            "app.services.job_requirement_profile_service."
            "get_profile_record",
            return_value=None,
        ) as get_profile,
        patch(
            "app.services.job_requirement_profile_service."
            "create_profile_record",
            return_value=pending_profile,
        ) as create_profile,
        patch(
            "app.services.job_requirement_profile_service."
            "parse_job_description",
            return_value=profile_data,
        ) as parse_description,
        patch(
            "app.services.job_requirement_profile_service."
            "update_profile_record",
            return_value=completed_profile,
        ) as update_profile,
    ):
        result = parse_job_requirement_profile(
            session=session,
            job_id=job_id,
        )

    get_job.assert_called_once_with(
        session,
        job_id,
    )
    get_profile.assert_called_once_with(
        session,
        job_id=job_id,
    )
    create_profile.assert_called_once_with(
        session,
        job_id=job_id,
    )
    parse_description.assert_called_once_with(
        job.description
    )

    update_profile.assert_called_once_with(
        session,
        profile=pending_profile,
        profile_data=profile_data.model_dump(
            mode="json"
        ),
        parsing_status="completed",
        parsing_error=None,
        parser_version="job-rule-based-v1",
        source_description_sha256=expected_hash,
        parsed_at=ANY,
    )

    session.commit.assert_called_once_with()
    session.refresh.assert_called_once_with(
        completed_profile
    )
    session.rollback.assert_not_called()

    assert result is completed_profile


def test_parse_job_requirement_profile_resets_existing_profile() -> None:
    session = MagicMock(spec=Session)
    job_id = uuid4()

    job = MagicMock(spec=Job)
    job.description = (
        "Backend Engineer role requiring Python and "
        "FastAPI experience for scalable API development."
    )

    existing_profile = MagicMock(spec=JobRequirementProfile)
    pending_profile = MagicMock(spec=JobRequirementProfile)
    completed_profile = MagicMock(spec=JobRequirementProfile)

    profile_data = JobRequirementProfileData(
        job_title="Backend Engineer",
        required_skills=[
            "Python",
            "FastAPI",
        ],
    )

    expected_hash = calculate_source_description_sha256(
        job.description
    )

    with (
        patch(
            "app.services.job_requirement_profile_service."
            "get_job_by_id_record",
            return_value=job,
        ),
        patch(
            "app.services.job_requirement_profile_service."
            "get_profile_record",
            return_value=existing_profile,
        ),
        patch(
            "app.services.job_requirement_profile_service."
            "update_profile_record",
            side_effect=[
                pending_profile,
                completed_profile,
            ],
        ) as update_profile,
        patch(
            "app.services.job_requirement_profile_service."
            "parse_job_description",
            return_value=profile_data,
        ),
    ):
        result = parse_job_requirement_profile(
            session=session,
            job_id=job_id,
        )

    assert update_profile.call_count == 2

    first_call = update_profile.call_args_list[0]

    assert first_call.args == (
        session,
    )
    assert first_call.kwargs == {
        "profile": existing_profile,
        "profile_data": None,
        "parsing_status": "pending",
        "parsing_error": None,
        "parser_version": None,
        "source_description_sha256": expected_hash,
        "parsed_at": None,
    }

    session.commit.assert_called_once_with()
    session.refresh.assert_called_once_with(
        completed_profile
    )

    assert result is completed_profile


@pytest.mark.parametrize(
    "description",
    [
        None,
        "",
        " \n\t ",
    ],
)
def test_parse_job_requirement_profile_rejects_empty_description(
    description: str | None,
) -> None:
    session = MagicMock(spec=Session)
    job_id = uuid4()

    job = MagicMock(spec=Job)
    job.description = description

    with patch(
        "app.services.job_requirement_profile_service."
        "get_job_by_id_record",
        return_value=job,
    ):
        with pytest.raises(AppException) as exc_info:
            parse_job_requirement_profile(
                session=session,
                job_id=job_id,
            )

    session.commit.assert_not_called()
    session.rollback.assert_not_called()

    assert_app_exception(
        exc_info.value,
        expected_status=status.HTTP_422_UNPROCESSABLE_CONTENT,
        expected_code="job_description_empty",
        expected_message=(
            "The job description is empty and "
            "cannot be processed."
        ),
    )


def test_parse_job_requirement_profile_persists_failed_parsing() -> None:
    session = MagicMock(spec=Session)
    job_id = uuid4()

    job = MagicMock(spec=Job)
    job.description = (
        "A job description that cannot be parsed correctly."
    )

    pending_profile = MagicMock(spec=JobRequirementProfile)
    failed_profile = MagicMock(spec=JobRequirementProfile)

    expected_hash = calculate_source_description_sha256(
        job.description
    )

    with (
        patch(
            "app.services.job_requirement_profile_service."
            "get_job_by_id_record",
            return_value=job,
        ),
        patch(
            "app.services.job_requirement_profile_service."
            "get_profile_record",
            return_value=None,
        ),
        patch(
            "app.services.job_requirement_profile_service."
            "create_profile_record",
            return_value=pending_profile,
        ),
        patch(
            "app.services.job_requirement_profile_service."
            "parse_job_description",
            side_effect=JobDescriptionParsingError(
                "Job description parsing failed."
            ),
        ),
        patch(
            "app.services.job_requirement_profile_service."
            "update_profile_record",
            return_value=failed_profile,
        ) as update_profile,
    ):
        with pytest.raises(AppException) as exc_info:
            parse_job_requirement_profile(
                session=session,
                job_id=job_id,
            )

    update_profile.assert_called_once_with(
        session,
        profile=pending_profile,
        profile_data=None,
        parsing_status="failed",
        parsing_error="Job description parsing failed.",
        parser_version="job-rule-based-v1",
        source_description_sha256=expected_hash,
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
        expected_code="job_description_parsing_failed",
        expected_message=(
            "The job description could not be parsed "
            "into structured requirements."
        ),
    )


def test_parse_job_requirement_profile_rolls_back_database_error() -> None:
    session = MagicMock(spec=Session)
    job_id = uuid4()

    with patch(
        "app.services.job_requirement_profile_service."
        "get_job_by_id_record",
        side_effect=SQLAlchemyError("database failure"),
    ):
        with pytest.raises(AppException) as exc_info:
            parse_job_requirement_profile(
                session=session,
                job_id=job_id,
            )

    session.rollback.assert_called_once_with()
    session.commit.assert_not_called()

    assert_app_exception(
        exc_info.value,
        expected_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        expected_code="job_requirement_profile_persistence_failed",
        expected_message=(
            "The structured job requirement profile "
            "could not be saved."
        ),
    )
