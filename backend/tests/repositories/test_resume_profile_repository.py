from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models.candidate import Candidate
from app.models.resume import Resume
from app.repositories.resume_profile_repository import (
    create_resume_profile,
    get_resume_profile_by_resume_id,
    update_resume_profile,
)


def persist_resume(
    db_session: Session,
) -> Resume:
    candidate = Candidate(
        full_name="Resume Profile Candidate",
        email=f"resume-profile-{uuid4()}@example.com",
        phone="+91 9876543210",
        current_location="Hyderabad",
        current_role="Backend Developer",
        total_experience_months=18,
        skills=["Python", "FastAPI"],
    )

    db_session.add(candidate)
    db_session.flush()

    resume_id = uuid4()

    resume = Resume(
        id=resume_id,
        candidate_id=candidate.id,
        original_filename="candidate-resume.pdf",
        stored_filename=f"{resume_id}.pdf",
        storage_path=f"uploads/resumes/{resume_id}.pdf",
        content_type="application/pdf",
        file_size_bytes=1024,
        is_primary=True,
    )

    db_session.add(resume)
    db_session.flush()

    return resume


def test_create_resume_profile_adds_pending_profile(
    db_session: Session,
) -> None:
    resume = persist_resume(db_session)

    resume_profile = create_resume_profile(
        db_session,
        resume_id=resume.id,
    )

    assert resume_profile.id is not None
    assert resume_profile.resume_id == resume.id
    assert resume_profile.profile_data is None
    assert resume_profile.parsing_status == "pending"
    assert resume_profile.parsing_error is None
    assert resume_profile.parser_version is None
    assert resume_profile.source_text_sha256 is None
    assert resume_profile.parsed_at is None


def test_get_resume_profile_by_resume_id_returns_profile_or_none(
    db_session: Session,
) -> None:
    resume = persist_resume(db_session)

    created_profile = create_resume_profile(
        db_session,
        resume_id=resume.id,
    )

    existing_profile = get_resume_profile_by_resume_id(
        db_session,
        resume_id=resume.id,
    )
    missing_profile = get_resume_profile_by_resume_id(
        db_session,
        resume_id=uuid4(),
    )

    assert existing_profile is created_profile
    assert missing_profile is None


def test_update_resume_profile_changes_parsing_result(
    db_session: Session,
) -> None:
    resume = persist_resume(db_session)

    resume_profile = create_resume_profile(
        db_session,
        resume_id=resume.id,
    )

    parsed_at = datetime.now(UTC)

    profile_data: dict[str, object] = {
        "full_name": "Harsha Vardhan",
        "email": "harsha@example.com",
        "phone": "+91 9876543210",
        "location": "Hyderabad",
        "current_role": "Backend Developer",
        "professional_summary": "Backend developer.",
        "total_experience_months": 18,
        "skills": ["Python", "FastAPI"],
        "education": [],
        "work_experience": [],
        "projects": [],
        "certifications": [],
        "languages": ["English"],
    }

    updated_profile = update_resume_profile(
        db_session,
        resume_profile=resume_profile,
        profile_data=profile_data,
        parsing_status="completed",
        parsing_error=None,
        parser_version="rule-based-v1",
        source_text_sha256="a" * 64,
        parsed_at=parsed_at,
    )

    assert updated_profile is resume_profile
    assert updated_profile.profile_data == profile_data
    assert updated_profile.parsing_status == "completed"
    assert updated_profile.parsing_error is None
    assert updated_profile.parser_version == "rule-based-v1"
    assert updated_profile.source_text_sha256 == "a" * 64
    assert updated_profile.parsed_at == parsed_at