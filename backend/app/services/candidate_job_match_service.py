import logging
from datetime import UTC, datetime
from uuid import UUID

from fastapi import status
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.matching.candidate_job_matcher import (
    SCORING_VERSION,
    build_candidate_job_match_create,
    match_candidate_profile_to_job_requirements,
)
from app.models.candidate_job_match import CandidateJobMatch
from app.models.job_requirement_profile import (
    JobRequirementProfile,
)
from app.models.resume_profile import ResumeProfile
from app.repositories.candidate_job_match_repository import (
    create_candidate_job_match as create_match_record,
    get_candidate_job_match_by_candidate_and_job as get_match_record,
    update_candidate_job_match as update_match_record,
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
from app.repositories.resume_profile_repository import (
    get_resume_profile_by_resume_id as get_resume_profile_record,
)
from app.repositories.resume_repository import (
    get_primary_resume_by_candidate_id as get_primary_resume_record,
)
from app.schemas.candidate_job_match import (
    CandidateJobMatchUpdate,
)
from app.schemas.job_requirement_profile import (
    JobRequirementProfileData,
    JobRequirementProfileResponse,
)
from app.schemas.resume_profile import (
    ResumeProfileData,
    ResumeProfileResponse,
)


logger = logging.getLogger(__name__)


def _get_candidate_or_raise(
    session: Session,
    candidate_id: UUID,
) -> None:
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


def _get_job_or_raise(
    session: Session,
    job_id: UUID,
) -> None:
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


def _get_primary_resume_or_raise(
    session: Session,
    candidate_id: UUID,
) -> object:
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


def _get_completed_resume_profile_or_raise(
    session: Session,
    *,
    resume_id: UUID,
) -> ResumeProfile:
    resume_profile = get_resume_profile_record(
        session,
        resume_id=resume_id,
    )

    if resume_profile is None:
        raise AppException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="resume_profile_not_found",
            message=(
                "A structured profile is not available for "
                "the candidate's primary Resume."
            ),
        )

    if (
        resume_profile.parsing_status != "completed"
        or resume_profile.profile_data is None
        or resume_profile.parser_version is None
        or resume_profile.source_text_sha256 is None
    ):
        raise AppException(
            status_code=status.HTTP_409_CONFLICT,
            code="resume_profile_not_ready",
            message=(
                "The candidate's primary Resume must have a "
                "completed structured profile before matching."
            ),
        )

    return resume_profile


def _get_completed_job_profile_or_raise(
    session: Session,
    *,
    job_id: UUID,
) -> JobRequirementProfile:
    job_profile = get_job_profile_record(
        session,
        job_id=job_id,
    )

    if job_profile is None:
        raise AppException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="job_requirement_profile_not_found",
            message=(
                "A structured requirement profile is not "
                "available for this job."
            ),
        )

    if (
        job_profile.parsing_status != "completed"
        or job_profile.profile_data is None
        or job_profile.parser_version is None
        or job_profile.source_description_sha256 is None
    ):
        raise AppException(
            status_code=status.HTTP_409_CONFLICT,
            code="job_requirement_profile_not_ready",
            message=(
                "The job must have a completed structured "
                "requirement profile before matching."
            ),
        )

    return job_profile


def _validate_resume_profile_data(
    resume_profile: ResumeProfile,
) -> ResumeProfileData:
    try:
        return ResumeProfileData.model_validate(
            resume_profile.profile_data
        )
    except ValidationError as exc:
        raise AppException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            code="resume_profile_data_invalid",
            message=(
                "The structured Resume profile contains "
                "invalid data."
            ),
        ) from exc


def _validate_job_profile_data(
    job_profile: JobRequirementProfile,
) -> JobRequirementProfileData:
    try:
        return JobRequirementProfileData.model_validate(
            job_profile.profile_data
        )
    except ValidationError as exc:
        raise AppException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            code="job_requirement_profile_data_invalid",
            message=(
                "The structured job requirement profile "
                "contains invalid data."
            ),
        ) from exc


def _build_resume_profile_response(
    *,
    resume_profile: ResumeProfile,
    profile_data: ResumeProfileData,
) -> ResumeProfileResponse:
    return ResumeProfileResponse(
        id=resume_profile.id,
        resume_id=resume_profile.resume_id,
        profile_data=profile_data,
        parsing_status=resume_profile.parsing_status,
        parsing_error=resume_profile.parsing_error,
        parser_version=resume_profile.parser_version,
        source_text_sha256=(
            resume_profile.source_text_sha256
        ),
        parsed_at=resume_profile.parsed_at,
        created_at=resume_profile.created_at,
        updated_at=resume_profile.updated_at,
    )


def _build_job_profile_response(
    *,
    job_profile: JobRequirementProfile,
    profile_data: JobRequirementProfileData,
) -> JobRequirementProfileResponse:
    return JobRequirementProfileResponse(
        id=job_profile.id,
        job_id=job_profile.job_id,
        profile_data=profile_data,
        parsing_status=job_profile.parsing_status,
        parsing_error=job_profile.parsing_error,
        parser_version=job_profile.parser_version,
        source_description_sha256=(
            job_profile.source_description_sha256
        ),
        parsed_at=job_profile.parsed_at,
        created_at=job_profile.created_at,
        updated_at=job_profile.updated_at,
    )


def _is_existing_match_current(
    *,
    existing_match: CandidateJobMatch,
    resume_profile: ResumeProfile,
    job_profile: JobRequirementProfile,
) -> bool:
    return (
        existing_match.resume_id
        == resume_profile.resume_id
        and existing_match.resume_profile_id
        == resume_profile.id
        and existing_match.job_requirement_profile_id
        == job_profile.id
        and existing_match.scoring_version
        == SCORING_VERSION
        and existing_match.source_resume_text_sha256
        == resume_profile.source_text_sha256
        and existing_match.source_resume_parser_version
        == resume_profile.parser_version
        and existing_match.source_job_description_sha256
        == job_profile.source_description_sha256
        and existing_match.source_job_parser_version
        == job_profile.parser_version
    )


def generate_candidate_job_match(
    session: Session,
    *,
    candidate_id: UUID,
    job_id: UUID,
    force: bool = False,
) -> CandidateJobMatch:
    try:
        _get_candidate_or_raise(
            session,
            candidate_id,
        )
        _get_job_or_raise(
            session,
            job_id,
        )

        primary_resume = _get_primary_resume_or_raise(
            session,
            candidate_id,
        )

        resume_profile = (
            _get_completed_resume_profile_or_raise(
                session,
                resume_id=primary_resume.id,
            )
        )
        job_profile = _get_completed_job_profile_or_raise(
            session,
            job_id=job_id,
        )

        resume_profile_data = (
            _validate_resume_profile_data(
                resume_profile
            )
        )
        job_profile_data = _validate_job_profile_data(
            job_profile
        )

        existing_match = get_match_record(
            session,
            candidate_id=candidate_id,
            job_id=job_id,
        )

        if (
            existing_match is not None
            and not force
            and _is_existing_match_current(
                existing_match=existing_match,
                resume_profile=resume_profile,
                job_profile=job_profile,
            )
        ):
            return existing_match

        computation = (
            match_candidate_profile_to_job_requirements(
                resume_profile=resume_profile_data,
                job_requirement_profile=job_profile_data,
                candidate_work_mode=None,
            )
        )

        resume_profile_response = (
            _build_resume_profile_response(
                resume_profile=resume_profile,
                profile_data=resume_profile_data,
            )
        )
        job_profile_response = (
            _build_job_profile_response(
                job_profile=job_profile,
                profile_data=job_profile_data,
            )
        )

        try:
            create_payload = (
                build_candidate_job_match_create(
                    candidate_id=candidate_id,
                    job_id=job_id,
                    resume_profile=(
                        resume_profile_response
                    ),
                    job_requirement_profile=(
                        job_profile_response
                    ),
                    computation=computation,
                    matched_at=datetime.now(UTC),
                )
            )
        except ValueError as exc:
            raise AppException(
                status_code=(
                    status.HTTP_422_UNPROCESSABLE_CONTENT
                ),
                code="candidate_job_match_input_invalid",
                message=(
                    "The candidate and job profiles could not "
                    "be used to calculate a match."
                ),
            ) from exc

        if existing_match is None:
            candidate_job_match = create_match_record(
                session,
                create_payload,
            )
        else:
            update_payload = CandidateJobMatchUpdate(
                **create_payload.model_dump(
                    exclude={
                        "candidate_id",
                        "job_id",
                    }
                )
            )

            candidate_job_match = update_match_record(
                session,
                match=existing_match,
                payload=update_payload,
            )

        session.commit()
        session.refresh(candidate_job_match)

        return candidate_job_match

    except AppException:
        raise

    except SQLAlchemyError as exc:
        session.rollback()

        logger.exception(
            "Database error while generating a "
            "Candidate–Job match."
        )

        raise AppException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="candidate_job_match_persistence_failed",
            message=(
                "The Candidate–Job match could not be "
                "generated or saved."
            ),
        ) from exc