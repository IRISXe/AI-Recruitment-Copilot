from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi import status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.extraction.resume_extractor import (
    EXTRACTOR_VERSION,
)
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
from app.models.resume_content import ResumeContent
from app.models.resume_profile import ResumeProfile
from app.parsing.job_description_parser import (
    PARSER_VERSION as JOB_PARSER_VERSION,
)
from app.parsing.resume_parser import (
    PARSER_VERSION as RESUME_PARSER_VERSION,
)
from app.schemas.job_requirement_profile import (
    JobRequirementProfileData,
)
from app.schemas.resume_profile import (
    ResumeProfileData,
)
from app.services.candidate_evaluation_service import (
    evaluate_candidate_for_job,
)
from app.services.job_requirement_profile_service import (
    calculate_source_description_sha256,
)
from app.services.resume_profile_service import (
    calculate_source_text_sha256,
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


def build_pipeline_records() -> tuple[
    UUID,
    UUID,
    Candidate,
    Job,
    Resume,
    ResumeContent,
    ResumeProfile,
    JobRequirementProfile,
    CandidateJobMatch,
]:
    candidate_id = uuid4()
    job_id = uuid4()
    resume_id = uuid4()

    timestamp = datetime(
        2026,
        7,
        24,
        12,
        0,
        tzinfo=UTC,
    )

    candidate = MagicMock(spec=Candidate)
    candidate.id = candidate_id

    job_description = (
        "Frontend Engineer requiring React, TypeScript, "
        "REST APIs and two years of experience."
    )

    job = MagicMock(spec=Job)
    job.id = job_id
    job.description = job_description

    primary_resume = MagicMock(spec=Resume)
    primary_resume.id = resume_id
    primary_resume.candidate_id = candidate_id
    primary_resume.is_primary = True

    extracted_text = (
        "Harsha Vardhan Frontend Engineer React TypeScript "
        "REST APIs AWS two years experience"
    )

    resume_content = ResumeContent(
        id=uuid4(),
        resume_id=resume_id,
        extracted_text=extracted_text,
        extraction_status="completed",
        extraction_error=None,
        extractor_version=EXTRACTOR_VERSION,
        extracted_at=timestamp,
        created_at=timestamp,
        updated_at=timestamp,
    )

    resume_data = ResumeProfileData(
        full_name="Harsha Vardhan",
        location="Hyderabad",
        total_experience_months=24,
        skills=[
            "React.js",
            "TypeScript",
            "REST APIs",
            "AWS",
        ],
        confidence=0.90,
    )

    resume_profile = ResumeProfile(
        id=uuid4(),
        resume_id=resume_id,
        profile_data=resume_data.model_dump(
            mode="json"
        ),
        parsing_status="completed",
        parsing_error=None,
        parser_version=RESUME_PARSER_VERSION,
        source_text_sha256=(
            calculate_source_text_sha256(
                extracted_text
            )
        ),
        parsed_at=timestamp,
        created_at=timestamp,
        updated_at=timestamp,
    )

    job_data = JobRequirementProfileData(
        job_title="Frontend Engineer",
        location="Hyderabad",
        work_mode="hybrid",
        required_skills=[
            "React",
            "TypeScript",
            "REST APIs",
        ],
        preferred_skills=[
            "AWS",
        ],
        minimum_experience_years=2,
        confidence=0.90,
    )

    job_profile = JobRequirementProfile(
        id=uuid4(),
        job_id=job_id,
        profile_data=job_data.model_dump(
            mode="json"
        ),
        parsing_status="completed",
        parsing_error=None,
        parser_version=JOB_PARSER_VERSION,
        source_description_sha256=(
            calculate_source_description_sha256(
                job_description
            )
        ),
        parsed_at=timestamp,
        created_at=timestamp,
        updated_at=timestamp,
    )

    candidate_job_match = CandidateJobMatch(
        id=uuid4(),
        candidate_id=candidate_id,
        job_id=job_id,
        resume_id=resume_id,
        resume_profile_id=resume_profile.id,
        job_requirement_profile_id=job_profile.id,
        overall_score=Decimal("88.50"),
        skill_score=Decimal("90.00"),
        experience_score=Decimal("85.00"),
        education_score=Decimal("80.00"),
        certification_score=Decimal("75.00"),
        location_score=Decimal("100.00"),
        work_mode_score=Decimal("90.00"),
        confidence_score=Decimal("90.00"),
        recommendation="strong_match",
        analysis_data={},
        scoring_version=SCORING_VERSION,
        source_resume_text_sha256=(
            resume_profile.source_text_sha256
        ),
        source_resume_parser_version=(
            resume_profile.parser_version
        ),
        source_job_description_sha256=(
            job_profile.source_description_sha256
        ),
        source_job_parser_version=(
            job_profile.parser_version
        ),
        matched_at=timestamp,
        created_at=timestamp,
        updated_at=timestamp,
    )

    return (
        candidate_id,
        job_id,
        candidate,
        job,
        primary_resume,
        resume_content,
        resume_profile,
        job_profile,
        candidate_job_match,
    )


def test_evaluate_candidate_processes_missing_pipeline(
) -> None:
    session = MagicMock(spec=Session)

    (
        candidate_id,
        job_id,
        candidate,
        job,
        primary_resume,
        resume_content,
        resume_profile,
        job_profile,
        candidate_job_match,
    ) = build_pipeline_records()

    with (
        patch(
            "app.services.candidate_evaluation_service."
            "get_candidate_record",
            return_value=candidate,
        ),
        patch(
            "app.services.candidate_evaluation_service."
            "get_job_record",
            return_value=job,
        ),
        patch(
            "app.services.candidate_evaluation_service."
            "get_primary_resume_record",
            return_value=primary_resume,
        ),
        patch(
            "app.services.candidate_evaluation_service."
            "get_resume_content_record",
            return_value=None,
        ),
        patch(
            "app.services.candidate_evaluation_service."
            "extract_resume_content_service",
            return_value=resume_content,
        ) as extract_content,
        patch(
            "app.services.candidate_evaluation_service."
            "get_resume_profile_record",
            return_value=None,
        ),
        patch(
            "app.services.candidate_evaluation_service."
            "parse_resume_profile_service",
            return_value=resume_profile,
        ) as parse_resume,
        patch(
            "app.services.candidate_evaluation_service."
            "get_job_profile_record",
            return_value=None,
        ),
        patch(
            "app.services.candidate_evaluation_service."
            "parse_job_profile_service",
            return_value=job_profile,
        ) as parse_job,
        patch(
            "app.services.candidate_evaluation_service."
            "get_match_record",
            return_value=None,
        ),
        patch(
            "app.services.candidate_evaluation_service."
            "generate_match_service",
            return_value=candidate_job_match,
        ) as generate_match,
    ):
        result = evaluate_candidate_for_job(
            session,
            candidate_id=candidate_id,
            job_id=job_id,
        )

    extract_content.assert_called_once_with(
        session,
        resume_id=primary_resume.id,
    )
    parse_resume.assert_called_once_with(
        session,
        resume_id=primary_resume.id,
        force=False,
    )
    parse_job.assert_called_once_with(
        session,
        job_id=job_id,
        force=False,
    )
    generate_match.assert_called_once_with(
        session,
        candidate_id=candidate_id,
        job_id=job_id,
        force=False,
    )

    assert result.status == "completed"
    assert result.force is False
    assert result.candidate_id == candidate_id
    assert result.job_id == job_id
    assert result.resume_id == primary_resume.id

    assert result.stages.resume_content == "processed"
    assert result.stages.resume_profile == "processed"
    assert (
        result.stages.job_requirement_profile
        == "processed"
    )
    assert (
        result.stages.candidate_job_match
        == "processed"
    )

    session.rollback.assert_not_called()


def test_evaluate_candidate_reuses_current_pipeline(
) -> None:
    session = MagicMock(spec=Session)

    (
        candidate_id,
        job_id,
        candidate,
        job,
        primary_resume,
        resume_content,
        resume_profile,
        job_profile,
        candidate_job_match,
    ) = build_pipeline_records()

    with (
        patch(
            "app.services.candidate_evaluation_service."
            "get_candidate_record",
            return_value=candidate,
        ),
        patch(
            "app.services.candidate_evaluation_service."
            "get_job_record",
            return_value=job,
        ),
        patch(
            "app.services.candidate_evaluation_service."
            "get_primary_resume_record",
            return_value=primary_resume,
        ),
        patch(
            "app.services.candidate_evaluation_service."
            "get_resume_content_record",
            return_value=resume_content,
        ),
        patch(
            "app.services.candidate_evaluation_service."
            "extract_resume_content_service",
        ) as extract_content,
        patch(
            "app.services.candidate_evaluation_service."
            "get_resume_profile_record",
            return_value=resume_profile,
        ),
        patch(
            "app.services.candidate_evaluation_service."
            "parse_resume_profile_service",
            return_value=resume_profile,
        ) as parse_resume,
        patch(
            "app.services.candidate_evaluation_service."
            "get_job_profile_record",
            return_value=job_profile,
        ),
        patch(
            "app.services.candidate_evaluation_service."
            "parse_job_profile_service",
            return_value=job_profile,
        ) as parse_job,
        patch(
            "app.services.candidate_evaluation_service."
            "get_match_record",
            return_value=candidate_job_match,
        ),
        patch(
            "app.services.candidate_evaluation_service."
            "generate_match_service",
            return_value=candidate_job_match,
        ) as generate_match,
    ):
        result = evaluate_candidate_for_job(
            session,
            candidate_id=candidate_id,
            job_id=job_id,
        )

    extract_content.assert_not_called()

    parse_resume.assert_called_once_with(
        session,
        resume_id=primary_resume.id,
        force=False,
    )
    parse_job.assert_called_once_with(
        session,
        job_id=job_id,
        force=False,
    )
    generate_match.assert_called_once_with(
        session,
        candidate_id=candidate_id,
        job_id=job_id,
        force=False,
    )

    assert result.stages.resume_content == "reused"
    assert result.stages.resume_profile == "reused"
    assert (
        result.stages.job_requirement_profile
        == "reused"
    )
    assert (
        result.stages.candidate_job_match
        == "reused"
    )


def test_evaluate_candidate_force_reprocesses_every_stage(
) -> None:
    session = MagicMock(spec=Session)

    (
        candidate_id,
        job_id,
        candidate,
        job,
        primary_resume,
        resume_content,
        resume_profile,
        job_profile,
        candidate_job_match,
    ) = build_pipeline_records()

    with (
        patch(
            "app.services.candidate_evaluation_service."
            "get_candidate_record",
            return_value=candidate,
        ),
        patch(
            "app.services.candidate_evaluation_service."
            "get_job_record",
            return_value=job,
        ),
        patch(
            "app.services.candidate_evaluation_service."
            "get_primary_resume_record",
            return_value=primary_resume,
        ),
        patch(
            "app.services.candidate_evaluation_service."
            "get_resume_content_record",
            return_value=resume_content,
        ),
        patch(
            "app.services.candidate_evaluation_service."
            "extract_resume_content_service",
            return_value=resume_content,
        ) as extract_content,
        patch(
            "app.services.candidate_evaluation_service."
            "get_resume_profile_record",
            return_value=resume_profile,
        ),
        patch(
            "app.services.candidate_evaluation_service."
            "parse_resume_profile_service",
            return_value=resume_profile,
        ) as parse_resume,
        patch(
            "app.services.candidate_evaluation_service."
            "get_job_profile_record",
            return_value=job_profile,
        ),
        patch(
            "app.services.candidate_evaluation_service."
            "parse_job_profile_service",
            return_value=job_profile,
        ) as parse_job,
        patch(
            "app.services.candidate_evaluation_service."
            "get_match_record",
            return_value=candidate_job_match,
        ),
        patch(
            "app.services.candidate_evaluation_service."
            "generate_match_service",
            return_value=candidate_job_match,
        ) as generate_match,
    ):
        result = evaluate_candidate_for_job(
            session,
            candidate_id=candidate_id,
            job_id=job_id,
            force=True,
        )

    extract_content.assert_called_once_with(
        session,
        resume_id=primary_resume.id,
    )
    parse_resume.assert_called_once_with(
        session,
        resume_id=primary_resume.id,
        force=True,
    )
    parse_job.assert_called_once_with(
        session,
        job_id=job_id,
        force=True,
    )
    generate_match.assert_called_once_with(
        session,
        candidate_id=candidate_id,
        job_id=job_id,
        force=True,
    )

    assert result.force is True
    assert result.stages.resume_content == "processed"
    assert result.stages.resume_profile == "processed"
    assert (
        result.stages.job_requirement_profile
        == "processed"
    )
    assert (
        result.stages.candidate_job_match
        == "processed"
    )


def test_evaluate_candidate_requires_candidate() -> None:
    session = MagicMock(spec=Session)
    candidate_id = uuid4()
    job_id = uuid4()

    with (
        patch(
            "app.services.candidate_evaluation_service."
            "get_candidate_record",
            return_value=None,
        ),
        patch(
            "app.services.candidate_evaluation_service."
            "get_job_record",
        ) as get_job,
    ):
        with pytest.raises(AppException) as exc_info:
            evaluate_candidate_for_job(
                session,
                candidate_id=candidate_id,
                job_id=job_id,
            )

    get_job.assert_not_called()
    session.rollback.assert_not_called()

    assert_app_exception(
        exc_info.value,
        expected_status=status.HTTP_404_NOT_FOUND,
        expected_code="candidate_not_found",
        expected_message=(
            "The requested candidate does not exist."
        ),
    )


def test_evaluate_candidate_requires_job() -> None:
    session = MagicMock(spec=Session)
    candidate_id = uuid4()
    job_id = uuid4()

    with (
        patch(
            "app.services.candidate_evaluation_service."
            "get_candidate_record",
            return_value=MagicMock(spec=Candidate),
        ),
        patch(
            "app.services.candidate_evaluation_service."
            "get_job_record",
            return_value=None,
        ),
        patch(
            "app.services.candidate_evaluation_service."
            "get_primary_resume_record",
        ) as get_primary_resume,
    ):
        with pytest.raises(AppException) as exc_info:
            evaluate_candidate_for_job(
                session,
                candidate_id=candidate_id,
                job_id=job_id,
            )

    get_primary_resume.assert_not_called()
    session.rollback.assert_not_called()

    assert_app_exception(
        exc_info.value,
        expected_status=status.HTTP_404_NOT_FOUND,
        expected_code="job_not_found",
        expected_message="The requested job does not exist.",
    )


def test_evaluate_candidate_requires_primary_resume() -> None:
    session = MagicMock(spec=Session)
    candidate_id = uuid4()
    job_id = uuid4()

    with (
        patch(
            "app.services.candidate_evaluation_service."
            "get_candidate_record",
            return_value=MagicMock(spec=Candidate),
        ),
        patch(
            "app.services.candidate_evaluation_service."
            "get_job_record",
            return_value=MagicMock(spec=Job),
        ),
        patch(
            "app.services.candidate_evaluation_service."
            "get_primary_resume_record",
            return_value=None,
        ),
        patch(
            "app.services.candidate_evaluation_service."
            "get_resume_content_record",
        ) as get_resume_content,
    ):
        with pytest.raises(AppException) as exc_info:
            evaluate_candidate_for_job(
                session,
                candidate_id=candidate_id,
                job_id=job_id,
            )

    get_resume_content.assert_not_called()
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


def test_evaluate_candidate_stops_when_extraction_fails(
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
    ) = build_pipeline_records()

    extraction_error = AppException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        code="resume_extraction_failed",
        message="The Resume text could not be extracted.",
    )

    with (
        patch(
            "app.services.candidate_evaluation_service."
            "get_candidate_record",
            return_value=candidate,
        ),
        patch(
            "app.services.candidate_evaluation_service."
            "get_job_record",
            return_value=job,
        ),
        patch(
            "app.services.candidate_evaluation_service."
            "get_primary_resume_record",
            return_value=primary_resume,
        ),
        patch(
            "app.services.candidate_evaluation_service."
            "get_resume_content_record",
            return_value=None,
        ),
        patch(
            "app.services.candidate_evaluation_service."
            "extract_resume_content_service",
            side_effect=extraction_error,
        ),
        patch(
            "app.services.candidate_evaluation_service."
            "parse_resume_profile_service",
        ) as parse_resume,
    ):
        with pytest.raises(AppException) as exc_info:
            evaluate_candidate_for_job(
                session,
                candidate_id=candidate_id,
                job_id=job_id,
            )

    parse_resume.assert_not_called()
    assert exc_info.value is extraction_error


def test_evaluate_candidate_stops_when_resume_parsing_fails(
) -> None:
    session = MagicMock(spec=Session)

    (
        candidate_id,
        job_id,
        candidate,
        job,
        primary_resume,
        resume_content,
        _,
        _,
        _,
    ) = build_pipeline_records()

    parsing_error = AppException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        code="resume_parsing_failed",
        message=(
            "The Resume could not be parsed into a "
            "structured profile."
        ),
    )

    with (
        patch(
            "app.services.candidate_evaluation_service."
            "get_candidate_record",
            return_value=candidate,
        ),
        patch(
            "app.services.candidate_evaluation_service."
            "get_job_record",
            return_value=job,
        ),
        patch(
            "app.services.candidate_evaluation_service."
            "get_primary_resume_record",
            return_value=primary_resume,
        ),
        patch(
            "app.services.candidate_evaluation_service."
            "get_resume_content_record",
            return_value=None,
        ),
        patch(
            "app.services.candidate_evaluation_service."
            "extract_resume_content_service",
            return_value=resume_content,
        ),
        patch(
            "app.services.candidate_evaluation_service."
            "get_resume_profile_record",
            return_value=None,
        ),
        patch(
            "app.services.candidate_evaluation_service."
            "parse_resume_profile_service",
            side_effect=parsing_error,
        ),
        patch(
            "app.services.candidate_evaluation_service."
            "parse_job_profile_service",
        ) as parse_job,
    ):
        with pytest.raises(AppException) as exc_info:
            evaluate_candidate_for_job(
                session,
                candidate_id=candidate_id,
                job_id=job_id,
            )

    parse_job.assert_not_called()
    assert exc_info.value is parsing_error


def test_evaluate_candidate_stops_when_job_parsing_fails(
) -> None:
    session = MagicMock(spec=Session)

    (
        candidate_id,
        job_id,
        candidate,
        job,
        primary_resume,
        resume_content,
        resume_profile,
        _,
        _,
    ) = build_pipeline_records()

    parsing_error = AppException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        code="job_description_parsing_failed",
        message=(
            "The job description could not be parsed "
            "into structured requirements."
        ),
    )

    with (
        patch(
            "app.services.candidate_evaluation_service."
            "get_candidate_record",
            return_value=candidate,
        ),
        patch(
            "app.services.candidate_evaluation_service."
            "get_job_record",
            return_value=job,
        ),
        patch(
            "app.services.candidate_evaluation_service."
            "get_primary_resume_record",
            return_value=primary_resume,
        ),
        patch(
            "app.services.candidate_evaluation_service."
            "get_resume_content_record",
            return_value=resume_content,
        ),
        patch(
            "app.services.candidate_evaluation_service."
            "get_resume_profile_record",
            return_value=resume_profile,
        ),
        patch(
            "app.services.candidate_evaluation_service."
            "parse_resume_profile_service",
            return_value=resume_profile,
        ),
        patch(
            "app.services.candidate_evaluation_service."
            "get_job_profile_record",
            return_value=None,
        ),
        patch(
            "app.services.candidate_evaluation_service."
            "parse_job_profile_service",
            side_effect=parsing_error,
        ),
        patch(
            "app.services.candidate_evaluation_service."
            "generate_match_service",
        ) as generate_match,
    ):
        with pytest.raises(AppException) as exc_info:
            evaluate_candidate_for_job(
                session,
                candidate_id=candidate_id,
                job_id=job_id,
            )

    generate_match.assert_not_called()
    assert exc_info.value is parsing_error


def test_evaluate_candidate_propagates_matching_error(
) -> None:
    session = MagicMock(spec=Session)

    (
        candidate_id,
        job_id,
        candidate,
        job,
        primary_resume,
        resume_content,
        resume_profile,
        job_profile,
        _,
    ) = build_pipeline_records()

    matching_error = AppException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        code="candidate_job_match_persistence_failed",
        message=(
            "The Candidate-Job match could not be "
            "generated or saved."
        ),
    )

    with (
        patch(
            "app.services.candidate_evaluation_service."
            "get_candidate_record",
            return_value=candidate,
        ),
        patch(
            "app.services.candidate_evaluation_service."
            "get_job_record",
            return_value=job,
        ),
        patch(
            "app.services.candidate_evaluation_service."
            "get_primary_resume_record",
            return_value=primary_resume,
        ),
        patch(
            "app.services.candidate_evaluation_service."
            "get_resume_content_record",
            return_value=resume_content,
        ),
        patch(
            "app.services.candidate_evaluation_service."
            "get_resume_profile_record",
            return_value=resume_profile,
        ),
        patch(
            "app.services.candidate_evaluation_service."
            "parse_resume_profile_service",
            return_value=resume_profile,
        ),
        patch(
            "app.services.candidate_evaluation_service."
            "get_job_profile_record",
            return_value=job_profile,
        ),
        patch(
            "app.services.candidate_evaluation_service."
            "parse_job_profile_service",
            return_value=job_profile,
        ),
        patch(
            "app.services.candidate_evaluation_service."
            "get_match_record",
            return_value=None,
        ),
        patch(
            "app.services.candidate_evaluation_service."
            "generate_match_service",
            side_effect=matching_error,
        ),
    ):
        with pytest.raises(AppException) as exc_info:
            evaluate_candidate_for_job(
                session,
                candidate_id=candidate_id,
                job_id=job_id,
            )

    assert exc_info.value is matching_error


def test_evaluate_candidate_rolls_back_lookup_database_error(
) -> None:
    session = MagicMock(spec=Session)
    candidate_id = uuid4()
    job_id = uuid4()

    with patch(
        "app.services.candidate_evaluation_service."
        "get_candidate_record",
        side_effect=SQLAlchemyError("database failure"),
    ):
        with pytest.raises(AppException) as exc_info:
            evaluate_candidate_for_job(
                session,
                candidate_id=candidate_id,
                job_id=job_id,
            )

    session.rollback.assert_called_once_with()

    assert_app_exception(
        exc_info.value,
        expected_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        expected_code="candidate_evaluation_failed",
        expected_message=(
            "The Candidate evaluation could not be "
            "completed."
        ),
    )