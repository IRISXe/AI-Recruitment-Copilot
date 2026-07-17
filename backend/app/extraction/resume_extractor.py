from pathlib import Path
from typing import Final

from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph
from pypdf import PdfReader


PDF_CONTENT_TYPE: Final = "application/pdf"

DOCX_CONTENT_TYPE: Final = (
    "application/vnd.openxmlformats-officedocument."
    "wordprocessingml.document"
)

SUPPORTED_RESUME_CONTENT_TYPES: Final = frozenset(
    {
        PDF_CONTENT_TYPE,
        DOCX_CONTENT_TYPE,
    }
)

EXTRACTOR_VERSION: Final = "1.0.0"


class ResumeExtractionError(Exception):
    """Base exception for Resume text extraction failures."""


class UnsupportedResumeContentTypeError(
    ResumeExtractionError
):
    """Raised when a Resume content type is unsupported."""


class ResumeDocumentReadError(ResumeExtractionError):
    """Raised when a Resume document cannot be read."""


class EmptyResumeTextError(ResumeExtractionError):
    """Raised when a Resume contains no extractable text."""


def extract_resume_text(
    *,
    file_path: Path,
    content_type: str,
) -> str:
    """Extract and normalize text from a PDF or DOCX Resume."""

    if content_type == PDF_CONTENT_TYPE:
        extracted_text = _extract_pdf_text(
            file_path=file_path,
        )

    elif content_type == DOCX_CONTENT_TYPE:
        extracted_text = _extract_docx_text(
            file_path=file_path,
        )

    else:
        raise UnsupportedResumeContentTypeError(
            "The Resume content type is not supported."
        )

    normalized_text = _normalize_text(
        extracted_text,
    )

    if not normalized_text:
        raise EmptyResumeTextError(
            "The Resume does not contain extractable text."
        )

    return normalized_text


def _extract_pdf_text(
    *,
    file_path: Path,
) -> str:
    try:
        reader = PdfReader(
            file_path,
        )

        if reader.is_encrypted:
            raise ResumeDocumentReadError(
                "Encrypted PDF Resume files are not supported."
            )

        page_texts: list[str] = []

        for page in reader.pages:
            page_text = page.extract_text()

            if page_text:
                page_texts.append(
                    page_text,
                )

        return "\n\n".join(
            page_texts,
        )

    except ResumeDocumentReadError:
        raise

    except Exception as exc:
        raise ResumeDocumentReadError(
            "The PDF Resume could not be read."
        ) from exc


def _extract_docx_text(
    *,
    file_path: Path,
) -> str:
    try:
        document = Document(
            file_path,
        )

        document_parts: list[str] = []

        for block in document.iter_inner_content():
            if isinstance(block, Paragraph):
                document_parts.append(
                    block.text,
                )

            elif isinstance(block, Table):
                table_text = _extract_table_text(
                    table=block,
                )

                if table_text:
                    document_parts.append(
                        table_text,
                    )

        return "\n\n".join(
            document_parts,
        )

    except Exception as exc:
        raise ResumeDocumentReadError(
            "The DOCX Resume could not be read."
        ) from exc


def _extract_table_text(
    *,
    table: Table,
) -> str:
    row_texts: list[str] = []

    for row in table.rows:
        cell_texts = [
            _normalize_line(
                cell.text,
            )
            for cell in row.cells
        ]

        non_empty_cells = [
            cell_text
            for cell_text in cell_texts
            if cell_text
        ]

        if non_empty_cells:
            row_texts.append(
                " | ".join(
                    non_empty_cells,
                )
            )

    return "\n".join(
        row_texts,
    )


def _normalize_text(
    text: str,
) -> str:
    normalized_newlines = (
        text.replace(
            "\r\n",
            "\n",
        ).replace(
            "\r",
            "\n",
        )
    )

    normalized_lines = [
        _normalize_line(line)
        for line in normalized_newlines.split("\n")
    ]

    non_empty_lines = [
        line
        for line in normalized_lines
        if line
    ]

    return "\n".join(
        non_empty_lines,
    ).strip()


def _normalize_line(
    line: str,
) -> str:
    return " ".join(
        line.split(),
    )