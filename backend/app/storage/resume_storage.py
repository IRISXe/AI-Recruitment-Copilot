from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import BinaryIO
from uuid import uuid4
from zipfile import BadZipFile, ZipFile, is_zipfile

from app.core.config import Settings


CONTENT_TYPE_BY_EXTENSION = {
    ".pdf": "application/pdf",
    ".docx": (
        "application/vnd.openxmlformats-officedocument."
        "wordprocessingml.document"
    ),
}

READ_CHUNK_SIZE_BYTES = 64 * 1024


class ResumeStorageError(Exception):
    """Base exception for local Resume storage operations."""


class InvalidResumeFileError(ResumeStorageError):
    """Raised when the uploaded file fails validation."""


class ResumeFileTooLargeError(ResumeStorageError):
    """Raised when the uploaded file exceeds the configured limit."""


@dataclass(frozen=True)
class StoredResumeFile:
    original_filename: str
    stored_filename: str
    storage_path: str
    content_type: str
    file_size_bytes: int


def store_resume_file(
    *,
    file: BinaryIO,
    original_filename: str | None,
    content_type: str | None,
    settings: Settings,
) -> StoredResumeFile:
    validated_filename = _validate_filename(
        original_filename,
    )

    extension = Path(validated_filename).suffix.lower()

    normalized_content_type = _validate_file_type(
        extension=extension,
        content_type=content_type,
        settings=settings,
    )

    stored_filename = f"{uuid4()}{extension}"

    storage_directory = settings.resume_storage_directory
    storage_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    destination = storage_directory / stored_filename
    file_size_bytes = 0

    try:
        file.seek(0)

        with destination.open("xb") as destination_file:
            while True:
                chunk = file.read(READ_CHUNK_SIZE_BYTES)

                if not chunk:
                    break

                file_size_bytes += len(chunk)

                if (
                    file_size_bytes
                    > settings.resume_max_file_size_bytes
                ):
                    raise ResumeFileTooLargeError(
                        "The Resume file exceeds the maximum "
                        "allowed size."
                    )

                destination_file.write(chunk)

        if file_size_bytes == 0:
            raise InvalidResumeFileError(
                "The Resume file cannot be empty."
            )

        _validate_file_contents(
            destination=destination,
            extension=extension,
        )

    except Exception:
        destination.unlink(
            missing_ok=True,
        )
        raise

    finally:
        file.seek(0)

    return StoredResumeFile(
        original_filename=validated_filename,
        stored_filename=stored_filename,
        storage_path=destination.as_posix(),
        content_type=normalized_content_type,
        file_size_bytes=file_size_bytes,
    )


def delete_resume_file(
    *,
    storage_path: str,
    settings: Settings,
) -> None:
    storage_root = (
        settings.resume_storage_directory
        .resolve()
    )
    target_path = Path(storage_path).resolve()

    if not target_path.is_relative_to(storage_root):
        raise ResumeStorageError(
            "The Resume file is outside the configured "
            "storage directory."
        )

    target_path.unlink(
        missing_ok=True,
    )


def _validate_filename(
    original_filename: str | None,
) -> str:
    if original_filename is None:
        raise InvalidResumeFileError(
            "The Resume filename is required."
        )

    normalized_filename = (
        original_filename
        .strip()
        .replace("\\", "/")
    )

    if not normalized_filename:
        raise InvalidResumeFileError(
            "The Resume filename is required."
        )

    filename = PurePosixPath(
        normalized_filename,
    ).name

    if filename != normalized_filename:
        raise InvalidResumeFileError(
            "The Resume filename must not contain "
            "directory components."
        )

    if filename in {".", ".."}:
        raise InvalidResumeFileError(
            "The Resume filename is invalid."
        )

    return filename


def _validate_file_type(
    *,
    extension: str,
    content_type: str | None,
    settings: Settings,
) -> str:
    if extension not in settings.resume_allowed_extension_set:
        raise InvalidResumeFileError(
            "Only PDF and DOCX Resume files are allowed."
        )

    normalized_content_type = (
        content_type
        .split(";", maxsplit=1)[0]
        .strip()
        .lower()
        if content_type
        else ""
    )

    if (
        normalized_content_type
        not in settings.resume_allowed_content_type_set
    ):
        raise InvalidResumeFileError(
            "The Resume file content type is not allowed."
        )

    expected_content_type = CONTENT_TYPE_BY_EXTENSION.get(
        extension,
    )

    if normalized_content_type != expected_content_type:
        raise InvalidResumeFileError(
            "The Resume extension does not match its "
            "content type."
        )

    return normalized_content_type


def _validate_file_contents(
    *,
    destination: Path,
    extension: str,
) -> None:
    if extension == ".pdf":
        with destination.open("rb") as stored_file:
            signature = stored_file.read(5)

        if signature != b"%PDF-":
            raise InvalidResumeFileError(
                "The uploaded file is not a valid PDF."
            )

        return

    if extension == ".docx":
        _validate_docx_contents(destination)
        return

    raise InvalidResumeFileError(
        "The Resume file type is unsupported."
    )


def _validate_docx_contents(
    destination: Path,
) -> None:
    if not is_zipfile(destination):
        raise InvalidResumeFileError(
            "The uploaded file is not a valid DOCX document."
        )

    required_entries = {
        "[Content_Types].xml",
        "word/document.xml",
    }

    try:
        with ZipFile(destination) as document:
            document_entries = set(
                document.namelist()
            )

    except BadZipFile as exc:
        raise InvalidResumeFileError(
            "The uploaded file is not a valid DOCX document."
        ) from exc

    if not required_entries.issubset(document_entries):
        raise InvalidResumeFileError(
            "The uploaded file is not a valid DOCX document."
        )