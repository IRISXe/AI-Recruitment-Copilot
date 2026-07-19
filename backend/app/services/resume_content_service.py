from datetime import UTC, datetime
from uuid import UUID

from fastapi import status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import AppException
from app.extraction.resume_extractor import (
    EXTRACTOR_VERSION,
    ResumeExtractionError,
    extract_resume_text,
)
from app.models.resume_content import ResumeContent
from app.repositories.resume_content_repository import (
    create_resume_content as create_resume_content_record,
)
from app.repositories.resume_content_repository import (
    get_resume_content_by_resume_id as get_resume_content_record,
)
from app.repositories.resume_content_repository import (
    update_resume_content as update_resume_content_record,
)
from app.repositories.resume_repository import (
    get_resume_by_id as get_resume_by_id_record,
)
from app.storage.resume_storage import (
    ResumeFileNotFoundError,
    ResumeStorageError,
    get_resume_file_path,
)


def get_resume_content(
    session: Session,
    resume_id: UUID,
) -> ResumeContent:
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

        return resume_content

    except AppException:
        raise

    except SQLAlchemyError as exc:
        session.rollback()

        raise AppException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="resume_content_retrieval_failed",
            message=(
                "The extracted Resume content "
                "could not be retrieved."
            ),
        ) from exc


def extract_resume_content(
    session: Session,
    resume_id: UUID,
) -> ResumeContent:
    settings = get_settings()

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

        file_path = get_resume_file_path(
            storage_path=resume.storage_path,
            settings=settings,
        )

        resume_content = get_resume_content_record(
            session,
            resume_id=resume_id,
        )

        if resume_content is None:
            resume_content = create_resume_content_record(
                session,
                resume_id=resume_id,
            )

        else:
            resume_content = update_resume_content_record(
                session,
                resume_content=resume_content,
                extracted_text=None,
                extraction_status="pending",
                extraction_error=None,
                extractor_version=None,
                extracted_at=None,
            )

        try:
            extracted_text = extract_resume_text(
                file_path=file_path,
                content_type=resume.content_type,
            )

        except ResumeExtractionError as exc:
            failed_content = update_resume_content_record(
                session,
                resume_content=resume_content,
                extracted_text=None,
                extraction_status="failed",
                extraction_error=str(exc),
                extractor_version=EXTRACTOR_VERSION,
                extracted_at=datetime.now(UTC),
            )

            session.commit()
            session.refresh(failed_content)

            raise AppException(
                status_code=(
                    status.HTTP_422_UNPROCESSABLE_CONTENT
                ),
                code="resume_extraction_failed",
                message=(
                    "The Resume text could not be extracted."
                ),
            ) from exc

        completed_content = update_resume_content_record(
            session,
            resume_content=resume_content,
            extracted_text=extracted_text,
            extraction_status="completed",
            extraction_error=None,
            extractor_version=EXTRACTOR_VERSION,
            extracted_at=datetime.now(UTC),
        )

        session.commit()
        session.refresh(completed_content)

        return completed_content

    except AppException:
        raise

    except ResumeFileNotFoundError as exc:
        raise AppException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="resume_file_not_found",
            message="The Resume file could not be found.",
        ) from exc

    except ResumeStorageError as exc:
        raise AppException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="resume_extraction_storage_failed",
            message=(
                "The Resume file could not be prepared "
                "for extraction."
            ),
        ) from exc

    except SQLAlchemyError as exc:
        session.rollback()

        raise AppException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="resume_extraction_persistence_failed",
            message=(
                "The Resume extraction result "
                "could not be saved."
            ),
        ) from exc
