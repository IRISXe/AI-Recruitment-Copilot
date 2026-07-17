from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi import UploadFile, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.models.candidate import Candidate
from app.models.resume import Resume
from app.schemas.resume import ResumeCreate, ResumeUpdate
from app.storage.resume_storage import (
    InvalidResumeFileError,
    ResumeFileNotFoundError,
    ResumeFileTooLargeError,
    ResumeStorageError,
    StoredResumeFile,
)
from app.services.resume_service import (
    create_resume,
    delete_resume,
    get_resume_by_id,
    get_resume_download,
    list_resumes,
    update_resume,
    upload_resume,
)


def build_create_payload(
    *,
    candidate_id: UUID | None = None,
    stored_filename: str = "harsha-resume.pdf",
    is_primary: bool = False,
) -> ResumeCreate:
    return ResumeCreate(
        candidate_id=candidate_id or uuid4(),
        original_filename="Harsha_Resume.pdf",
        stored_filename=stored_filename,
        storage_path=f"uploads/resumes/{stored_filename}",
        content_type="application/pdf",
        file_size_bytes=245760,
        is_primary=is_primary,
    )


def build_uploaded_file() -> UploadFile:
    uploaded_file = MagicMock(spec=UploadFile)
    uploaded_file.filename = "Harsha_Resume.pdf"
    uploaded_file.content_type = "application/pdf"
    uploaded_file.file = MagicMock()

    return uploaded_file


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


def test_create_resume_validates_candidate_commits_and_refreshes() -> None:
    session = MagicMock(spec=Session)
    candidate = MagicMock(spec=Candidate)
    resume = MagicMock(spec=Resume)
    payload = build_create_payload()

    with patch(
        "app.services.resume_service.get_candidate_by_id_record",
        return_value=candidate,
    ) as get_candidate:
        with patch(
            "app.services.resume_service.get_primary_resume_record",
        ) as get_primary:
            with patch(
                "app.services.resume_service.create_resume_record",
                return_value=resume,
            ) as create_record:
                result = create_resume(
                    session=session,
                    payload=payload,
                )

    get_candidate.assert_called_once_with(
        session,
        payload.candidate_id,
    )
    get_primary.assert_not_called()
    create_record.assert_called_once_with(
        session,
        payload,
    )

    session.commit.assert_called_once_with()
    session.refresh.assert_called_once_with(resume)
    session.rollback.assert_not_called()

    assert result is resume


def test_create_resume_raises_when_candidate_does_not_exist() -> None:
    session = MagicMock(spec=Session)
    payload = build_create_payload()

    with patch(
        "app.services.resume_service.get_candidate_by_id_record",
        return_value=None,
    ) as get_candidate:
        with patch(
            "app.services.resume_service.get_primary_resume_record",
        ) as get_primary:
            with patch(
                "app.services.resume_service.create_resume_record",
            ) as create_record:
                with pytest.raises(AppException) as exc_info:
                    create_resume(
                        session=session,
                        payload=payload,
                    )

    get_candidate.assert_called_once_with(
        session,
        payload.candidate_id,
    )
    get_primary.assert_not_called()
    create_record.assert_not_called()

    session.commit.assert_not_called()
    session.refresh.assert_not_called()
    session.rollback.assert_not_called()

    assert_app_exception(
        exc_info.value,
        expected_status=status.HTTP_404_NOT_FOUND,
        expected_code="candidate_not_found",
        expected_message="The requested candidate does not exist.",
    )


def test_create_primary_resume_demotes_existing_primary() -> None:
    session = MagicMock(spec=Session)
    candidate = MagicMock(spec=Candidate)
    existing_primary = MagicMock(spec=Resume)
    new_resume = MagicMock(spec=Resume)
    payload = build_create_payload(is_primary=True)

    with patch(
        "app.services.resume_service.get_candidate_by_id_record",
        return_value=candidate,
    ):
        with patch(
            "app.services.resume_service.get_primary_resume_record",
            return_value=existing_primary,
        ) as get_primary:
            with patch(
                "app.services.resume_service.update_resume_record",
                return_value=existing_primary,
            ) as update_record:
                with patch(
                    "app.services.resume_service.create_resume_record",
                    return_value=new_resume,
                ) as create_record:
                    result = create_resume(
                        session=session,
                        payload=payload,
                    )

    get_primary.assert_called_once_with(
        session,
        payload.candidate_id,
    )

    update_record.assert_called_once()
    update_args, update_kwargs = update_record.call_args

    assert update_args == (session,)
    assert update_kwargs["resume"] is existing_primary
    assert update_kwargs["payload"].is_primary is False

    create_record.assert_called_once_with(
        session,
        payload,
    )

    session.commit.assert_called_once_with()
    session.refresh.assert_called_once_with(new_resume)
    session.rollback.assert_not_called()

    assert result is new_resume


def test_create_resume_rolls_back_database_error() -> None:
    session = MagicMock(spec=Session)
    payload = build_create_payload()

    with patch(
        "app.services.resume_service.get_candidate_by_id_record",
        side_effect=SQLAlchemyError("database failure"),
    ):
        with pytest.raises(AppException) as exc_info:
            create_resume(
                session=session,
                payload=payload,
            )

    session.rollback.assert_called_once_with()
    session.commit.assert_not_called()
    session.refresh.assert_not_called()

    assert_app_exception(
        exc_info.value,
        expected_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        expected_code="resume_creation_failed",
        expected_message="The resume could not be created.",
    )


def test_get_resume_by_id_returns_existing_resume() -> None:
    session = MagicMock(spec=Session)
    resume = MagicMock(spec=Resume)
    resume_id = uuid4()

    with patch(
        "app.services.resume_service.get_resume_by_id_record",
        return_value=resume,
    ) as get_record:
        result = get_resume_by_id(
            session=session,
            resume_id=resume_id,
        )

    get_record.assert_called_once_with(
        session,
        resume_id,
    )
    session.rollback.assert_not_called()

    assert result is resume


def test_get_resume_by_id_raises_not_found() -> None:
    session = MagicMock(spec=Session)
    resume_id = uuid4()

    with patch(
        "app.services.resume_service.get_resume_by_id_record",
        return_value=None,
    ):
        with pytest.raises(AppException) as exc_info:
            get_resume_by_id(
                session=session,
                resume_id=resume_id,
            )

    session.rollback.assert_not_called()

    assert_app_exception(
        exc_info.value,
        expected_status=status.HTTP_404_NOT_FOUND,
        expected_code="resume_not_found",
        expected_message="The requested resume does not exist.",
    )


def test_get_resume_by_id_rolls_back_database_error() -> None:
    session = MagicMock(spec=Session)
    resume_id = uuid4()

    with patch(
        "app.services.resume_service.get_resume_by_id_record",
        side_effect=SQLAlchemyError("database failure"),
    ):
        with pytest.raises(AppException) as exc_info:
            get_resume_by_id(
                session=session,
                resume_id=resume_id,
            )

    session.rollback.assert_called_once_with()

    assert_app_exception(
        exc_info.value,
        expected_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        expected_code="resume_retrieval_failed",
        expected_message="The resume could not be retrieved.",
    )


def test_get_resume_download_returns_download_information() -> None:
    session = MagicMock(spec=Session)
    settings = MagicMock()
    resume = MagicMock(spec=Resume)
    resume_id = uuid4()

    file_path = Path(
        "local_storage/resumes/stored-resume.pdf"
    ).resolve()

    resume.storage_path = (
        "local_storage/resumes/stored-resume.pdf"
    )
    resume.original_filename = "Harsha_Resume.pdf"
    resume.content_type = "application/pdf"

    with patch(
        "app.services.resume_service.get_settings",
        return_value=settings,
    ):
        with patch(
            "app.services.resume_service.get_resume_by_id_record",
            return_value=resume,
        ) as get_record:
            with patch(
                "app.services.resume_service.get_resume_file_path",
                return_value=file_path,
            ) as get_file_path:
                result = get_resume_download(
                    session=session,
                    resume_id=resume_id,
                )

    get_record.assert_called_once_with(
        session,
        resume_id,
    )

    get_file_path.assert_called_once_with(
        storage_path=resume.storage_path,
        settings=settings,
    )

    session.commit.assert_not_called()
    session.rollback.assert_not_called()
    session.refresh.assert_not_called()

    assert result.file_path == file_path
    assert result.filename == "Harsha_Resume.pdf"
    assert result.content_type == "application/pdf"


def test_get_resume_download_maps_missing_physical_file() -> None:
    session = MagicMock(spec=Session)
    settings = MagicMock()
    resume = MagicMock(spec=Resume)
    resume_id = uuid4()

    resume.storage_path = (
        "local_storage/resumes/missing-resume.pdf"
    )
    resume.original_filename = "Harsha_Resume.pdf"
    resume.content_type = "application/pdf"

    with patch(
        "app.services.resume_service.get_settings",
        return_value=settings,
    ):
        with patch(
            "app.services.resume_service.get_resume_by_id_record",
            return_value=resume,
        ):
            with patch(
                "app.services.resume_service.get_resume_file_path",
                side_effect=ResumeFileNotFoundError(
                    "The Resume file could not be found."
                ),
            ):
                with pytest.raises(AppException) as exc_info:
                    get_resume_download(
                        session=session,
                        resume_id=resume_id,
                    )

    session.commit.assert_not_called()
    session.rollback.assert_not_called()
    session.refresh.assert_not_called()

    assert_app_exception(
        exc_info.value,
        expected_status=status.HTTP_404_NOT_FOUND,
        expected_code="resume_file_not_found",
        expected_message="The Resume file could not be found.",
    )


def test_get_resume_download_maps_unsafe_storage_path() -> None:
    session = MagicMock(spec=Session)
    settings = MagicMock()
    resume = MagicMock(spec=Resume)
    resume_id = uuid4()

    resume.storage_path = (
        "external-storage/resumes/private-resume.pdf"
    )
    resume.original_filename = "Harsha_Resume.pdf"
    resume.content_type = "application/pdf"

    with patch(
        "app.services.resume_service.get_settings",
        return_value=settings,
    ):
        with patch(
            "app.services.resume_service.get_resume_by_id_record",
            return_value=resume,
        ):
            with patch(
                "app.services.resume_service.get_resume_file_path",
                side_effect=ResumeStorageError(
                    "The storage path is outside the configured "
                    "storage directory."
                ),
            ):
                with pytest.raises(AppException) as exc_info:
                    get_resume_download(
                        session=session,
                        resume_id=resume_id,
                    )

    session.commit.assert_not_called()
    session.rollback.assert_not_called()
    session.refresh.assert_not_called()

    assert_app_exception(
        exc_info.value,
        expected_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        expected_code="resume_download_failed",
        expected_message=(
            "The Resume file could not be downloaded."
        ),
    )

    assert "external-storage" not in exc_info.value.message
    assert resume.storage_path not in exc_info.value.message


def test_list_resumes_returns_repository_results() -> None:
    session = MagicMock(spec=Session)
    candidate_id = uuid4()
    resumes = [
        MagicMock(spec=Resume),
        MagicMock(spec=Resume),
    ]

    with patch(
        "app.services.resume_service.list_resumes_records",
        return_value=resumes,
    ) as list_records:
        result = list_resumes(
            session=session,
            offset=10,
            limit=20,
            candidate_id=candidate_id,
        )

    list_records.assert_called_once_with(
        session,
        offset=10,
        limit=20,
        candidate_id=candidate_id,
    )
    session.rollback.assert_not_called()

    assert result is resumes


def test_list_resumes_rolls_back_database_error() -> None:
    session = MagicMock(spec=Session)

    with patch(
        "app.services.resume_service.list_resumes_records",
        side_effect=SQLAlchemyError("database failure"),
    ):
        with pytest.raises(AppException) as exc_info:
            list_resumes(
                session=session,
                offset=0,
                limit=20,
            )

    session.rollback.assert_called_once_with()

    assert_app_exception(
        exc_info.value,
        expected_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        expected_code="resume_listing_failed",
        expected_message="The resumes could not be retrieved.",
    )


def test_update_resume_commits_refreshes_and_returns_resume() -> None:
    session = MagicMock(spec=Session)
    resume = MagicMock(spec=Resume)
    updated_resume = MagicMock(spec=Resume)
    resume_id = uuid4()
    payload = ResumeUpdate(is_primary=False)

    with patch(
        "app.services.resume_service.get_resume_by_id_record",
        return_value=resume,
    ) as get_record:
        with patch(
            "app.services.resume_service.get_primary_resume_record",
        ) as get_primary:
            with patch(
                "app.services.resume_service.update_resume_record",
                return_value=updated_resume,
            ) as update_record:
                result = update_resume(
                    session=session,
                    resume_id=resume_id,
                    payload=payload,
                )

    get_record.assert_called_once_with(
        session,
        resume_id,
    )
    get_primary.assert_not_called()
    update_record.assert_called_once_with(
        session,
        resume=resume,
        payload=payload,
    )

    session.commit.assert_called_once_with()
    session.refresh.assert_called_once_with(updated_resume)
    session.rollback.assert_not_called()

    assert result is updated_resume


def test_update_primary_resume_demotes_previous_primary() -> None:
    session = MagicMock(spec=Session)

    candidate_id = uuid4()
    resume_id = uuid4()
    existing_primary_id = uuid4()

    resume = MagicMock(spec=Resume)
    resume.id = resume_id
    resume.candidate_id = candidate_id

    existing_primary = MagicMock(spec=Resume)
    existing_primary.id = existing_primary_id
    existing_primary.candidate_id = candidate_id

    updated_resume = MagicMock(spec=Resume)
    payload = ResumeUpdate(is_primary=True)

    with patch(
        "app.services.resume_service.get_resume_by_id_record",
        return_value=resume,
    ):
        with patch(
            "app.services.resume_service.get_primary_resume_record",
            return_value=existing_primary,
        ) as get_primary:
            with patch(
                "app.services.resume_service.update_resume_record",
                side_effect=[
                    existing_primary,
                    updated_resume,
                ],
            ) as update_record:
                result = update_resume(
                    session=session,
                    resume_id=resume_id,
                    payload=payload,
                )

    get_primary.assert_called_once_with(
        session,
        candidate_id,
    )

    assert update_record.call_count == 2

    first_args, first_kwargs = update_record.call_args_list[0]
    assert first_args == (session,)
    assert first_kwargs["resume"] is existing_primary
    assert first_kwargs["payload"].is_primary is False

    second_args, second_kwargs = update_record.call_args_list[1]
    assert second_args == (session,)
    assert second_kwargs["resume"] is resume
    assert second_kwargs["payload"] is payload

    session.commit.assert_called_once_with()
    session.refresh.assert_called_once_with(updated_resume)
    session.rollback.assert_not_called()

    assert result is updated_resume


def test_update_current_primary_does_not_demote_itself() -> None:
    session = MagicMock(spec=Session)
    candidate_id = uuid4()
    resume_id = uuid4()

    resume = MagicMock(spec=Resume)
    resume.id = resume_id
    resume.candidate_id = candidate_id

    updated_resume = MagicMock(spec=Resume)
    payload = ResumeUpdate(is_primary=True)

    with patch(
        "app.services.resume_service.get_resume_by_id_record",
        return_value=resume,
    ):
        with patch(
            "app.services.resume_service.get_primary_resume_record",
            return_value=resume,
        ):
            with patch(
                "app.services.resume_service.update_resume_record",
                return_value=updated_resume,
            ) as update_record:
                result = update_resume(
                    session=session,
                    resume_id=resume_id,
                    payload=payload,
                )

    update_record.assert_called_once_with(
        session,
        resume=resume,
        payload=payload,
    )

    session.commit.assert_called_once_with()
    session.refresh.assert_called_once_with(updated_resume)
    session.rollback.assert_not_called()

    assert result is updated_resume


def test_update_resume_raises_not_found() -> None:
    session = MagicMock(spec=Session)
    resume_id = uuid4()
    payload = ResumeUpdate(is_primary=True)

    with patch(
        "app.services.resume_service.get_resume_by_id_record",
        return_value=None,
    ) as get_record:
        with patch(
            "app.services.resume_service.update_resume_record",
        ) as update_record:
            with pytest.raises(AppException) as exc_info:
                update_resume(
                    session=session,
                    resume_id=resume_id,
                    payload=payload,
                )

    get_record.assert_called_once_with(
        session,
        resume_id,
    )
    update_record.assert_not_called()

    session.commit.assert_not_called()
    session.refresh.assert_not_called()
    session.rollback.assert_not_called()

    assert_app_exception(
        exc_info.value,
        expected_status=status.HTTP_404_NOT_FOUND,
        expected_code="resume_not_found",
        expected_message="The requested resume does not exist.",
    )


def test_update_resume_rolls_back_database_error() -> None:
    session = MagicMock(spec=Session)
    resume = MagicMock(spec=Resume)
    resume_id = uuid4()
    payload = ResumeUpdate(is_primary=False)

    with patch(
        "app.services.resume_service.get_resume_by_id_record",
        return_value=resume,
    ):
        with patch(
            "app.services.resume_service.update_resume_record",
            side_effect=SQLAlchemyError("database failure"),
        ):
            with pytest.raises(AppException) as exc_info:
                update_resume(
                    session=session,
                    resume_id=resume_id,
                    payload=payload,
                )

    session.rollback.assert_called_once_with()
    session.commit.assert_not_called()
    session.refresh.assert_not_called()

    assert_app_exception(
        exc_info.value,
        expected_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        expected_code="resume_update_failed",
        expected_message="The resume could not be updated.",
    )


def test_delete_resume_commits_and_removes_stored_file() -> None:
    session = MagicMock(spec=Session)
    settings = MagicMock()
    resume = MagicMock(spec=Resume)
    resume_id = uuid4()

    resume.storage_path = (
        "local_storage/resumes/stored-resume.pdf"
    )

    with patch(
        "app.services.resume_service.get_settings",
        return_value=settings,
    ):
        with patch(
            "app.services.resume_service.get_resume_by_id_record",
            return_value=resume,
        ) as get_record:
            with patch(
                "app.services.resume_service.delete_resume_record",
            ) as delete_record:
                with patch(
                    "app.services.resume_service.delete_resume_file",
                ) as delete_file:
                    result = delete_resume(
                        session=session,
                        resume_id=resume_id,
                    )

    get_record.assert_called_once_with(
        session,
        resume_id,
    )

    delete_record.assert_called_once_with(
        session,
        resume=resume,
    )

    session.commit.assert_called_once_with()
    session.rollback.assert_not_called()

    delete_file.assert_called_once_with(
        storage_path=resume.storage_path,
        settings=settings,
    )

    assert result is None


def test_delete_resume_raises_not_found() -> None:
    session = MagicMock(spec=Session)
    settings = MagicMock()
    resume_id = uuid4()

    with patch(
        "app.services.resume_service.get_settings",
        return_value=settings,
    ):
        with patch(
            "app.services.resume_service.get_resume_by_id_record",
            return_value=None,
        ) as get_record:
            with patch(
                "app.services.resume_service.delete_resume_record",
            ) as delete_record:
                with patch(
                    "app.services.resume_service.delete_resume_file",
                ) as delete_file:
                    with pytest.raises(AppException) as exc_info:
                        delete_resume(
                            session=session,
                            resume_id=resume_id,
                        )

    get_record.assert_called_once_with(
        session,
        resume_id,
    )

    delete_record.assert_not_called()
    delete_file.assert_not_called()

    session.commit.assert_not_called()
    session.rollback.assert_not_called()

    assert_app_exception(
        exc_info.value,
        expected_status=status.HTTP_404_NOT_FOUND,
        expected_code="resume_not_found",
        expected_message="The requested resume does not exist.",
    )


def test_delete_resume_rolls_back_database_error() -> None:
    session = MagicMock(spec=Session)
    settings = MagicMock()
    resume = MagicMock(spec=Resume)
    resume_id = uuid4()

    resume.storage_path = (
        "local_storage/resumes/stored-resume.pdf"
    )

    with patch(
        "app.services.resume_service.get_settings",
        return_value=settings,
    ):
        with patch(
            "app.services.resume_service.get_resume_by_id_record",
            return_value=resume,
        ):
            with patch(
                "app.services.resume_service.delete_resume_record",
                side_effect=SQLAlchemyError(
                    "database failure"
                ),
            ):
                with patch(
                    "app.services.resume_service.delete_resume_file",
                ) as delete_file:
                    with pytest.raises(AppException) as exc_info:
                        delete_resume(
                            session=session,
                            resume_id=resume_id,
                        )

    session.rollback.assert_called_once_with()
    session.commit.assert_not_called()
    delete_file.assert_not_called()

    assert_app_exception(
        exc_info.value,
        expected_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        expected_code="resume_deletion_failed",
        expected_message="The resume could not be deleted.",
    )


def test_delete_resume_skips_unmanaged_storage_path() -> None:
    session = MagicMock(spec=Session)
    settings = MagicMock()
    resume = MagicMock(spec=Resume)
    resume_id = uuid4()

    resume.storage_path = (
        "external-storage/resumes/resume.pdf"
    )

    with patch(
        "app.services.resume_service.get_settings",
        return_value=settings,
    ):
        with patch(
            "app.services.resume_service.get_resume_by_id_record",
            return_value=resume,
        ):
            with patch(
                "app.services.resume_service.delete_resume_record",
            ):
                with patch(
                    "app.services.resume_service.delete_resume_file",
                    side_effect=ResumeStorageError(
                        "The storage path is outside the "
                        "configured storage directory."
                    ),
                ) as delete_file:
                    result = delete_resume(
                        session=session,
                        resume_id=resume_id,
                    )

    session.commit.assert_called_once_with()
    session.rollback.assert_not_called()

    delete_file.assert_called_once_with(
        storage_path=resume.storage_path,
        settings=settings,
    )

    assert result is None


def test_delete_resume_reports_file_cleanup_failure() -> None:
    session = MagicMock(spec=Session)
    settings = MagicMock()
    resume = MagicMock(spec=Resume)
    resume_id = uuid4()

    resume.storage_path = (
        "local_storage/resumes/stored-resume.pdf"
    )

    with patch(
        "app.services.resume_service.get_settings",
        return_value=settings,
    ):
        with patch(
            "app.services.resume_service.get_resume_by_id_record",
            return_value=resume,
        ):
            with patch(
                "app.services.resume_service.delete_resume_record",
            ):
                with patch(
                    "app.services.resume_service.delete_resume_file",
                    side_effect=OSError(
                        "file is locked"
                    ),
                ):
                    with pytest.raises(AppException) as exc_info:
                        delete_resume(
                            session=session,
                            resume_id=resume_id,
                        )

    session.commit.assert_called_once_with()
    session.rollback.assert_not_called()

    assert_app_exception(
        exc_info.value,
        expected_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        expected_code="resume_file_cleanup_failed",
        expected_message=(
            "The resume metadata was deleted, but its "
            "stored file could not be removed."
        ),
    )


def test_upload_resume_stores_file_creates_record_and_commits() -> None:
    session = MagicMock(spec=Session)
    settings = MagicMock()
    candidate = MagicMock(spec=Candidate)
    resume = MagicMock(spec=Resume)
    candidate_id = uuid4()
    uploaded_file = build_uploaded_file()

    stored_file = StoredResumeFile(
        original_filename="Harsha_Resume.pdf",
        stored_filename="stored-resume.pdf",
        storage_path="local_storage/resumes/stored-resume.pdf",
        content_type="application/pdf",
        file_size_bytes=245760,
    )

    with patch(
        "app.services.resume_service.get_settings",
        return_value=settings,
    ):
        with patch(
            "app.services.resume_service.get_candidate_by_id_record",
            return_value=candidate,
        ) as get_candidate:
            with patch(
                "app.services.resume_service.store_resume_file",
                return_value=stored_file,
            ) as store_file:
                with patch(
                    "app.services.resume_service."
                    "get_primary_resume_record",
                ) as get_primary:
                    with patch(
                        "app.services.resume_service."
                        "create_resume_record",
                        return_value=resume,
                    ) as create_record:
                        result = upload_resume(
                            session=session,
                            candidate_id=candidate_id,
                            uploaded_file=uploaded_file,
                        )

    get_candidate.assert_called_once_with(
        session,
        candidate_id,
    )

    store_file.assert_called_once_with(
        file=uploaded_file.file,
        original_filename=uploaded_file.filename,
        content_type=uploaded_file.content_type,
        settings=settings,
    )

    get_primary.assert_not_called()
    create_record.assert_called_once()

    create_args = create_record.call_args.args

    assert create_args[0] is session

    created_payload = create_args[1]

    assert created_payload.candidate_id == candidate_id
    assert (
        created_payload.original_filename
        == "Harsha_Resume.pdf"
    )
    assert created_payload.stored_filename == "stored-resume.pdf"
    assert (
        created_payload.storage_path
        == "local_storage/resumes/stored-resume.pdf"
    )
    assert created_payload.content_type == "application/pdf"
    assert created_payload.file_size_bytes == 245760
    assert created_payload.is_primary is False

    session.commit.assert_called_once_with()
    session.refresh.assert_called_once_with(resume)
    session.rollback.assert_not_called()

    assert result is resume


def test_upload_resume_raises_when_candidate_does_not_exist() -> None:
    session = MagicMock(spec=Session)
    settings = MagicMock()
    candidate_id = uuid4()
    uploaded_file = build_uploaded_file()

    with patch(
        "app.services.resume_service.get_settings",
        return_value=settings,
    ):
        with patch(
            "app.services.resume_service.get_candidate_by_id_record",
            return_value=None,
        ) as get_candidate:
            with patch(
                "app.services.resume_service.store_resume_file",
            ) as store_file:
                with patch(
                    "app.services.resume_service.create_resume_record",
                ) as create_record:
                    with pytest.raises(AppException) as exc_info:
                        upload_resume(
                            session=session,
                            candidate_id=candidate_id,
                            uploaded_file=uploaded_file,
                        )

    get_candidate.assert_called_once_with(
        session,
        candidate_id,
    )
    store_file.assert_not_called()
    create_record.assert_not_called()

    session.commit.assert_not_called()
    session.refresh.assert_not_called()
    session.rollback.assert_not_called()

    assert_app_exception(
        exc_info.value,
        expected_status=status.HTTP_404_NOT_FOUND,
        expected_code="candidate_not_found",
        expected_message="The requested candidate does not exist.",
    )


def test_upload_primary_resume_demotes_existing_primary() -> None:
    session = MagicMock(spec=Session)
    settings = MagicMock()
    candidate = MagicMock(spec=Candidate)
    existing_primary = MagicMock(spec=Resume)
    new_resume = MagicMock(spec=Resume)
    candidate_id = uuid4()
    uploaded_file = build_uploaded_file()

    stored_file = StoredResumeFile(
        original_filename="Harsha_Resume.pdf",
        stored_filename="stored-primary.pdf",
        storage_path="local_storage/resumes/stored-primary.pdf",
        content_type="application/pdf",
        file_size_bytes=245760,
    )

    with patch(
        "app.services.resume_service.get_settings",
        return_value=settings,
    ):
        with patch(
            "app.services.resume_service.get_candidate_by_id_record",
            return_value=candidate,
        ):
            with patch(
                "app.services.resume_service.store_resume_file",
                return_value=stored_file,
            ):
                with patch(
                    "app.services.resume_service."
                    "get_primary_resume_record",
                    return_value=existing_primary,
                ) as get_primary:
                    with patch(
                        "app.services.resume_service."
                        "update_resume_record",
                        return_value=existing_primary,
                    ) as update_record:
                        with patch(
                            "app.services.resume_service."
                            "create_resume_record",
                            return_value=new_resume,
                        ) as create_record:
                            result = upload_resume(
                                session=session,
                                candidate_id=candidate_id,
                                uploaded_file=uploaded_file,
                                is_primary=True,
                            )

    get_primary.assert_called_once_with(
        session,
        candidate_id,
    )

    update_record.assert_called_once()

    update_args, update_kwargs = update_record.call_args

    assert update_args == (session,)
    assert update_kwargs["resume"] is existing_primary
    assert update_kwargs["payload"].is_primary is False

    create_record.assert_called_once()
    created_payload = create_record.call_args.args[1]

    assert created_payload.is_primary is True

    session.commit.assert_called_once_with()
    session.refresh.assert_called_once_with(new_resume)
    session.rollback.assert_not_called()

    assert result is new_resume


def test_upload_resume_maps_invalid_file_error() -> None:
    session = MagicMock(spec=Session)
    settings = MagicMock()
    candidate = MagicMock(spec=Candidate)
    candidate_id = uuid4()
    uploaded_file = build_uploaded_file()

    with patch(
        "app.services.resume_service.get_settings",
        return_value=settings,
    ):
        with patch(
            "app.services.resume_service.get_candidate_by_id_record",
            return_value=candidate,
        ):
            with patch(
                "app.services.resume_service.store_resume_file",
                side_effect=InvalidResumeFileError(
                    "Only PDF and DOCX Resume files are allowed."
                ),
            ):
                with pytest.raises(AppException) as exc_info:
                    upload_resume(
                        session=session,
                        candidate_id=candidate_id,
                        uploaded_file=uploaded_file,
                    )

    session.rollback.assert_called_once_with()
    session.commit.assert_not_called()
    session.refresh.assert_not_called()

    assert_app_exception(
        exc_info.value,
        expected_status=status.HTTP_400_BAD_REQUEST,
        expected_code="invalid_resume_file",
        expected_message=(
            "Only PDF and DOCX Resume files are allowed."
        ),
    )


def test_upload_resume_maps_file_too_large_error() -> None:
    session = MagicMock(spec=Session)
    settings = MagicMock()
    candidate = MagicMock(spec=Candidate)
    candidate_id = uuid4()
    uploaded_file = build_uploaded_file()

    with patch(
        "app.services.resume_service.get_settings",
        return_value=settings,
    ):
        with patch(
            "app.services.resume_service.get_candidate_by_id_record",
            return_value=candidate,
        ):
            with patch(
                "app.services.resume_service.store_resume_file",
                side_effect=ResumeFileTooLargeError(
                    "File too large."
                ),
            ):
                with pytest.raises(AppException) as exc_info:
                    upload_resume(
                        session=session,
                        candidate_id=candidate_id,
                        uploaded_file=uploaded_file,
                    )

    session.rollback.assert_called_once_with()
    session.commit.assert_not_called()
    session.refresh.assert_not_called()

    assert_app_exception(
        exc_info.value,
        expected_status=status.HTTP_413_CONTENT_TOO_LARGE,
        expected_code="resume_file_too_large",
        expected_message=(
            "The Resume file exceeds the maximum allowed size."
        ),
    )


def test_upload_resume_maps_storage_error() -> None:
    session = MagicMock(spec=Session)
    settings = MagicMock()
    candidate = MagicMock(spec=Candidate)
    candidate_id = uuid4()
    uploaded_file = build_uploaded_file()

    with patch(
        "app.services.resume_service.get_settings",
        return_value=settings,
    ):
        with patch(
            "app.services.resume_service.get_candidate_by_id_record",
            return_value=candidate,
        ):
            with patch(
                "app.services.resume_service.store_resume_file",
                side_effect=ResumeStorageError(
                    "Storage failure."
                ),
            ):
                with pytest.raises(AppException) as exc_info:
                    upload_resume(
                        session=session,
                        candidate_id=candidate_id,
                        uploaded_file=uploaded_file,
                    )

    session.rollback.assert_called_once_with()
    session.commit.assert_not_called()
    session.refresh.assert_not_called()

    assert_app_exception(
        exc_info.value,
        expected_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        expected_code="resume_storage_failed",
        expected_message="The Resume file could not be stored.",
    )


def test_upload_resume_removes_file_after_database_error() -> None:
    session = MagicMock(spec=Session)
    settings = MagicMock()
    candidate = MagicMock(spec=Candidate)
    candidate_id = uuid4()
    uploaded_file = build_uploaded_file()

    stored_file = StoredResumeFile(
        original_filename="Harsha_Resume.pdf",
        stored_filename="orphan-resume.pdf",
        storage_path="local_storage/resumes/orphan-resume.pdf",
        content_type="application/pdf",
        file_size_bytes=245760,
    )

    with patch(
        "app.services.resume_service.get_settings",
        return_value=settings,
    ):
        with patch(
            "app.services.resume_service.get_candidate_by_id_record",
            return_value=candidate,
        ):
            with patch(
                "app.services.resume_service.store_resume_file",
                return_value=stored_file,
            ):
                with patch(
                    "app.services.resume_service.create_resume_record",
                    side_effect=SQLAlchemyError(
                        "database failure"
                    ),
                ):
                    with patch(
                        "app.services.resume_service.delete_resume_file",
                    ) as delete_file:
                        with pytest.raises(AppException) as exc_info:
                            upload_resume(
                                session=session,
                                candidate_id=candidate_id,
                                uploaded_file=uploaded_file,
                            )

    session.rollback.assert_called_once_with()
    session.commit.assert_not_called()
    session.refresh.assert_not_called()

    delete_file.assert_called_once_with(
        storage_path=stored_file.storage_path,
        settings=settings,
    )

    assert_app_exception(
        exc_info.value,
        expected_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        expected_code="resume_upload_failed",
        expected_message="The Resume could not be uploaded.",
    )