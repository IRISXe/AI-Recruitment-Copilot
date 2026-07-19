from datetime import UTC, datetime
from hashlib import sha256
from uuid import UUID

from fastapi import status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.models.resume_profile import ResumeProfile
from app.parsing.resume_parser import (
    PARSER_VERSION,
    ResumeParsingError,
    parse_resume_text,
)
from app.repositories.resume_content_repository import (
    get_resume_content_by_resume_id as get_resume_content_record,
)
from app.repositories.resume_profile_repository import (
    create_resume_profile as create_resume_profile_record,
)
from app.repositories.resume_profile_repository import (
    get_resume_profile_by_resume_id as get_resume_profile_record,
)
from app.repositories.resume_profile_repository import (
    update_resume_profile as update_resume_profile_record,
)
from app.repositories.resume_repository import (
    get_resume_by_id as get_resume_by_id_record,
)


def calculate_source_text_sha256(
    text: str,
) -> str:
    return sha256(
        text.encode("utf-8")
    ).hexdigest()


def get_resume_profile(
    session: Session,
    resume_id: UUID,
) -> ResumeProfile:
    try:
        resume = get_resume_by_id_record(
            session,
            resume_id,
        )

        if resume is None:
            raise AppException(
                status_code=status.HTTP_404_NOT_FOUND,
                code="resume_not_found",
                message="The requested resume does not exist.",
            )

        resume_profile = get_resume_profile_record(
            session,
            resume_id=resume_id,
        )

        if resume_profile is None:
            raise AppException(
                status_code=status.HTTP_404_NOT_FOUND,
                code="resume_profile_not_found",
                message=(
                    "A structured profile is not available "
                    "for this resume."
                ),
            )

        return resume_profile

    except AppException:
        raise

    except SQLAlchemyError as exc:
        session.rollback()

        raise AppException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="resume_profile_retrieval_failed",
            message=(
                "The structured Resume profile "
                "could not be retrieved."
            ),
        ) from exc


def parse_resume_profile(
    session: Session,
    resume_id: UUID,
) -> ResumeProfile:
    try:
        resume = get_resume_by_id_record(
            session,
            resume_id,
        )

        if resume is None:
            raise AppException(
                status_code=status.HTTP_404_NOT_FOUND,
                code="resume_not_found",
                message="The requested resume does not exist.",
            )

        resume_content = get_resume_content_record(
            session,
            resume_id=resume_id,
        )

        if resume_content is None:
            raise AppException(
                status_code=status.HTTP_404_NOT_FOUND,
                code="resume_content_not_found",
                message=(
                    "Extracted content is not available "
                    "for this resume."
                ),
            )

        if resume_content.extraction_status != "completed":
            raise AppException(
                status_code=status.HTTP_409_CONFLICT,
                code="resume_content_not_ready",
                message=(
                    "Resume extraction must be completed "
                    "before parsing."
                ),
            )

        extracted_text = resume_content.extracted_text

        if extracted_text is None or not extracted_text.strip():
            raise AppException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                code="resume_content_empty",
                message=(
                    "The extracted Resume content is empty."
                ),
            )

        source_text_sha256 = calculate_source_text_sha256(
            extracted_text
        )

        resume_profile = get_resume_profile_record(
            session,
            resume_id=resume_id,
        )

        if resume_profile is None:
            resume_profile = create_resume_profile_record(
                session,
                resume_id=resume_id,
            )

        else:
            resume_profile = update_resume_profile_record(
                session,
                resume_profile=resume_profile,
                profile_data=None,
                parsing_status="pending",
                parsing_error=None,
                parser_version=None,
                source_text_sha256=source_text_sha256,
                parsed_at=None,
            )

        try:
            profile_data = parse_resume_text(
                extracted_text
            )

        except ResumeParsingError as exc:
            failed_profile = update_resume_profile_record(
                session,
                resume_profile=resume_profile,
                profile_data=None,
                parsing_status="failed",
                parsing_error=str(exc),
                parser_version=PARSER_VERSION,
                source_text_sha256=source_text_sha256,
                parsed_at=datetime.now(UTC),
            )

            session.commit()
            session.refresh(failed_profile)

            raise AppException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                code="resume_parsing_failed",
                message=(
                    "The Resume could not be parsed "
                    "into a structured profile."
                ),
            ) from exc

        completed_profile = update_resume_profile_record(
            session,
            resume_profile=resume_profile,
            profile_data=profile_data.model_dump(
                mode="json",
            ),
            parsing_status="completed",
            parsing_error=None,
            parser_version=PARSER_VERSION,
            source_text_sha256=source_text_sha256,
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
            code="resume_profile_persistence_failed",
            message=(
                "The structured Resume profile "
                "could not be saved."
            ),
        ) from exc