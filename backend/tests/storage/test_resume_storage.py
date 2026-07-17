from io import BytesIO
from pathlib import Path
from zipfile import ZipFile
from unittest.mock import patch
import pytest

from app.core.config import Settings
from app.storage.resume_storage import (
    InvalidResumeFileError,
    ResumeFileNotFoundError,
    ResumeFileTooLargeError,
    ResumeStorageError,
    delete_resume_file,
    get_resume_file_path,
    resolve_resume_file_path,
    store_resume_file,
)


PDF_CONTENT_TYPE = "application/pdf"
DOCX_CONTENT_TYPE = (
    "application/vnd.openxmlformats-officedocument."
    "wordprocessingml.document"
)


def build_settings(
    storage_directory: Path,
    *,
    max_file_size_bytes: int = 5 * 1024 * 1024,
) -> Settings:
    return Settings(
        database_url=(
            "postgresql+psycopg://user:password@localhost/test"
        ),
        resume_storage_directory=storage_directory,
        resume_max_file_size_bytes=max_file_size_bytes,
    )


def build_valid_docx() -> BytesIO:
    document = BytesIO()

    with ZipFile(document, mode="w") as archive:
        archive.writestr(
            "[Content_Types].xml",
            "<Types></Types>",
        )
        archive.writestr(
            "word/document.xml",
            "<document></document>",
        )

    document.seek(0)

    return document


def test_store_resume_file_saves_valid_pdf(
    tmp_path: Path,
) -> None:
    settings = build_settings(
        tmp_path / "resumes",
    )
    file = BytesIO(
        b"%PDF-1.4\nResume PDF content"
    )

    stored_file = store_resume_file(
        file=file,
        original_filename="Harsha_Resume.PDF",
        content_type=PDF_CONTENT_TYPE,
        settings=settings,
    )

    stored_path = Path(stored_file.storage_path)

    assert stored_file.original_filename == "Harsha_Resume.PDF"
    assert stored_file.stored_filename.endswith(".pdf")
    assert stored_file.content_type == PDF_CONTENT_TYPE
    assert stored_file.file_size_bytes == len(
        b"%PDF-1.4\nResume PDF content"
    )

    assert stored_path.exists()
    assert stored_path.parent == settings.resume_storage_directory
    assert stored_path.read_bytes() == (
        b"%PDF-1.4\nResume PDF content"
    )
    assert file.tell() == 0


def test_store_resume_file_saves_valid_docx(
    tmp_path: Path,
) -> None:
    settings = build_settings(
        tmp_path / "resumes",
    )
    file = build_valid_docx()

    stored_file = store_resume_file(
        file=file,
        original_filename="Harsha_Resume.docx",
        content_type=DOCX_CONTENT_TYPE,
        settings=settings,
    )

    stored_path = Path(stored_file.storage_path)

    assert stored_file.stored_filename.endswith(".docx")
    assert stored_file.content_type == DOCX_CONTENT_TYPE
    assert stored_file.file_size_bytes > 0
    assert stored_path.exists()
    assert file.tell() == 0


@pytest.mark.parametrize(
    "filename",
    [
        "../resume.pdf",
        "../../resume.pdf",
        "folder/resume.pdf",
        r"C:\private\resume.pdf",
        "",
        "   ",
    ],
)
def test_store_resume_file_rejects_invalid_filename(
    tmp_path: Path,
    filename: str,
) -> None:
    settings = build_settings(
        tmp_path / "resumes",
    )

    with pytest.raises(
        InvalidResumeFileError,
    ):
        store_resume_file(
            file=BytesIO(b"%PDF-1.4\ncontent"),
            original_filename=filename,
            content_type=PDF_CONTENT_TYPE,
            settings=settings,
        )

    assert not settings.resume_storage_directory.exists()


def test_store_resume_file_rejects_unsupported_extension(
    tmp_path: Path,
) -> None:
    settings = build_settings(
        tmp_path / "resumes",
    )

    with pytest.raises(
        InvalidResumeFileError,
        match="Only PDF and DOCX",
    ):
        store_resume_file(
            file=BytesIO(b"plain text"),
            original_filename="resume.txt",
            content_type="text/plain",
            settings=settings,
        )


def test_store_resume_file_rejects_mismatched_content_type(
    tmp_path: Path,
) -> None:
    settings = build_settings(
        tmp_path / "resumes",
    )

    with pytest.raises(
        InvalidResumeFileError,
        match="extension does not match",
    ):
        store_resume_file(
            file=BytesIO(b"%PDF-1.4\ncontent"),
            original_filename="resume.pdf",
            content_type=DOCX_CONTENT_TYPE,
            settings=settings,
        )


def test_store_resume_file_rejects_oversized_file_and_removes_partial_file(
    tmp_path: Path,
) -> None:
    settings = build_settings(
        tmp_path / "resumes",
        max_file_size_bytes=10,
    )

    with pytest.raises(
        ResumeFileTooLargeError,
    ):
        store_resume_file(
            file=BytesIO(
                b"%PDF-1.4\nThis file is too large."
            ),
            original_filename="resume.pdf",
            content_type=PDF_CONTENT_TYPE,
            settings=settings,
        )

    assert list(
        settings.resume_storage_directory.glob("*")
    ) == []


def test_store_resume_file_rejects_empty_file(
    tmp_path: Path,
) -> None:
    settings = build_settings(
        tmp_path / "resumes",
    )

    with pytest.raises(
        InvalidResumeFileError,
        match="cannot be empty",
    ):
        store_resume_file(
            file=BytesIO(),
            original_filename="resume.pdf",
            content_type=PDF_CONTENT_TYPE,
            settings=settings,
        )

    assert list(
        settings.resume_storage_directory.glob("*")
    ) == []


def test_store_resume_file_rejects_invalid_pdf_contents(
    tmp_path: Path,
) -> None:
    settings = build_settings(
        tmp_path / "resumes",
    )

    with pytest.raises(
        InvalidResumeFileError,
        match="not a valid PDF",
    ):
        store_resume_file(
            file=BytesIO(b"This is not a PDF"),
            original_filename="resume.pdf",
            content_type=PDF_CONTENT_TYPE,
            settings=settings,
        )

    assert list(
        settings.resume_storage_directory.glob("*")
    ) == []


def test_store_resume_file_rejects_invalid_docx_contents(
    tmp_path: Path,
) -> None:
    settings = build_settings(
        tmp_path / "resumes",
    )

    with pytest.raises(
        InvalidResumeFileError,
        match="not a valid DOCX",
    ):
        store_resume_file(
            file=BytesIO(b"This is not a DOCX"),
            original_filename="resume.docx",
            content_type=DOCX_CONTENT_TYPE,
            settings=settings,
        )

    assert list(
        settings.resume_storage_directory.glob("*")
    ) == []


def test_resolve_resume_file_path_returns_safe_resolved_path(
    tmp_path: Path,
) -> None:
    settings = build_settings(
        tmp_path / "resumes",
    )

    settings.resume_storage_directory.mkdir(
        parents=True,
    )

    stored_file = (
        settings.resume_storage_directory
        / "stored-resume.pdf"
    )

    stored_file.write_bytes(
        b"%PDF-1.4\ncontent"
    )

    resolved_path = resolve_resume_file_path(
        storage_path=stored_file.as_posix(),
        settings=settings,
    )

    assert resolved_path == stored_file.resolve()
    assert resolved_path.is_file()

def test_get_resume_file_path_returns_existing_regular_file(
    tmp_path: Path,
) -> None:
    settings = build_settings(
        tmp_path / "resumes",
    )

    settings.resume_storage_directory.mkdir(
        parents=True,
    )

    stored_file = (
        settings.resume_storage_directory
        / "stored-resume.pdf"
    )

    stored_file.write_bytes(
        b"%PDF-1.4\ncontent"
    )

    result = get_resume_file_path(
        storage_path=stored_file.as_posix(),
        settings=settings,
    )

    assert result == stored_file.resolve()
    assert result.is_file()


def test_get_resume_file_path_raises_when_file_is_missing(
    tmp_path: Path,
) -> None:
    settings = build_settings(
        tmp_path / "resumes",
    )

    missing_file = (
        settings.resume_storage_directory
        / "missing-resume.pdf"
    )

    with pytest.raises(
        ResumeFileNotFoundError,
        match="could not be found",
    ):
        get_resume_file_path(
            storage_path=missing_file.as_posix(),
            settings=settings,
        )


def test_get_resume_file_path_rejects_directory(
    tmp_path: Path,
) -> None:
    settings = build_settings(
        tmp_path / "resumes",
    )

    directory_path = (
        settings.resume_storage_directory
        / "not-a-file.pdf"
    )

    directory_path.mkdir(
        parents=True,
    )

    with pytest.raises(
        ResumeStorageError,
        match="not a regular file",
    ):
        get_resume_file_path(
            storage_path=directory_path.as_posix(),
            settings=settings,
        )


def test_get_resume_file_path_maps_filesystem_failure(
    tmp_path: Path,
) -> None:
    settings = build_settings(
        tmp_path / "resumes",
    )

    stored_file = (
        settings.resume_storage_directory
        / "stored-resume.pdf"
    )

    with patch.object(
        Path,
        "stat",
        side_effect=OSError("filesystem failure"),
    ):
        with pytest.raises(
            ResumeStorageError,
            match="could not be accessed",
        ):
            get_resume_file_path(
                storage_path=stored_file.as_posix(),
                settings=settings,
            )

def test_resolve_resume_file_path_rejects_outside_path(
    tmp_path: Path,
) -> None:
    settings = build_settings(
        tmp_path / "resumes",
    )

    outside_file = tmp_path / "private-file.pdf"

    outside_file.write_bytes(
        b"%PDF-1.4\ncontent"
    )

    with pytest.raises(
        ResumeStorageError,
        match=(
            "outside the configured storage directory"
        ),
    ):
        resolve_resume_file_path(
            storage_path=outside_file.as_posix(),
            settings=settings,
        )

    assert outside_file.exists()


def test_delete_resume_file_removes_stored_file(
    tmp_path: Path,
) -> None:
    settings = build_settings(
        tmp_path / "resumes",
    )
    settings.resume_storage_directory.mkdir(
        parents=True,
    )

    stored_file = (
        settings.resume_storage_directory
        / "stored-resume.pdf"
    )
    stored_file.write_bytes(
        b"%PDF-1.4\ncontent"
    )

    delete_resume_file(
        storage_path=stored_file.as_posix(),
        settings=settings,
    )

    assert not stored_file.exists()


def test_delete_resume_file_rejects_path_outside_storage_directory(
    tmp_path: Path,
) -> None:
    settings = build_settings(
        tmp_path / "resumes",
    )

    outside_file = tmp_path / "outside-file.pdf"
    outside_file.write_bytes(
        b"%PDF-1.4\ncontent"
    )

    with pytest.raises(
        ResumeStorageError,
        match="outside the configured storage directory",
    ):
        delete_resume_file(
            storage_path=outside_file.as_posix(),
            settings=settings,
        )

    assert outside_file.exists()
