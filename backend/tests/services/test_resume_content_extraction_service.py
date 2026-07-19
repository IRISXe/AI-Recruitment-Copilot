from datetime import UTC
from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.extraction.resume_extractor import (
    EXTRACTOR_VERSION,
    ResumeDocumentReadError,
)
from app.models.resume import Resume
from app.models.resume_content import ResumeContent
from app.services.resume_content_service import (
    extract_resume_content,
)
from app.storage.resume_storage import (
    ResumeFileNotFoundError,
    ResumeStorageError,
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


def build_resume() -> MagicMock:
    resume = MagicMock(spec=Resume)
    resume.storage_path = (
        "local_storage/resumes/stored-resume.pdf"
    )
    resume.content_type = "application/pdf"

    return resume


def test_extract_resume_content_creates_completed_record() -> None:
    session = MagicMock(spec=Session)
    settings = MagicMock()
    resume = build_resume()
    pending_content = MagicMock(spec=ResumeContent)
    completed_content = MagicMock(spec=ResumeContent)

    resume_id = uuid4()
    file_path = Path("stored-resume.pdf")

    with patch(
        "app.services.resume_content_service.get_settings",
        return_value=settings,
    ):
        with patch(
            "app.services.resume_content_service."
            "get_resume_by_id_record",
            return_value=resume,
        ) as get_resume_record:
            with patch(
                "app.services.resume_content_service."
                "get_resume_file_path",
                return_value=file_path,
            ) as get_file_path:
                with patch(
                    "app.services.resume_content_service."
                    "get_resume_content_record",
                    return_value=None,
                ):
                    with patch(
                        "app.services.resume_content_service."
                        "create_resume_content_record",
                        return_value=pending_content,
                    ) as create_record:
                        with patch(
                            "app.services.resume_content_service."
                            "extract_resume_text",
                            return_value="Backend Developer",
                        ) as extract_text:
                            with patch(
                                "app.services."
                                "resume_content_service."
                                "update_resume_content_record",
                                return_value=completed_content,
                            ) as update_record:
                                result = (
                                    extract_resume_content(
                                        session=session,
                                        resume_id=resume_id,
                                    )
                                )

    get_resume_record.assert_called_once_with(
        session,
        resume_id,
    )

    get_file_path.assert_called_once_with(
        storage_path=resume.storage_path,
        settings=settings,
    )

    create_record.assert_called_once_with(
        session,
        resume_id=resume_id,
    )

    extract_text.assert_called_once_with(
        file_path=file_path,
        content_type="application/pdf",
    )

    update_args, update_kwargs = update_record.call_args

    assert update_args == (session,)
    assert update_kwargs["resume_content"] is pending_content
    assert update_kwargs["extracted_text"] == "Backend Developer"
    assert update_kwargs["extraction_status"] == "completed"
    assert update_kwargs["extraction_error"] is None
    assert (
        update_kwargs["extractor_version"]
        == EXTRACTOR_VERSION
    )
    assert update_kwargs["extracted_at"].tzinfo is UTC

    session.commit.assert_called_once_with()
    session.refresh.assert_called_once_with(
        completed_content
    )
    session.rollback.assert_not_called()

    assert result is completed_content


def test_extract_resume_content_resets_existing_record() -> None:
    session = MagicMock(spec=Session)
    settings = MagicMock()
    resume = build_resume()
    existing_content = MagicMock(spec=ResumeContent)
    completed_content = MagicMock(spec=ResumeContent)

    resume_id = uuid4()
    file_path = Path("stored-resume.pdf")

    with patch(
        "app.services.resume_content_service.get_settings",
        return_value=settings,
    ):
        with patch(
            "app.services.resume_content_service."
            "get_resume_by_id_record",
            return_value=resume,
        ):
            with patch(
                "app.services.resume_content_service."
                "get_resume_file_path",
                return_value=file_path,
            ):
                with patch(
                    "app.services.resume_content_service."
                    "get_resume_content_record",
                    return_value=existing_content,
                ):
                    with patch(
                        "app.services.resume_content_service."
                        "create_resume_content_record",
                    ) as create_record:
                        with patch(
                            "app.services.resume_content_service."
                            "extract_resume_text",
                            return_value="Updated Resume text",
                        ):
                            with patch(
                                "app.services."
                                "resume_content_service."
                                "update_resume_content_record",
                                side_effect=[
                                    existing_content,
                                    completed_content,
                                ],
                            ) as update_record:
                                result = (
                                    extract_resume_content(
                                        session=session,
                                        resume_id=resume_id,
                                    )
                                )

    create_record.assert_not_called()

    assert update_record.call_count == 2

    first_args, first_kwargs = (
        update_record.call_args_list[0]
    )

    assert first_args == (session,)
    assert first_kwargs["resume_content"] is existing_content
    assert first_kwargs["extracted_text"] is None
    assert first_kwargs["extraction_status"] == "pending"
    assert first_kwargs["extraction_error"] is None
    assert first_kwargs["extractor_version"] is None
    assert first_kwargs["extracted_at"] is None

    second_args, second_kwargs = (
        update_record.call_args_list[1]
    )

    assert second_args == (session,)
    assert second_kwargs["resume_content"] is existing_content
    assert second_kwargs["extracted_text"] == (
        "Updated Resume text"
    )
    assert second_kwargs["extraction_status"] == "completed"

    session.commit.assert_called_once_with()
    session.refresh.assert_called_once_with(
        completed_content
    )
    session.rollback.assert_not_called()

    assert result is completed_content


def test_extract_resume_content_raises_when_resume_missing() -> None:
    session = MagicMock(spec=Session)
    settings = MagicMock()
    resume_id = uuid4()

    with patch(
        "app.services.resume_content_service.get_settings",
        return_value=settings,
    ):
        with patch(
            "app.services.resume_content_service."
            "get_resume_by_id_record",
            return_value=None,
        ):
            with patch(
                "app.services.resume_content_service."
                "get_resume_file_path",
            ) as get_file_path:
                with pytest.raises(AppException) as exc_info:
                    extract_resume_content(
                        session=session,
                        resume_id=resume_id,
                    )

    get_file_path.assert_not_called()
    session.commit.assert_not_called()
    session.rollback.assert_not_called()
    session.refresh.assert_not_called()

    assert_app_exception(
        exc_info.value,
        expected_status=status.HTTP_404_NOT_FOUND,
        expected_code="resume_not_found",
        expected_message=(
            "The requested resume does not exist."
        ),
    )


def test_extract_resume_content_maps_missing_file() -> None:
    session = MagicMock(spec=Session)
    settings = MagicMock()
    resume = build_resume()
    resume_id = uuid4()

    with patch(
        "app.services.resume_content_service.get_settings",
        return_value=settings,
    ):
        with patch(
            "app.services.resume_content_service."
            "get_resume_by_id_record",
            return_value=resume,
        ):
            with patch(
                "app.services.resume_content_service."
                "get_resume_file_path",
                side_effect=ResumeFileNotFoundError(
                    "The Resume file could not be found."
                ),
            ):
                with patch(
                    "app.services.resume_content_service."
                    "get_resume_content_record",
                ) as get_content_record:
                    with pytest.raises(
                        AppException
                    ) as exc_info:
                        extract_resume_content(
                            session=session,
                            resume_id=resume_id,
                        )

    get_content_record.assert_not_called()
    session.commit.assert_not_called()
    session.rollback.assert_not_called()
    session.refresh.assert_not_called()

    assert_app_exception(
        exc_info.value,
        expected_status=status.HTTP_404_NOT_FOUND,
        expected_code="resume_file_not_found",
        expected_message=(
            "The Resume file could not be found."
        ),
    )


def test_extract_resume_content_maps_storage_error() -> None:
    session = MagicMock(spec=Session)
    settings = MagicMock()
    resume = build_resume()
    resume_id = uuid4()

    with patch(
        "app.services.resume_content_service.get_settings",
        return_value=settings,
    ):
        with patch(
            "app.services.resume_content_service."
            "get_resume_by_id_record",
            return_value=resume,
        ):
            with patch(
                "app.services.resume_content_service."
                "get_resume_file_path",
                side_effect=ResumeStorageError(
                    "filesystem failure"
                ),
            ):
                with pytest.raises(AppException) as exc_info:
                    extract_resume_content(
                        session=session,
                        resume_id=resume_id,
                    )

    session.commit.assert_not_called()
    session.rollback.assert_not_called()
    session.refresh.assert_not_called()

    assert_app_exception(
        exc_info.value,
        expected_status=(
            status.HTTP_500_INTERNAL_SERVER_ERROR
        ),
        expected_code="resume_extraction_storage_failed",
        expected_message=(
            "The Resume file could not be prepared "
            "for extraction."
        ),
    )

    assert "filesystem" not in exc_info.value.message


def test_extract_resume_content_persists_failed_extraction() -> None:
    session = MagicMock(spec=Session)
    settings = MagicMock()
    resume = build_resume()
    pending_content = MagicMock(spec=ResumeContent)
    failed_content = MagicMock(spec=ResumeContent)

    resume_id = uuid4()
    file_path = Path("stored-resume.pdf")

    with patch(
        "app.services.resume_content_service.get_settings",
        return_value=settings,
    ):
        with patch(
            "app.services.resume_content_service."
            "get_resume_by_id_record",
            return_value=resume,
        ):
            with patch(
                "app.services.resume_content_service."
                "get_resume_file_path",
                return_value=file_path,
            ):
                with patch(
                    "app.services.resume_content_service."
                    "get_resume_content_record",
                    return_value=None,
                ):
                    with patch(
                        "app.services.resume_content_service."
                        "create_resume_content_record",
                        return_value=pending_content,
                    ):
                        with patch(
                            "app.services.resume_content_service."
                            "extract_resume_text",
                            side_effect=ResumeDocumentReadError(
                                "The PDF Resume could not be read."
                            ),
                        ):
                            with patch(
                                "app.services."
                                "resume_content_service."
                                "update_resume_content_record",
                                return_value=failed_content,
                            ) as update_record:
                                with pytest.raises(
                                    AppException
                                ) as exc_info:
                                    extract_resume_content(
                                        session=session,
                                        resume_id=resume_id,
                                    )

    update_args, update_kwargs = update_record.call_args

    assert update_args == (session,)
    assert update_kwargs["resume_content"] is pending_content
    assert update_kwargs["extracted_text"] is None
    assert update_kwargs["extraction_status"] == "failed"
    assert update_kwargs["extraction_error"] == (
        "The PDF Resume could not be read."
    )
    assert (
        update_kwargs["extractor_version"]
        == EXTRACTOR_VERSION
    )
    assert update_kwargs["extracted_at"].tzinfo is UTC

    session.commit.assert_called_once_with()
    session.refresh.assert_called_once_with(
        failed_content
    )
    session.rollback.assert_not_called()

    assert_app_exception(
        exc_info.value,
        expected_status=(
            status.HTTP_422_UNPROCESSABLE_CONTENT
        ),
        expected_code="resume_extraction_failed",
        expected_message=(
            "The Resume text could not be extracted."
        ),
    )


def test_extract_resume_content_rolls_back_database_error() -> None:
    session = MagicMock(spec=Session)
    settings = MagicMock()
    resume = build_resume()
    resume_id = uuid4()
    file_path = Path("stored-resume.pdf")

    with patch(
        "app.services.resume_content_service.get_settings",
        return_value=settings,
    ):
        with patch(
            "app.services.resume_content_service."
            "get_resume_by_id_record",
            return_value=resume,
        ):
            with patch(
                "app.services.resume_content_service."
                "get_resume_file_path",
                return_value=file_path,
            ):
                with patch(
                    "app.services.resume_content_service."
                    "get_resume_content_record",
                    side_effect=SQLAlchemyError(
                        "database failure"
                    ),
                ):
                    with pytest.raises(
                        AppException
                    ) as exc_info:
                        extract_resume_content(
                            session=session,
                            resume_id=resume_id,
                        )

    session.rollback.assert_called_once_with()
    session.commit.assert_not_called()
    session.refresh.assert_not_called()

    assert_app_exception(
        exc_info.value,
        expected_status=(
            status.HTTP_500_INTERNAL_SERVER_ERROR
        ),
        expected_code=(
            "resume_extraction_persistence_failed"
        ),
        expected_message=(
            "The Resume extraction result "
            "could not be saved."
        ),
    )
