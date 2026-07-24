import logging
from datetime import UTC, datetime
from uuid import UUID

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
from app.repositories.candidate_job_match_repository import (
    get_candidate_job_match_by_candidate_and_job as get_match_record,
)
from app.repositories.candidate_repository import (
    get_candidate_by_id as get_candidate_record,
)
from app.repositories.job_repository import (
    get_job_by_id as get_job_record,
)
from app.repositories.job_requirement_profile_repository import (
    get_job_requirement_profile_by_job_id as get_job_profile_record,
)
from app.repositories.resume_content_repository import (
    get_resume_content_by_resume_id as get_resume_content_record,
)
from app.repositories.resume_profile_repository import (
    get_resume_profile_by_resume_id as get_resume_profile_record,
)
from app.repositories.resume_repository import (
    get_primary_resume_by_candidate_id as get_primary_resume_record,
)
from app.schemas.candidate_evaluation import (
    CandidateEvaluationResponse,
    CandidateEvaluationStages,
)
from app.schemas.candidate_job_match import (
    CandidateJobMatchResponse,
)
from app.schemas.job_requirement_profile import (
    JobRequirementProfileResponse,
)
from app.schemas.resume_content import (
    ResumeContentResponse,
)
from app.schemas.resume_profile import (
    ResumeProfileResponse,
)
from app.services.candidate_job_match_service import (
    generate_candidate_job_match as generate_match_service,
)
from app.services.job_requirement_profile_service import (
    calculate_source_description_sha256,
    parse_job_requirement_profile as parse_job_profile_service,
)
from app.services.resume_content_service import (
    extract_resume_content as extract_resume_content_service,
)
from app.services.resume_profile_service import (
    calculate_source_text_sha256,
    parse_resume_profile as parse_resume_profile_service,
)


logger = logging.getLogger(__name__)


def _get_candidate_or_raise(
    session: Session,
    candidate_id: UUID,
) -> Candidate:
    candidate = get_candidate_record(
        session,
        candidate_id,
    )

    if candidate is None:
        raise AppException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="candidate_not_found",
            message="The requested candidate does not exist.",
        )

    return candidate


def _get_job_or_raise(
    session: Session,
    job_id: UUID,
) -> Job:
    job = get_job_record(
        session,
        job_id,
    )

    if job is None:
        raise AppException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="job_not_found",
            message="The requested job does not exist.",
        )

    return job


def _get_primary_resume_or_raise(
    session: Session,
    candidate_id: UUID,
) -> Resume:
    primary_resume = get_primary_resume_record(
        session,
        candidate_id,
    )

    if primary_resume is None:
        raise AppException(
            status_code=status.HTTP_409_CONFLICT,
            code="primary_resume_not_found",
            message=(
                "The candidate must have an explicitly selected "
                "primary Resume before matching."
            ),
        )

    return primary_resume


def _is_resume_content_current(
    resume_content: ResumeContent | None,
) -> bool:
    if resume_content is None:
        return False

    extracted_text = resume_content.extracted_text

    return (
        resume_content.extraction_status == "completed"
        and extracted_text is not None
        and bool(extracted_text.strip())
        and resume_content.extractor_version
        == EXTRACTOR_VERSION
    )


def _is_resume_profile_current(
    resume_profile: ResumeProfile | None,
    resume_content: ResumeContent,
) -> bool:
    extracted_text = resume_content.extracted_text

    if (
        resume_profile is None
        or extracted_text is None
        or not extracted_text.strip()
    ):
        return False

    expected_hash = calculate_source_text_sha256(
        extracted_text
    )

    return (
        resume_profile.parsing_status == "completed"
        and resume_profile.profile_data is not None
        and resume_profile.parser_version
        == RESUME_PARSER_VERSION
        and resume_profile.source_text_sha256
        == expected_hash
    )


def _is_job_profile_current(
    job_profile: JobRequirementProfile | None,
    job: Job,
) -> bool:
    description = job.description

    if (
        job_profile is None
        or description is None
        or not description.strip()
    ):
        return False

    expected_hash = calculate_source_description_sha256(
        description
    )

    return (
        job_profile.parsing_status == "completed"
        and job_profile.profile_data is not None
        and job_profile.parser_version
        == JOB_PARSER_VERSION
        and job_profile.source_description_sha256
        == expected_hash
    )


def _is_match_current(
    candidate_job_match: CandidateJobMatch | None,
    *,
    resume_id: UUID,
    resume_profile: ResumeProfile,
    job_profile: JobRequirementProfile,
) -> bool:
    if candidate_job_match is None:
        return False

    return (
        candidate_job_match.resume_id == resume_id
        and candidate_job_match.resume_profile_id
        == resume_profile.id
        and candidate_job_match.job_requirement_profile_id
        == job_profile.id
        and candidate_job_match.scoring_version
        == SCORING_VERSION
        and candidate_job_match.source_resume_text_sha256
        == resume_profile.source_text_sha256
        and candidate_job_match.source_resume_parser_version
        == resume_profile.parser_version
        and candidate_job_match.source_job_description_sha256
        == job_profile.source_description_sha256
        and candidate_job_match.source_job_parser_version
        == job_profile.parser_version
    )


def evaluate_candidate_for_job(
    session: Session,
    *,
    candidate_id: UUID,
    job_id: UUID,
    force: bool = False,
) -> CandidateEvaluationResponse:
    try:
        _get_candidate_or_raise(
            session,
            candidate_id,
        )

        job = _get_job_or_raise(
            session,
            job_id,
        )

        primary_resume = _get_primary_resume_or_raise(
            session,
            candidate_id,
        )

        existing_resume_content = get_resume_content_record(
            session,
            resume_id=primary_resume.id,
        )

        resume_content_was_current = (
            _is_resume_content_current(
                existing_resume_content
            )
        )

        if force or not resume_content_was_current:
            resume_content = extract_resume_content_service(
                session,
                resume_id=primary_resume.id,
            )
        else:
            resume_content = existing_resume_content

        existing_resume_profile = get_resume_profile_record(
            session,
            resume_id=primary_resume.id,
        )

        resume_profile_was_current = (
            _is_resume_profile_current(
                existing_resume_profile,
                resume_content,
            )
        )

        resume_profile = parse_resume_profile_service(
            session,
            resume_id=primary_resume.id,
            force=force,
        )

        existing_job_profile = get_job_profile_record(
            session,
            job_id=job_id,
        )

        job_profile_was_current = (
            _is_job_profile_current(
                existing_job_profile,
                job,
            )
        )

        job_profile = parse_job_profile_service(
            session,
            job_id=job_id,
            force=force,
        )

        existing_match = get_match_record(
            session,
            candidate_id=candidate_id,
            job_id=job_id,
        )

        match_was_current = _is_match_current(
            existing_match,
            resume_id=primary_resume.id,
            resume_profile=resume_profile,
            job_profile=job_profile,
        )

        candidate_job_match = generate_match_service(
            session,
            candidate_id=candidate_id,
            job_id=job_id,
            force=force,
        )

        return CandidateEvaluationResponse(
            candidate_id=candidate_id,
            job_id=job_id,
            resume_id=primary_resume.id,
            force=force,
            evaluated_at=datetime.now(UTC),
            stages=CandidateEvaluationStages(
                resume_content=(
                    "reused"
                    if resume_content_was_current
                    and not force
                    else "processed"
                ),
                resume_profile=(
                    "reused"
                    if resume_profile_was_current
                    and not force
                    else "processed"
                ),
                job_requirement_profile=(
                    "reused"
                    if job_profile_was_current
                    and not force
                    else "processed"
                ),
                candidate_job_match=(
                    "reused"
                    if match_was_current
                    and not force
                    else "processed"
                ),
            ),
            resume_content=(
                ResumeContentResponse.model_validate(
                    resume_content
                )
            ),
            resume_profile=(
                ResumeProfileResponse.model_validate(
                    resume_profile
                )
            ),
            job_requirement_profile=(
                JobRequirementProfileResponse.model_validate(
                    job_profile
                )
            ),
            candidate_job_match=(
                CandidateJobMatchResponse.model_validate(
                    candidate_job_match
                )
            ),
        )

    except AppException:
        raise

    except SQLAlchemyError as exc:
        session.rollback()

        logger.exception(
            "Database error while evaluating a Candidate "
            "for a Job."
        )

        raise AppException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="candidate_evaluation_failed",
            message=(
                "The Candidate evaluation could not be "
                "completed."
            ),
        ) from exc