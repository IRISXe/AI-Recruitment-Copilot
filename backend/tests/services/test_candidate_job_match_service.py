from datetime import UTC, datetime
from unittest.mock import ANY, MagicMock, patch
from uuid import UUID, uuid4

from sqlalchemy.exc import SQLAlchemyError

import pytest
from fastapi import status
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from sqlalchemy.orm import Session

from app.matching.candidate_job_matcher import (
    SCORING_VERSION,
)
from app.models.candidate import Candidate
from app.models.candidate_job_match import CandidateJobMatch
from app.models.job import Job
from app.models.job_requirement_profile import (
    JobRequirementProfile,
)
from app.models.resume import Resume
from app.models.resume_profile import ResumeProfile
from app.schemas.candidate_job_match import (
    CandidateJobMatchCreate,
)
from app.schemas.job_requirement_profile import (
    JobRequirementProfileData,
)
from app.schemas.resume_profile import ResumeProfileData
from app.services.candidate_job_match_service import (
    generate_candidate_job_match,
)


def _build_completed_matching_inputs() -> tuple[
    UUID,
    UUID,
    Candidate,
    Job,
    Resume,
    ResumeProfile,
    JobRequirementProfile,
    ResumeProfileData,
    JobRequirementProfileData,
]:
    candidate_id = uuid4()
    job_id = uuid4()
    resume_id = uuid4()
    resume_profile_id = uuid4()
    job_profile_id = uuid4()

    now = datetime(
        2026,
        7,
        20,
        12,
        0,
        tzinfo=UTC,
    )

    candidate = MagicMock(spec=Candidate)
    candidate.id = candidate_id

    job = MagicMock(spec=Job)
    job.id = job_id

    primary_resume = MagicMock(spec=Resume)
    primary_resume.id = resume_id
    primary_resume.candidate_id = candidate_id
    primary_resume.is_primary = True

    resume_data = ResumeProfileData(
        full_name="Harsha Vardhan",
        location="Bangalore",
        total_experience_months=30,
        skills=[
            "React.js",
            "PostgreSQL",
            "AWS",
        ],
        confidence=0.90,
    )

    resume_profile = MagicMock(spec=ResumeProfile)
    resume_profile.id = resume_profile_id
    resume_profile.resume_id = resume_id
    resume_profile.profile_data = resume_data.model_dump(
        mode="json"
    )
    resume_profile.parsing_status = "completed"
    resume_profile.parsing_error = None
    resume_profile.parser_version = "resume-parser-v1"
    resume_profile.source_text_sha256 = "a" * 64
    resume_profile.parsed_at = now
    resume_profile.created_at = now
    resume_profile.updated_at = now

    job_data = JobRequirementProfileData(
        job_title="Frontend Engineer",
        location="Bengaluru, Karnataka",
        work_mode="hybrid",
        required_skills=[
            "React",
            "PostgreSQL",
        ],
        preferred_skills=[
            "AWS",
            "Docker",
        ],
        confidence=0.80,
    )

    job_profile = MagicMock(
        spec=JobRequirementProfile
    )
    job_profile.id = job_profile_id
    job_profile.job_id = job_id
    job_profile.profile_data = job_data.model_dump(
        mode="json"
    )
    job_profile.parsing_status = "completed"
    job_profile.parsing_error = None
    job_profile.parser_version = "job-parser-v1"
    job_profile.source_description_sha256 = "b" * 64
    job_profile.parsed_at = now
    job_profile.created_at = now
    job_profile.updated_at = now

    return (
        candidate_id,
        job_id,
        candidate,
        job,
        primary_resume,
        resume_profile,
        job_profile,
        resume_data,
        job_data,
    )


def test_generate_candidate_job_match_creates_new_match(
) -> None:
    session = MagicMock(spec=Session)

    (
        candidate_id,
        job_id,
        candidate,
        job,
        primary_resume,
        resume_profile,
        job_profile,
        resume_data,
        job_data,
    ) = _build_completed_matching_inputs()

    computation = MagicMock()
    create_payload = MagicMock(
        spec=CandidateJobMatchCreate
    )
    persisted_match = MagicMock(
        spec=CandidateJobMatch
    )

    with (
        patch(
            "app.services.candidate_job_match_service."
            "get_candidate_record",
            return_value=candidate,
        ) as get_candidate,
        patch(
            "app.services.candidate_job_match_service."
            "get_job_record",
            return_value=job,
        ) as get_job,
        patch(
            "app.services.candidate_job_match_service."
            "get_primary_resume_record",
            return_value=primary_resume,
        ) as get_primary_resume,
        patch(
            "app.services.candidate_job_match_service."
            "get_resume_profile_record",
            return_value=resume_profile,
        ) as get_resume_profile,
        patch(
            "app.services.candidate_job_match_service."
            "get_job_profile_record",
            return_value=job_profile,
        ) as get_job_profile,
        patch(
            "app.services.candidate_job_match_service."
            "get_match_record",
            return_value=None,
        ) as get_match,
        patch(
            "app.services.candidate_job_match_service."
            "match_candidate_profile_to_job_requirements",
            return_value=computation,
        ) as calculate_match,
        patch(
            "app.services.candidate_job_match_service."
            "build_candidate_job_match_create",
            return_value=create_payload,
        ) as build_payload,
        patch(
            "app.services.candidate_job_match_service."
            "create_match_record",
            return_value=persisted_match,
        ) as create_match,
        patch(
            "app.services.candidate_job_match_service."
            "update_match_record",
        ) as update_match,
    ):
        result = generate_candidate_job_match(
            session=session,
            candidate_id=candidate_id,
            job_id=job_id,
        )

    get_candidate.assert_called_once_with(
        session,
        candidate_id,
    )
    get_job.assert_called_once_with(
        session,
        job_id,
    )
    get_primary_resume.assert_called_once_with(
        session,
        candidate_id,
    )
    get_resume_profile.assert_called_once_with(
        session,
        resume_id=primary_resume.id,
    )
    get_job_profile.assert_called_once_with(
        session,
        job_id=job_id,
    )
    get_match.assert_called_once_with(
        session,
        candidate_id=candidate_id,
        job_id=job_id,
    )

    calculate_match.assert_called_once_with(
        resume_profile=resume_data,
        job_requirement_profile=job_data,
        candidate_work_mode=None,
    )

    build_payload.assert_called_once_with(
        candidate_id=candidate_id,
        job_id=job_id,
        resume_profile=ANY,
        job_requirement_profile=ANY,
        computation=computation,
        matched_at=ANY,
    )

    create_match.assert_called_once_with(
        session,
        create_payload,
    )
    update_match.assert_not_called()

    session.commit.assert_called_once_with()
    session.refresh.assert_called_once_with(
        persisted_match
    )
    session.rollback.assert_not_called()

    assert result is persisted_match


def test_generate_candidate_job_match_returns_current_match(
) -> None:
    session = MagicMock(spec=Session)

    (
        candidate_id,
        job_id,
        candidate,
        job,
        primary_resume,
        resume_profile,
        job_profile,
        _,
        _,
    ) = _build_completed_matching_inputs()

    existing_match = MagicMock(
        spec=CandidateJobMatch
    )
    existing_match.resume_id = (
        resume_profile.resume_id
    )
    existing_match.resume_profile_id = (
        resume_profile.id
    )
    existing_match.job_requirement_profile_id = (
        job_profile.id
    )
    existing_match.scoring_version = SCORING_VERSION
    existing_match.source_resume_text_sha256 = (
        resume_profile.source_text_sha256
    )
    existing_match.source_resume_parser_version = (
        resume_profile.parser_version
    )
    existing_match.source_job_description_sha256 = (
        job_profile.source_description_sha256
    )
    existing_match.source_job_parser_version = (
        job_profile.parser_version
    )

    with (
        patch(
            "app.services.candidate_job_match_service."
            "get_candidate_record",
            return_value=candidate,
        ),
        patch(
            "app.services.candidate_job_match_service."
            "get_job_record",
            return_value=job,
        ),
        patch(
            "app.services.candidate_job_match_service."
            "get_primary_resume_record",
            return_value=primary_resume,
        ),
        patch(
            "app.services.candidate_job_match_service."
            "get_resume_profile_record",
            return_value=resume_profile,
        ),
        patch(
            "app.services.candidate_job_match_service."
            "get_job_profile_record",
            return_value=job_profile,
        ),
        patch(
            "app.services.candidate_job_match_service."
            "get_match_record",
            return_value=existing_match,
        ),
        patch(
            "app.services.candidate_job_match_service."
            "match_candidate_profile_to_job_requirements",
        ) as calculate_match,
        patch(
            "app.services.candidate_job_match_service."
            "build_candidate_job_match_create",
        ) as build_payload,
        patch(
            "app.services.candidate_job_match_service."
            "create_match_record",
        ) as create_match,
        patch(
            "app.services.candidate_job_match_service."
            "update_match_record",
        ) as update_match,
    ):
        result = generate_candidate_job_match(
            session=session,
            candidate_id=candidate_id,
            job_id=job_id,
        )

    calculate_match.assert_not_called()
    build_payload.assert_not_called()
    create_match.assert_not_called()
    update_match.assert_not_called()

    session.commit.assert_not_called()
    session.refresh.assert_not_called()
    session.rollback.assert_not_called()

    assert result is existing_match

def _make_existing_match_current(
    *,
    existing_match: CandidateJobMatch,
    resume_profile: ResumeProfile,
    job_profile: JobRequirementProfile,
) -> None:
    existing_match.resume_id = resume_profile.resume_id
    existing_match.resume_profile_id = resume_profile.id
    existing_match.job_requirement_profile_id = job_profile.id
    existing_match.scoring_version = SCORING_VERSION
    existing_match.source_resume_text_sha256 = (
        resume_profile.source_text_sha256
    )
    existing_match.source_resume_parser_version = (
        resume_profile.parser_version
    )
    existing_match.source_job_description_sha256 = (
        job_profile.source_description_sha256
    )
    existing_match.source_job_parser_version = (
        job_profile.parser_version
    )


def test_generate_candidate_job_match_updates_stale_match(
) -> None:
    session = MagicMock(spec=Session)

    (
        candidate_id,
        job_id,
        candidate,
        job,
        primary_resume,
        resume_profile,
        job_profile,
        resume_data,
        job_data,
    ) = _build_completed_matching_inputs()

    existing_match = MagicMock(
        spec=CandidateJobMatch
    )
    _make_existing_match_current(
        existing_match=existing_match,
        resume_profile=resume_profile,
        job_profile=job_profile,
    )
    existing_match.scoring_version = "old-scoring-version"

    computation = MagicMock()
    create_payload = MagicMock(
        spec=CandidateJobMatchCreate
    )
    create_payload.model_dump.return_value = {
        "overall_score": 85.0,
    }

    update_payload = MagicMock()
    updated_match = MagicMock(
        spec=CandidateJobMatch
    )

    with (
        patch(
            "app.services.candidate_job_match_service."
            "get_candidate_record",
            return_value=candidate,
        ),
        patch(
            "app.services.candidate_job_match_service."
            "get_job_record",
            return_value=job,
        ),
        patch(
            "app.services.candidate_job_match_service."
            "get_primary_resume_record",
            return_value=primary_resume,
        ),
        patch(
            "app.services.candidate_job_match_service."
            "get_resume_profile_record",
            return_value=resume_profile,
        ),
        patch(
            "app.services.candidate_job_match_service."
            "get_job_profile_record",
            return_value=job_profile,
        ),
        patch(
            "app.services.candidate_job_match_service."
            "get_match_record",
            return_value=existing_match,
        ),
        patch(
            "app.services.candidate_job_match_service."
            "match_candidate_profile_to_job_requirements",
            return_value=computation,
        ) as calculate_match,
        patch(
            "app.services.candidate_job_match_service."
            "build_candidate_job_match_create",
            return_value=create_payload,
        ) as build_payload,
        patch(
            "app.services.candidate_job_match_service."
            "CandidateJobMatchUpdate",
            return_value=update_payload,
        ) as build_update_payload,
        patch(
            "app.services.candidate_job_match_service."
            "create_match_record",
        ) as create_match,
        patch(
            "app.services.candidate_job_match_service."
            "update_match_record",
            return_value=updated_match,
        ) as update_match,
    ):
        result = generate_candidate_job_match(
            session=session,
            candidate_id=candidate_id,
            job_id=job_id,
        )

    calculate_match.assert_called_once_with(
        resume_profile=resume_data,
        job_requirement_profile=job_data,
        candidate_work_mode=None,
    )
    build_payload.assert_called_once()

    create_payload.model_dump.assert_called_once_with(
        exclude={
            "candidate_id",
            "job_id",
        }
    )
    build_update_payload.assert_called_once_with(
        overall_score=85.0,
    )

    create_match.assert_not_called()
    update_match.assert_called_once_with(
        session,
        match=existing_match,
        payload=update_payload,
    )

    session.commit.assert_called_once_with()
    session.refresh.assert_called_once_with(
        updated_match
    )
    session.rollback.assert_not_called()

    assert result is updated_match


def test_generate_candidate_job_match_force_recomputes_current_match(
) -> None:
    session = MagicMock(spec=Session)

    (
        candidate_id,
        job_id,
        candidate,
        job,
        primary_resume,
        resume_profile,
        job_profile,
        _,
        _,
    ) = _build_completed_matching_inputs()

    existing_match = MagicMock(
        spec=CandidateJobMatch
    )
    _make_existing_match_current(
        existing_match=existing_match,
        resume_profile=resume_profile,
        job_profile=job_profile,
    )

    computation = MagicMock()
    create_payload = MagicMock(
        spec=CandidateJobMatchCreate
    )
    create_payload.model_dump.return_value = {
        "overall_score": 90.0,
    }

    update_payload = MagicMock()
    updated_match = MagicMock(
        spec=CandidateJobMatch
    )

    with (
        patch(
            "app.services.candidate_job_match_service."
            "get_candidate_record",
            return_value=candidate,
        ),
        patch(
            "app.services.candidate_job_match_service."
            "get_job_record",
            return_value=job,
        ),
        patch(
            "app.services.candidate_job_match_service."
            "get_primary_resume_record",
            return_value=primary_resume,
        ),
        patch(
            "app.services.candidate_job_match_service."
            "get_resume_profile_record",
            return_value=resume_profile,
        ),
        patch(
            "app.services.candidate_job_match_service."
            "get_job_profile_record",
            return_value=job_profile,
        ),
        patch(
            "app.services.candidate_job_match_service."
            "get_match_record",
            return_value=existing_match,
        ),
        patch(
            "app.services.candidate_job_match_service."
            "match_candidate_profile_to_job_requirements",
            return_value=computation,
        ) as calculate_match,
        patch(
            "app.services.candidate_job_match_service."
            "build_candidate_job_match_create",
            return_value=create_payload,
        ),
        patch(
            "app.services.candidate_job_match_service."
            "CandidateJobMatchUpdate",
            return_value=update_payload,
        ),
        patch(
            "app.services.candidate_job_match_service."
            "update_match_record",
            return_value=updated_match,
        ) as update_match,
    ):
        result = generate_candidate_job_match(
            session=session,
            candidate_id=candidate_id,
            job_id=job_id,
            force=True,
        )

    calculate_match.assert_called_once()
    update_match.assert_called_once_with(
        session,
        match=existing_match,
        payload=update_payload,
    )

    session.commit.assert_called_once_with()
    session.refresh.assert_called_once_with(
        updated_match
    )
    session.rollback.assert_not_called()

    assert result is updated_match
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

def test_generate_candidate_job_match_requires_candidate() -> None:
    session = MagicMock(spec=Session)
    candidate_id = uuid4()
    job_id = uuid4()

    with (
        patch(
            "app.services.candidate_job_match_service."
            "get_candidate_record",
            return_value=None,
        ) as get_candidate,
        patch(
            "app.services.candidate_job_match_service."
            "get_job_record",
        ) as get_job,
        patch(
            "app.services.candidate_job_match_service."
            "get_primary_resume_record",
        ) as get_primary_resume,
    ):
        with pytest.raises(AppException) as exc_info:
            generate_candidate_job_match(
                session=session,
                candidate_id=candidate_id,
                job_id=job_id,
            )

    get_candidate.assert_called_once_with(
        session,
        candidate_id,
    )
    get_job.assert_not_called()
    get_primary_resume.assert_not_called()

    session.commit.assert_not_called()
    session.refresh.assert_not_called()
    session.rollback.assert_not_called()

    assert_app_exception(
        exc_info.value,
        expected_status=status.HTTP_404_NOT_FOUND,
        expected_code="candidate_not_found",
        expected_message=(
            "The requested candidate does not exist."
        ),
    )


def test_generate_candidate_job_match_requires_job() -> None:
    session = MagicMock(spec=Session)
    candidate_id = uuid4()
    job_id = uuid4()

    candidate = MagicMock(spec=Candidate)

    with (
        patch(
            "app.services.candidate_job_match_service."
            "get_candidate_record",
            return_value=candidate,
        ) as get_candidate,
        patch(
            "app.services.candidate_job_match_service."
            "get_job_record",
            return_value=None,
        ) as get_job,
        patch(
            "app.services.candidate_job_match_service."
            "get_primary_resume_record",
        ) as get_primary_resume,
    ):
        with pytest.raises(AppException) as exc_info:
            generate_candidate_job_match(
                session=session,
                candidate_id=candidate_id,
                job_id=job_id,
            )

    get_candidate.assert_called_once_with(
        session,
        candidate_id,
    )
    get_job.assert_called_once_with(
        session,
        job_id,
    )
    get_primary_resume.assert_not_called()

    session.commit.assert_not_called()
    session.refresh.assert_not_called()
    session.rollback.assert_not_called()

    assert_app_exception(
        exc_info.value,
        expected_status=status.HTTP_404_NOT_FOUND,
        expected_code="job_not_found",
        expected_message="The requested job does not exist.",
    )


def test_generate_candidate_job_match_requires_primary_resume(
) -> None:
    session = MagicMock(spec=Session)
    candidate_id = uuid4()
    job_id = uuid4()

    candidate = MagicMock(spec=Candidate)
    job = MagicMock(spec=Job)

    with (
        patch(
            "app.services.candidate_job_match_service."
            "get_candidate_record",
            return_value=candidate,
        ),
        patch(
            "app.services.candidate_job_match_service."
            "get_job_record",
            return_value=job,
        ),
        patch(
            "app.services.candidate_job_match_service."
            "get_primary_resume_record",
            return_value=None,
        ) as get_primary_resume,
        patch(
            "app.services.candidate_job_match_service."
            "get_resume_profile_record",
        ) as get_resume_profile,
    ):
        with pytest.raises(AppException) as exc_info:
            generate_candidate_job_match(
                session=session,
                candidate_id=candidate_id,
                job_id=job_id,
            )

    get_primary_resume.assert_called_once_with(
        session,
        candidate_id,
    )
    get_resume_profile.assert_not_called()

    session.commit.assert_not_called()
    session.refresh.assert_not_called()
    session.rollback.assert_not_called()

    assert_app_exception(
        exc_info.value,
        expected_status=status.HTTP_409_CONFLICT,
        expected_code="primary_resume_not_found",
        expected_message=(
            "The candidate must have an explicitly selected "
            "primary Resume before matching."
        ),
    )
def test_generate_candidate_job_match_requires_resume_profile(
) -> None:
    session = MagicMock(spec=Session)

    (
        candidate_id,
        job_id,
        candidate,
        job,
        primary_resume,
        _,
        _,
        _,
        _,
    ) = _build_completed_matching_inputs()

    with (
        patch(
            "app.services.candidate_job_match_service."
            "get_candidate_record",
            return_value=candidate,
        ),
        patch(
            "app.services.candidate_job_match_service."
            "get_job_record",
            return_value=job,
        ),
        patch(
            "app.services.candidate_job_match_service."
            "get_primary_resume_record",
            return_value=primary_resume,
        ),
        patch(
            "app.services.candidate_job_match_service."
            "get_resume_profile_record",
            return_value=None,
        ) as get_resume_profile,
        patch(
            "app.services.candidate_job_match_service."
            "get_job_profile_record",
        ) as get_job_profile,
    ):
        with pytest.raises(AppException) as exc_info:
            generate_candidate_job_match(
                session=session,
                candidate_id=candidate_id,
                job_id=job_id,
            )

    get_resume_profile.assert_called_once_with(
        session,
        resume_id=primary_resume.id,
    )
    get_job_profile.assert_not_called()

    session.commit.assert_not_called()
    session.refresh.assert_not_called()
    session.rollback.assert_not_called()

    assert_app_exception(
        exc_info.value,
        expected_status=status.HTTP_404_NOT_FOUND,
        expected_code="resume_profile_not_found",
        expected_message=(
            "A structured profile is not available for "
            "the candidate's primary Resume."
        ),
    )


@pytest.mark.parametrize(
    (
        "field_name",
        "invalid_value",
    ),
    [
        (
            "parsing_status",
            "pending",
        ),
        (
            "profile_data",
            None,
        ),
        (
            "parser_version",
            None,
        ),
        (
            "source_text_sha256",
            None,
        ),
    ],
)
def test_generate_candidate_job_match_requires_ready_resume_profile(
    field_name: str,
    invalid_value: object,
) -> None:
    session = MagicMock(spec=Session)

    (
        candidate_id,
        job_id,
        candidate,
        job,
        primary_resume,
        resume_profile,
        _,
        _,
        _,
    ) = _build_completed_matching_inputs()

    setattr(
        resume_profile,
        field_name,
        invalid_value,
    )

    with (
        patch(
            "app.services.candidate_job_match_service."
            "get_candidate_record",
            return_value=candidate,
        ),
        patch(
            "app.services.candidate_job_match_service."
            "get_job_record",
            return_value=job,
        ),
        patch(
            "app.services.candidate_job_match_service."
            "get_primary_resume_record",
            return_value=primary_resume,
        ),
        patch(
            "app.services.candidate_job_match_service."
            "get_resume_profile_record",
            return_value=resume_profile,
        ),
        patch(
            "app.services.candidate_job_match_service."
            "get_job_profile_record",
        ) as get_job_profile,
    ):
        with pytest.raises(AppException) as exc_info:
            generate_candidate_job_match(
                session=session,
                candidate_id=candidate_id,
                job_id=job_id,
            )

    get_job_profile.assert_not_called()

    session.commit.assert_not_called()
    session.refresh.assert_not_called()
    session.rollback.assert_not_called()

    assert_app_exception(
        exc_info.value,
        expected_status=status.HTTP_409_CONFLICT,
        expected_code="resume_profile_not_ready",
        expected_message=(
            "The candidate's primary Resume must have a "
            "completed structured profile before matching."
        ),
    )


def test_generate_candidate_job_match_requires_job_profile(
) -> None:
    session = MagicMock(spec=Session)

    (
        candidate_id,
        job_id,
        candidate,
        job,
        primary_resume,
        resume_profile,
        _,
        _,
        _,
    ) = _build_completed_matching_inputs()

    with (
        patch(
            "app.services.candidate_job_match_service."
            "get_candidate_record",
            return_value=candidate,
        ),
        patch(
            "app.services.candidate_job_match_service."
            "get_job_record",
            return_value=job,
        ),
        patch(
            "app.services.candidate_job_match_service."
            "get_primary_resume_record",
            return_value=primary_resume,
        ),
        patch(
            "app.services.candidate_job_match_service."
            "get_resume_profile_record",
            return_value=resume_profile,
        ),
        patch(
            "app.services.candidate_job_match_service."
            "get_job_profile_record",
            return_value=None,
        ) as get_job_profile,
        patch(
            "app.services.candidate_job_match_service."
            "get_match_record",
        ) as get_match,
    ):
        with pytest.raises(AppException) as exc_info:
            generate_candidate_job_match(
                session=session,
                candidate_id=candidate_id,
                job_id=job_id,
            )

    get_job_profile.assert_called_once_with(
        session,
        job_id=job_id,
    )
    get_match.assert_not_called()

    session.commit.assert_not_called()
    session.refresh.assert_not_called()
    session.rollback.assert_not_called()

    assert_app_exception(
        exc_info.value,
        expected_status=status.HTTP_404_NOT_FOUND,
        expected_code=(
            "job_requirement_profile_not_found"
        ),
        expected_message=(
            "A structured requirement profile is not "
            "available for this job."
        ),
    )


@pytest.mark.parametrize(
    (
        "field_name",
        "invalid_value",
    ),
    [
        (
            "parsing_status",
            "pending",
        ),
        (
            "profile_data",
            None,
        ),
        (
            "parser_version",
            None,
        ),
        (
            "source_description_sha256",
            None,
        ),
    ],
)
def test_generate_candidate_job_match_requires_ready_job_profile(
    field_name: str,
    invalid_value: object,
) -> None:
    session = MagicMock(spec=Session)

    (
        candidate_id,
        job_id,
        candidate,
        job,
        primary_resume,
        resume_profile,
        job_profile,
        _,
        _,
    ) = _build_completed_matching_inputs()

    setattr(
        job_profile,
        field_name,
        invalid_value,
    )

    with (
        patch(
            "app.services.candidate_job_match_service."
            "get_candidate_record",
            return_value=candidate,
        ),
        patch(
            "app.services.candidate_job_match_service."
            "get_job_record",
            return_value=job,
        ),
        patch(
            "app.services.candidate_job_match_service."
            "get_primary_resume_record",
            return_value=primary_resume,
        ),
        patch(
            "app.services.candidate_job_match_service."
            "get_resume_profile_record",
            return_value=resume_profile,
        ),
        patch(
            "app.services.candidate_job_match_service."
            "get_job_profile_record",
            return_value=job_profile,
        ),
        patch(
            "app.services.candidate_job_match_service."
            "get_match_record",
        ) as get_match,
    ):
        with pytest.raises(AppException) as exc_info:
            generate_candidate_job_match(
                session=session,
                candidate_id=candidate_id,
                job_id=job_id,
            )

    get_match.assert_not_called()

    session.commit.assert_not_called()
    session.refresh.assert_not_called()
    session.rollback.assert_not_called()

    assert_app_exception(
        exc_info.value,
        expected_status=status.HTTP_409_CONFLICT,
        expected_code=(
            "job_requirement_profile_not_ready"
        ),
        expected_message=(
            "The job must have a completed structured "
            "requirement profile before matching."
        ),
    )

def test_generate_candidate_job_match_rejects_invalid_resume_profile_data(
) -> None:
    session = MagicMock(spec=Session)

    (
        candidate_id,
        job_id,
        candidate,
        job,
        primary_resume,
        resume_profile,
        job_profile,
        _,
        _,
    ) = _build_completed_matching_inputs()

    resume_profile.profile_data = {
        "confidence": 2.0,
    }

    with (
        patch(
            "app.services.candidate_job_match_service."
            "get_candidate_record",
            return_value=candidate,
        ),
        patch(
            "app.services.candidate_job_match_service."
            "get_job_record",
            return_value=job,
        ),
        patch(
            "app.services.candidate_job_match_service."
            "get_primary_resume_record",
            return_value=primary_resume,
        ),
        patch(
            "app.services.candidate_job_match_service."
            "get_resume_profile_record",
            return_value=resume_profile,
        ),
        patch(
            "app.services.candidate_job_match_service."
            "get_job_profile_record",
            return_value=job_profile,
        ),
        patch(
            "app.services.candidate_job_match_service."
            "get_match_record",
        ) as get_match,
    ):
        with pytest.raises(AppException) as exc_info:
            generate_candidate_job_match(
                session=session,
                candidate_id=candidate_id,
                job_id=job_id,
            )

    get_match.assert_not_called()

    session.commit.assert_not_called()
    session.refresh.assert_not_called()
    session.rollback.assert_not_called()

    assert_app_exception(
        exc_info.value,
        expected_status=(
            status.HTTP_422_UNPROCESSABLE_CONTENT
        ),
        expected_code="resume_profile_data_invalid",
        expected_message=(
            "The structured Resume profile contains "
            "invalid data."
        ),
    )


def test_generate_candidate_job_match_rejects_invalid_job_profile_data(
) -> None:
    session = MagicMock(spec=Session)

    (
        candidate_id,
        job_id,
        candidate,
        job,
        primary_resume,
        resume_profile,
        job_profile,
        _,
        _,
    ) = _build_completed_matching_inputs()

    job_profile.profile_data = {
        "confidence": 2.0,
    }

    with (
        patch(
            "app.services.candidate_job_match_service."
            "get_candidate_record",
            return_value=candidate,
        ),
        patch(
            "app.services.candidate_job_match_service."
            "get_job_record",
            return_value=job,
        ),
        patch(
            "app.services.candidate_job_match_service."
            "get_primary_resume_record",
            return_value=primary_resume,
        ),
        patch(
            "app.services.candidate_job_match_service."
            "get_resume_profile_record",
            return_value=resume_profile,
        ),
        patch(
            "app.services.candidate_job_match_service."
            "get_job_profile_record",
            return_value=job_profile,
        ),
        patch(
            "app.services.candidate_job_match_service."
            "get_match_record",
        ) as get_match,
    ):
        with pytest.raises(AppException) as exc_info:
            generate_candidate_job_match(
                session=session,
                candidate_id=candidate_id,
                job_id=job_id,
            )

    get_match.assert_not_called()

    session.commit.assert_not_called()
    session.refresh.assert_not_called()
    session.rollback.assert_not_called()

    assert_app_exception(
        exc_info.value,
        expected_status=(
            status.HTTP_422_UNPROCESSABLE_CONTENT
        ),
        expected_code=(
            "job_requirement_profile_data_invalid"
        ),
        expected_message=(
            "The structured job requirement profile "
            "contains invalid data."
        ),
    )


def test_generate_candidate_job_match_rejects_invalid_match_payload(
) -> None:
    session = MagicMock(spec=Session)

    (
        candidate_id,
        job_id,
        candidate,
        job,
        primary_resume,
        resume_profile,
        job_profile,
        _,
        _,
    ) = _build_completed_matching_inputs()

    computation = MagicMock()

    with (
        patch(
            "app.services.candidate_job_match_service."
            "get_candidate_record",
            return_value=candidate,
        ),
        patch(
            "app.services.candidate_job_match_service."
            "get_job_record",
            return_value=job,
        ),
        patch(
            "app.services.candidate_job_match_service."
            "get_primary_resume_record",
            return_value=primary_resume,
        ),
        patch(
            "app.services.candidate_job_match_service."
            "get_resume_profile_record",
            return_value=resume_profile,
        ),
        patch(
            "app.services.candidate_job_match_service."
            "get_job_profile_record",
            return_value=job_profile,
        ),
        patch(
            "app.services.candidate_job_match_service."
            "get_match_record",
            return_value=None,
        ),
        patch(
            "app.services.candidate_job_match_service."
            "match_candidate_profile_to_job_requirements",
            return_value=computation,
        ),
        patch(
            "app.services.candidate_job_match_service."
            "build_candidate_job_match_create",
            side_effect=ValueError(
                "Invalid persistence payload."
            ),
        ),
        patch(
            "app.services.candidate_job_match_service."
            "create_match_record",
        ) as create_match,
        patch(
            "app.services.candidate_job_match_service."
            "update_match_record",
        ) as update_match,
    ):
        with pytest.raises(AppException) as exc_info:
            generate_candidate_job_match(
                session=session,
                candidate_id=candidate_id,
                job_id=job_id,
            )

    create_match.assert_not_called()
    update_match.assert_not_called()

    session.commit.assert_not_called()
    session.refresh.assert_not_called()
    session.rollback.assert_not_called()

    assert_app_exception(
        exc_info.value,
        expected_status=(
            status.HTTP_422_UNPROCESSABLE_CONTENT
        ),
        expected_code="candidate_job_match_input_invalid",
        expected_message=(
            "The candidate and job profiles could not "
            "be used to calculate a match."
        ),
    )
def test_generate_candidate_job_match_rolls_back_lookup_database_error(
) -> None:
    session = MagicMock(spec=Session)
    candidate_id = uuid4()
    job_id = uuid4()

    with patch(
        "app.services.candidate_job_match_service."
        "get_candidate_record",
        side_effect=SQLAlchemyError("database failure"),
    ):
        with pytest.raises(AppException) as exc_info:
            generate_candidate_job_match(
                session=session,
                candidate_id=candidate_id,
                job_id=job_id,
            )

    session.rollback.assert_called_once_with()
    session.commit.assert_not_called()
    session.refresh.assert_not_called()

    assert_app_exception(
        exc_info.value,
        expected_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        expected_code=(
            "candidate_job_match_persistence_failed"
        ),
        expected_message=(
            "The Candidate–Job match could not be "
            "generated or saved."
        ),
    )


def test_generate_candidate_job_match_rolls_back_create_error(
) -> None:
    session = MagicMock(spec=Session)

    (
        candidate_id,
        job_id,
        candidate,
        job,
        primary_resume,
        resume_profile,
        job_profile,
        _,
        _,
    ) = _build_completed_matching_inputs()

    computation = MagicMock()
    create_payload = MagicMock(
        spec=CandidateJobMatchCreate
    )

    with (
        patch(
            "app.services.candidate_job_match_service."
            "get_candidate_record",
            return_value=candidate,
        ),
        patch(
            "app.services.candidate_job_match_service."
            "get_job_record",
            return_value=job,
        ),
        patch(
            "app.services.candidate_job_match_service."
            "get_primary_resume_record",
            return_value=primary_resume,
        ),
        patch(
            "app.services.candidate_job_match_service."
            "get_resume_profile_record",
            return_value=resume_profile,
        ),
        patch(
            "app.services.candidate_job_match_service."
            "get_job_profile_record",
            return_value=job_profile,
        ),
        patch(
            "app.services.candidate_job_match_service."
            "get_match_record",
            return_value=None,
        ),
        patch(
            "app.services.candidate_job_match_service."
            "match_candidate_profile_to_job_requirements",
            return_value=computation,
        ),
        patch(
            "app.services.candidate_job_match_service."
            "build_candidate_job_match_create",
            return_value=create_payload,
        ),
        patch(
            "app.services.candidate_job_match_service."
            "create_match_record",
            side_effect=SQLAlchemyError(
                "database failure"
            ),
        ),
    ):
        with pytest.raises(AppException) as exc_info:
            generate_candidate_job_match(
                session=session,
                candidate_id=candidate_id,
                job_id=job_id,
            )

    session.rollback.assert_called_once_with()
    session.commit.assert_not_called()
    session.refresh.assert_not_called()

    assert_app_exception(
        exc_info.value,
        expected_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        expected_code=(
            "candidate_job_match_persistence_failed"
        ),
        expected_message=(
            "The Candidate–Job match could not be "
            "generated or saved."
        ),
    )


def test_generate_candidate_job_match_rolls_back_update_error(
) -> None:
    session = MagicMock(spec=Session)

    (
        candidate_id,
        job_id,
        candidate,
        job,
        primary_resume,
        resume_profile,
        job_profile,
        _,
        _,
    ) = _build_completed_matching_inputs()

    existing_match = MagicMock(
        spec=CandidateJobMatch
    )
    _make_existing_match_current(
        existing_match=existing_match,
        resume_profile=resume_profile,
        job_profile=job_profile,
    )
    existing_match.scoring_version = "old-version"

    computation = MagicMock()
    create_payload = MagicMock(
        spec=CandidateJobMatchCreate
    )
    create_payload.model_dump.return_value = {
        "overall_score": 80.0,
    }

    with (
        patch(
            "app.services.candidate_job_match_service."
            "get_candidate_record",
            return_value=candidate,
        ),
        patch(
            "app.services.candidate_job_match_service."
            "get_job_record",
            return_value=job,
        ),
        patch(
            "app.services.candidate_job_match_service."
            "get_primary_resume_record",
            return_value=primary_resume,
        ),
        patch(
            "app.services.candidate_job_match_service."
            "get_resume_profile_record",
            return_value=resume_profile,
        ),
        patch(
            "app.services.candidate_job_match_service."
            "get_job_profile_record",
            return_value=job_profile,
        ),
        patch(
            "app.services.candidate_job_match_service."
            "get_match_record",
            return_value=existing_match,
        ),
        patch(
            "app.services.candidate_job_match_service."
            "match_candidate_profile_to_job_requirements",
            return_value=computation,
        ),
        patch(
            "app.services.candidate_job_match_service."
            "build_candidate_job_match_create",
            return_value=create_payload,
        ),
        patch(
            "app.services.candidate_job_match_service."
            "CandidateJobMatchUpdate",
            return_value=MagicMock(),
        ),
        patch(
            "app.services.candidate_job_match_service."
            "update_match_record",
            side_effect=SQLAlchemyError(
                "database failure"
            ),
        ),
    ):
        with pytest.raises(AppException) as exc_info:
            generate_candidate_job_match(
                session=session,
                candidate_id=candidate_id,
                job_id=job_id,
            )

    session.rollback.assert_called_once_with()
    session.commit.assert_not_called()
    session.refresh.assert_not_called()

    assert_app_exception(
        exc_info.value,
        expected_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        expected_code=(
            "candidate_job_match_persistence_failed"
        ),
        expected_message=(
            "The Candidate–Job match could not be "
            "generated or saved."
        ),
    )