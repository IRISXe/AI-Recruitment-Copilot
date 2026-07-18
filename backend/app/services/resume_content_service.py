from uuid import UUID

from fastapi import status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.models.resume_content import ResumeContent
from app.repositories.resume_content_repository import (
    get_resume_content_by_resume_id as get_resume_content_record,
)
from app.repositories.resume_repository import (
    get_resume_by_id as get_resume_by_id_record,
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