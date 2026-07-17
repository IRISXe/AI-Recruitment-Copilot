from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.models.resume import Resume
from app.repositories.candidate_repository import create_candidate
from app.repositories.resume_repository import (
    create_resume,
    delete_resume,
    get_primary_resume_by_candidate_id,
    get_resume_by_id,
    list_resumes,
    update_resume,
)
from app.schemas.candidate import CandidateCreate
from app.schemas.resume import ResumeCreate, ResumeUpdate


def build_candidate_payload(
    *,
    full_name: str = "Harsha Vardhan",
    email: str = "harsha@example.com",
) -> CandidateCreate:
    return CandidateCreate(
        full_name=full_name,
        email=email,
        phone="+91 9876543210",
        current_location="Hyderabad",
        current_role="Backend Developer",
        total_experience_months=18,
        skills=["Python", "FastAPI", "PostgreSQL"],
    )


def build_resume_payload(
    candidate_id: UUID,
    *,
    original_filename: str = "Harsha_Resume.pdf",
    stored_filename: str = "harsha-resume.pdf",
    is_primary: bool = False,
) -> ResumeCreate:
    return ResumeCreate(
        candidate_id=candidate_id,
        original_filename=original_filename,
        stored_filename=stored_filename,
        storage_path=f"uploads/resumes/{stored_filename}",
        content_type="application/pdf",
        file_size_bytes=245760,
        is_primary=is_primary,
    )


def test_create_resume_adds_resume_to_database_session(
    db_session: Session,
) -> None:
    candidate = create_candidate(
        session=db_session,
        payload=build_candidate_payload(),
    )

    resume = create_resume(
        session=db_session,
        payload=build_resume_payload(
            candidate_id=candidate.id,
        ),
    )

    persisted_resume = db_session.get(
        Resume,
        resume.id,
    )

    assert resume.id is not None
    assert persisted_resume is not None
    assert persisted_resume.id == resume.id
    assert persisted_resume.candidate_id == candidate.id
    assert persisted_resume.original_filename == "Harsha_Resume.pdf"
    assert persisted_resume.stored_filename == "harsha-resume.pdf"
    assert (
        persisted_resume.storage_path
        == "uploads/resumes/harsha-resume.pdf"
    )
    assert persisted_resume.content_type == "application/pdf"
    assert persisted_resume.file_size_bytes == 245760
    assert persisted_resume.is_primary is False


def test_get_resume_by_id_returns_resume_or_none(
    db_session: Session,
) -> None:
    candidate = create_candidate(
        session=db_session,
        payload=build_candidate_payload(),
    )
    created_resume = create_resume(
        session=db_session,
        payload=build_resume_payload(
            candidate_id=candidate.id,
        ),
    )

    existing_resume = get_resume_by_id(
        session=db_session,
        resume_id=created_resume.id,
    )
    missing_resume = get_resume_by_id(
        session=db_session,
        resume_id=uuid4(),
    )

    assert existing_resume is not None
    assert existing_resume.id == created_resume.id
    assert existing_resume.candidate_id == candidate.id
    assert missing_resume is None


def test_list_resumes_supports_pagination_and_candidate_filtering(
    db_session: Session,
) -> None:
    first_candidate = create_candidate(
        session=db_session,
        payload=build_candidate_payload(),
    )
    second_candidate = create_candidate(
        session=db_session,
        payload=build_candidate_payload(
            full_name="Second Candidate",
            email="second@example.com",
        ),
    )

    first_resume = create_resume(
        session=db_session,
        payload=build_resume_payload(
            candidate_id=first_candidate.id,
            stored_filename="first-resume.pdf",
        ),
    )
    second_resume = create_resume(
        session=db_session,
        payload=build_resume_payload(
            candidate_id=first_candidate.id,
            stored_filename="second-resume.pdf",
        ),
    )
    third_resume = create_resume(
        session=db_session,
        payload=build_resume_payload(
            candidate_id=second_candidate.id,
            stored_filename="third-resume.pdf",
        ),
    )

    first_resume.created_at = datetime(
        9999,
        1,
        1,
        tzinfo=UTC,
    )
    second_resume.created_at = datetime(
        9999,
        1,
        2,
        tzinfo=UTC,
    )
    third_resume.created_at = datetime(
        9999,
        1,
        3,
        tzinfo=UTC,
    )

    db_session.flush()

    first_page = list_resumes(
        session=db_session,
        offset=0,
        limit=2,
    )
    second_page = list_resumes(
        session=db_session,
        offset=2,
        limit=1,
    )
    candidate_resumes = list_resumes(
        session=db_session,
        offset=0,
        limit=20,
        candidate_id=first_candidate.id,
    )

    assert [resume.id for resume in first_page] == [
        third_resume.id,
        second_resume.id,
    ]
    assert [resume.id for resume in second_page] == [
        first_resume.id,
    ]
    assert [resume.id for resume in candidate_resumes] == [
        second_resume.id,
        first_resume.id,
    ]


def test_get_primary_resume_by_candidate_id_returns_primary_resume(
    db_session: Session,
) -> None:
    candidate = create_candidate(
        session=db_session,
        payload=build_candidate_payload(),
    )

    create_resume(
        session=db_session,
        payload=build_resume_payload(
            candidate_id=candidate.id,
            stored_filename="secondary-resume.pdf",
        ),
    )
    primary_resume = create_resume(
        session=db_session,
        payload=build_resume_payload(
            candidate_id=candidate.id,
            stored_filename="primary-resume.pdf",
            is_primary=True,
        ),
    )

    existing_primary_resume = get_primary_resume_by_candidate_id(
        session=db_session,
        candidate_id=candidate.id,
    )
    missing_primary_resume = get_primary_resume_by_candidate_id(
        session=db_session,
        candidate_id=uuid4(),
    )

    assert existing_primary_resume is not None
    assert existing_primary_resume.id == primary_resume.id
    assert existing_primary_resume.is_primary is True
    assert missing_primary_resume is None


def test_update_resume_changes_only_provided_fields(
    db_session: Session,
) -> None:
    candidate = create_candidate(
        session=db_session,
        payload=build_candidate_payload(),
    )
    resume = create_resume(
        session=db_session,
        payload=build_resume_payload(
            candidate_id=candidate.id,
        ),
    )

    original_id = resume.id
    original_candidate_id = resume.candidate_id
    original_filename = resume.original_filename
    original_stored_filename = resume.stored_filename
    original_storage_path = resume.storage_path
    original_content_type = resume.content_type
    original_file_size = resume.file_size_bytes

    updated_resume = update_resume(
        session=db_session,
        resume=resume,
        payload=ResumeUpdate(
            is_primary=True,
        ),
    )

    assert updated_resume is resume
    assert updated_resume.id == original_id
    assert updated_resume.is_primary is True

    assert updated_resume.candidate_id == original_candidate_id
    assert updated_resume.original_filename == original_filename
    assert updated_resume.stored_filename == original_stored_filename
    assert updated_resume.storage_path == original_storage_path
    assert updated_resume.content_type == original_content_type
    assert updated_resume.file_size_bytes == original_file_size

    db_session.expire_all()

    persisted_resume = get_resume_by_id(
        session=db_session,
        resume_id=original_id,
    )

    assert persisted_resume is not None
    assert persisted_resume.is_primary is True


def test_delete_resume_removes_resume_from_database_session(
    db_session: Session,
) -> None:
    candidate = create_candidate(
        session=db_session,
        payload=build_candidate_payload(),
    )
    resume = create_resume(
        session=db_session,
        payload=build_resume_payload(
            candidate_id=candidate.id,
        ),
    )

    resume_id = resume.id

    delete_result = delete_resume(
        session=db_session,
        resume=resume,
    )

    deleted_resume = get_resume_by_id(
        session=db_session,
        resume_id=resume_id,
    )

    assert delete_result is None
    assert deleted_resume is None