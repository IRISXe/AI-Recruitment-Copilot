from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.resume_content import ResumeContent
from app.repositories.candidate_repository import create_candidate
from app.repositories.resume_content_repository import (
    create_resume_content,
    get_resume_content_by_resume_id,
    update_resume_content,
)
from app.repositories.resume_repository import create_resume
from app.schemas.candidate import CandidateCreate
from app.schemas.resume import ResumeCreate


def build_candidate_payload() -> CandidateCreate:
    return CandidateCreate(
        full_name="Harsha Vardhan",
        email="harsha@example.com",
        phone="+91 9876543210",
        current_location="Hyderabad",
        current_role="Backend Developer",
        total_experience_months=18,
        skills=[
            "Python",
            "FastAPI",
            "PostgreSQL",
        ],
    )


def build_resume_payload(
    candidate_id: UUID,
) -> ResumeCreate:
    return ResumeCreate(
        candidate_id=candidate_id,
        original_filename="Harsha_Resume.pdf",
        stored_filename="harsha-resume.pdf",
        storage_path="uploads/resumes/harsha-resume.pdf",
        content_type="application/pdf",
        file_size_bytes=245760,
        is_primary=True,
    )


def create_test_resume(
    db_session: Session,
):
    candidate = create_candidate(
        session=db_session,
        payload=build_candidate_payload(),
    )

    return create_resume(
        session=db_session,
        payload=build_resume_payload(
            candidate_id=candidate.id,
        ),
    )


def test_create_resume_content_adds_pending_record(
    db_session: Session,
) -> None:
    resume = create_test_resume(
        db_session,
    )

    resume_content = create_resume_content(
        session=db_session,
        resume_id=resume.id,
    )

    persisted_content = db_session.get(
        ResumeContent,
        resume_content.id,
    )

    assert resume_content.id is not None
    assert persisted_content is not None
    assert persisted_content.resume_id == resume.id
    assert persisted_content.extraction_status == "pending"
    assert persisted_content.extracted_text is None
    assert persisted_content.extraction_error is None
    assert persisted_content.extractor_version is None
    assert persisted_content.extracted_at is None


def test_get_resume_content_by_resume_id_returns_content_or_none(
    db_session: Session,
) -> None:
    resume = create_test_resume(
        db_session,
    )

    created_content = create_resume_content(
        session=db_session,
        resume_id=resume.id,
    )

    existing_content = get_resume_content_by_resume_id(
        session=db_session,
        resume_id=resume.id,
    )

    missing_content = get_resume_content_by_resume_id(
        session=db_session,
        resume_id=UUID(
            "00000000-0000-0000-0000-000000000001"
        ),
    )

    assert existing_content is not None
    assert existing_content.id == created_content.id
    assert existing_content.resume_id == resume.id
    assert missing_content is None


def test_update_resume_content_marks_extraction_completed(
    db_session: Session,
) -> None:
    resume = create_test_resume(
        db_session,
    )

    resume_content = create_resume_content(
        session=db_session,
        resume_id=resume.id,
    )

    extracted_at = datetime.now(UTC)

    updated_content = update_resume_content(
        session=db_session,
        resume_content=resume_content,
        extracted_text=(
            "Backend Developer\n"
            "Python FastAPI PostgreSQL"
        ),
        extraction_status="completed",
        extraction_error=None,
        extractor_version="1.0.0",
        extracted_at=extracted_at,
    )

    assert updated_content is resume_content
    assert updated_content.extraction_status == "completed"
    assert updated_content.extracted_text == (
        "Backend Developer\n"
        "Python FastAPI PostgreSQL"
    )
    assert updated_content.extraction_error is None
    assert updated_content.extractor_version == "1.0.0"
    assert updated_content.extracted_at == extracted_at

    db_session.expire_all()

    persisted_content = get_resume_content_by_resume_id(
        session=db_session,
        resume_id=resume.id,
    )

    assert persisted_content is not None
    assert persisted_content.extraction_status == "completed"
    assert persisted_content.extracted_text == (
        "Backend Developer\n"
        "Python FastAPI PostgreSQL"
    )


def test_update_resume_content_marks_extraction_failed(
    db_session: Session,
) -> None:
    resume = create_test_resume(
        db_session,
    )

    resume_content = create_resume_content(
        session=db_session,
        resume_id=resume.id,
    )

    extracted_at = datetime.now(UTC)

    updated_content = update_resume_content(
        session=db_session,
        resume_content=resume_content,
        extracted_text=None,
        extraction_status="failed",
        extraction_error="The PDF Resume could not be read.",
        extractor_version="1.0.0",
        extracted_at=extracted_at,
    )

    assert updated_content.extraction_status == "failed"
    assert updated_content.extracted_text is None
    assert (
        updated_content.extraction_error
        == "The PDF Resume could not be read."
    )
    assert updated_content.extractor_version == "1.0.0"
    assert updated_content.extracted_at == extracted_at