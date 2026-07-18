from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.resume_content import (
    ResumeContentResponse,
    ResumeExtractionStatus,
)


@pytest.mark.parametrize(
    "status",
    [
        "pending",
        "completed",
        "failed",
    ],
)
def test_resume_content_response_accepts_supported_statuses(
    status: ResumeExtractionStatus,
) -> None:
    now = datetime.now(UTC)

    response = ResumeContentResponse(
        id=uuid4(),
        resume_id=uuid4(),
        extracted_text=None,
        extraction_status=status,
        extraction_error=None,
        extractor_version=None,
        extracted_at=None,
        created_at=now,
        updated_at=now,
    )

    assert response.extraction_status == status


def test_resume_content_response_rejects_unsupported_status() -> None:
    now = datetime.now(UTC)

    with pytest.raises(ValidationError):
        ResumeContentResponse(
            id=uuid4(),
            resume_id=uuid4(),
            extracted_text=None,
            extraction_status="processing",
            extraction_error=None,
            extractor_version=None,
            extracted_at=None,
            created_at=now,
            updated_at=now,
        )


def test_resume_content_response_serializes_attribute_object() -> None:
    content_id = uuid4()
    resume_id = uuid4()
    now = datetime.now(UTC)

    orm_like_content = SimpleNamespace(
        id=content_id,
        resume_id=resume_id,
        extracted_text=(
            "Python Developer\n"
            "FastAPI and PostgreSQL"
        ),
        extraction_status="completed",
        extraction_error=None,
        extractor_version="1.0.0",
        extracted_at=now,
        created_at=now,
        updated_at=now,
    )

    response = ResumeContentResponse.model_validate(
        orm_like_content
    )

    assert response.id == content_id
    assert response.resume_id == resume_id
    assert response.extracted_text == (
        "Python Developer\n"
        "FastAPI and PostgreSQL"
    )
    assert response.extraction_status == "completed"
    assert response.extractor_version == "1.0.0"
    assert response.extracted_at == now


def test_resume_content_response_strips_surrounding_whitespace() -> None:
    now = datetime.now(UTC)

    response = ResumeContentResponse(
        id=uuid4(),
        resume_id=uuid4(),
        extracted_text="  Backend Engineer  ",
        extraction_status="failed",
        extraction_error="  Unable to read document  ",
        extractor_version="  1.0.0  ",
        extracted_at=now,
        created_at=now,
        updated_at=now,
    )

    assert response.extracted_text == "Backend Engineer"
    assert response.extraction_error == "Unable to read document"
    assert response.extractor_version == "1.0.0"