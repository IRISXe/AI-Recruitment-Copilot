from datetime import UTC, datetime
from hashlib import sha256
from uuid import UUID

from fastapi import status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.models.job_requirement_profile import JobRequirementProfile
from app.parsing.job_description_parser import (
    PARSER_VERSION,
    JobDescriptionParsingError,
    parse_job_description,
)
from app.repositories.job_repository import (
    get_job_by_id as get_job_by_id_record,
)
from app.repositories.job_requirement_profile_repository import (
    create_job_requirement_profile as create_profile_record,
    get_job_requirement_profile_by_job_id as get_profile_record,
    update_job_requirement_profile as update_profile_record,
)


def calculate_source_description_sha256(
    description: str,
) -> str:
    return sha256(
        description.encode("utf-8")
    ).hexdigest()


def _get_existing_job(
    session: Session,
    job_id: UUID,
) -> object:
    job = get_job_by_id_record(
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


def get_job_requirement_profile(
    session: Session,
    job_id: UUID,
) -> JobRequirementProfile:
    try:
        _get_existing_job(
            session,
            job_id,
        )

        profile = get_profile_record(
            session,
            job_id=job_id,
        )

    except SQLAlchemyError as exc:
        session.rollback()

        raise AppException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="job_requirement_profile_retrieval_failed",
            message=(
                "The structured job requirement profile "
                "could not be retrieved."
            ),
        ) from exc

    if profile is None:
        raise AppException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="job_requirement_profile_not_found",
            message=(
                "A structured requirement profile is not "
                "available for this job."
            ),
        )

    return profile


def parse_job_requirement_profile(
    session: Session,
    *,
    job_id: UUID,
    force: bool = False,
) -> JobRequirementProfile:
    try:
        job = _get_existing_job(
            session,
            job_id,
        )

        description = job.description

        if description is None or not description.strip():
            raise AppException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                code="job_description_empty",
                message=(
                    "The job description is empty and "
                    "cannot be processed."
                ),
            )

        source_description_sha256 = (
            calculate_source_description_sha256(
                description
            )
        )

        profile = get_profile_record(
            session,
            job_id=job_id,
        )

        if (
            profile is not None
            and profile.parsing_status == "completed"
            and profile.source_description_sha256
            == source_description_sha256
            and profile.parser_version == PARSER_VERSION
            and not force
        ):
            return profile

        if profile is None:
            profile = create_profile_record(
                session,
                job_id=job_id,
            )
        else:
            profile = update_profile_record(
                session,
                profile=profile,
                profile_data=None,
                parsing_status="pending",
                parsing_error=None,
                parser_version=None,
                source_description_sha256=(
                    source_description_sha256
                ),
                parsed_at=None,
            )

        try:
            parsed_profile = parse_job_description(
                description
            )

        except JobDescriptionParsingError as exc:
            failed_profile = update_profile_record(
                session,
                profile=profile,
                profile_data=None,
                parsing_status="failed",
                parsing_error=str(exc),
                parser_version=PARSER_VERSION,
                source_description_sha256=(
                    source_description_sha256
                ),
                parsed_at=datetime.now(UTC),
            )

            session.commit()
            session.refresh(failed_profile)

            raise AppException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                code="job_description_parsing_failed",
                message=(
                    "The job description could not be parsed "
                    "into structured requirements."
                ),
            ) from exc

        completed_profile = update_profile_record(
            session,
            profile=profile,
            profile_data=parsed_profile.model_dump(
                mode="json"
            ),
            parsing_status="completed",
            parsing_error=None,
            parser_version=PARSER_VERSION,
            source_description_sha256=(
                source_description_sha256
            ),
            parsed_at=datetime.now(UTC),
        )

        session.commit()
        session.refresh(completed_profile)

        return completed_profile

    except AppException:
        raise

    except SQLAlchemyError as exc:
        session.rollback()

        raise AppException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="job_requirement_profile_persistence_failed",
            message=(
                "The structured job requirement profile "
                "could not be saved."
            ),
        ) from exc