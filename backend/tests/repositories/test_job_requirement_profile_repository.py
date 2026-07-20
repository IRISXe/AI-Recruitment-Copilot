from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models.job import Job
from app.repositories.job_repository import create_job
from app.repositories.job_requirement_profile_repository import (
    create_job_requirement_profile,
    get_job_requirement_profile_by_job_id,
    update_job_requirement_profile,
)
from app.schemas.job import JobCreate


def persist_job(
    db_session: Session,
) -> Job:
    payload = JobCreate(
        title="Backend Engineer",
        description=(
            "We are looking for a Backend Engineer with "
            "Python, FastAPI, PostgreSQL, and Docker experience."
        ),
        department="Engineering",
        location="Hyderabad",
        employment_type="full_time",
        minimum_experience=2,
        required_skills=[
            "Python",
            "FastAPI",
        ],
        preferred_skills=[
            "PostgreSQL",
            "Docker",
        ],
    )

    return create_job(
        session=db_session,
        payload=payload,
    )


def test_create_job_requirement_profile_adds_pending_profile(
    db_session: Session,
) -> None:
    job = persist_job(db_session)

    profile = create_job_requirement_profile(
        db_session,
        job_id=job.id,
    )

    assert profile.id is not None
    assert profile.job_id == job.id
    assert profile.profile_data is None
    assert profile.parsing_status == "pending"
    assert profile.parsing_error is None
    assert profile.parser_version is None
    assert profile.source_description_sha256 is None
    assert profile.parsed_at is None


def test_get_job_requirement_profile_by_job_id_returns_profile_or_none(
    db_session: Session,
) -> None:
    job = persist_job(db_session)

    created_profile = create_job_requirement_profile(
        db_session,
        job_id=job.id,
    )

    existing_profile = (
        get_job_requirement_profile_by_job_id(
            db_session,
            job_id=job.id,
        )
    )

    missing_profile = (
        get_job_requirement_profile_by_job_id(
            db_session,
            job_id=uuid4(),
        )
    )

    assert existing_profile is created_profile
    assert missing_profile is None


def test_update_job_requirement_profile_changes_parsing_result(
    db_session: Session,
) -> None:
    job = persist_job(db_session)

    profile = create_job_requirement_profile(
        db_session,
        job_id=job.id,
    )

    parsed_at = datetime.now(UTC)

    profile_data: dict[str, object] = {
        "job_title": "Backend Engineer",
        "department": "Engineering",
        "location": "Hyderabad",
        "employment_type": "full_time",
        "work_mode": "hybrid",
        "seniority_level": "mid",
        "summary": "Backend engineering position.",
        "responsibilities": [
            "Develop scalable REST APIs.",
        ],
        "required_skills": [
            "Python",
            "FastAPI",
        ],
        "preferred_skills": [
            "PostgreSQL",
            "Docker",
        ],
        "minimum_experience_years": 2,
        "maximum_experience_years": 4,
        "required_education": [
            "Bachelor's degree in Computer Science",
        ],
        "preferred_education": [],
        "required_certifications": [],
        "preferred_certifications": [],
        "keywords": [
            "Python",
            "FastAPI",
            "Backend",
        ],
        "warnings": [],
        "missing_sections": [],
        "confidence": 0.9,
    }

    updated_profile = update_job_requirement_profile(
        db_session,
        profile=profile,
        profile_data=profile_data,
        parsing_status="completed",
        parsing_error=None,
        parser_version="job-rule-based-v1",
        source_description_sha256="a" * 64,
        parsed_at=parsed_at,
    )

    assert updated_profile is profile
    assert updated_profile.profile_data == profile_data
    assert updated_profile.parsing_status == "completed"
    assert updated_profile.parsing_error is None
    assert updated_profile.parser_version == "job-rule-based-v1"
    assert updated_profile.source_description_sha256 == "a" * 64
    assert updated_profile.parsed_at == parsed_at


def test_deleting_job_cascades_requirement_profile(
    db_session: Session,
) -> None:
    job = persist_job(db_session)

    profile = create_job_requirement_profile(
        db_session,
        job_id=job.id,
    )

    profile_id = profile.id

    db_session.delete(job)
    db_session.flush()
    db_session.expire_all()

    deleted_profile = db_session.get(
        type(profile),
        profile_id,
    )

    assert deleted_profile is None