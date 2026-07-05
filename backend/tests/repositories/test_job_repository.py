from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models.job import Job
from app.repositories.job_repository import (
    create_job,
    delete_job,
    get_job_by_id,
    list_jobs,
    update_job,
)
from app.schemas.job import JobCreate, JobUpdate


def build_job_payload(
    title: str = "Backend Engineer",
) -> JobCreate:
    return JobCreate(
        title=title,
        department="Engineering",
        location="Hyderabad",
        employment_type="full_time",
        minimum_experience=2,
        required_skills=["Python", "FastAPI"],
        preferred_skills=["PostgreSQL"],
    )


def test_create_job_adds_job_to_database_session(
    db_session: Session,
) -> None:
    job = create_job(
        session=db_session,
        payload=build_job_payload(),
    )

    persisted_job = db_session.get(Job, job.id)

    assert job.id is not None
    assert persisted_job is not None
    assert persisted_job.id == job.id
    assert persisted_job.title == "Backend Engineer"
    assert persisted_job.required_skills == ["Python", "FastAPI"]


def test_get_job_by_id_returns_job_or_none(
    db_session: Session,
) -> None:
    created_job = create_job(
        session=db_session,
        payload=build_job_payload(),
    )

    existing_job = get_job_by_id(
        session=db_session,
        job_id=created_job.id,
    )

    missing_job = get_job_by_id(
        session=db_session,
        job_id=uuid4(),
    )

    assert existing_job is not None
    assert existing_job.id == created_job.id
    assert missing_job is None


def test_list_jobs_returns_newest_jobs_with_pagination(
    db_session: Session,
) -> None:
    first_job = create_job(
        session=db_session,
        payload=build_job_payload("First Repository Test"),
    )
    second_job = create_job(
        session=db_session,
        payload=build_job_payload("Second Repository Test"),
    )
    third_job = create_job(
        session=db_session,
        payload=build_job_payload("Third Repository Test"),
    )

    first_job.created_at = datetime(
        9999,
        1,
        1,
        tzinfo=UTC,
    )
    second_job.created_at = datetime(
        9999,
        1,
        2,
        tzinfo=UTC,
    )
    third_job.created_at = datetime(
        9999,
        1,
        3,
        tzinfo=UTC,
    )

    db_session.flush()

    first_page = list_jobs(
        session=db_session,
        offset=0,
        limit=2,
    )

    second_page = list_jobs(
        session=db_session,
        offset=2,
        limit=1,
    )

    assert [job.id for job in first_page] == [
        third_job.id,
        second_job.id,
    ]

    assert [job.id for job in second_page] == [
        first_job.id,
    ]


def test_update_job_changes_only_provided_fields(
    db_session: Session,
) -> None:
    job = create_job(
        session=db_session,
        payload=build_job_payload(),
    )

    original_id = job.id
    original_department = job.department
    original_location = job.location
    original_required_skills = job.required_skills

    updated_job = update_job(
        session=db_session,
        job=job,
        payload=JobUpdate(
            title="Senior Backend Engineer",
            minimum_experience=5,
            preferred_skills=[],
        ),
    )

    assert updated_job is job
    assert updated_job.id == original_id
    assert updated_job.title == "Senior Backend Engineer"
    assert updated_job.minimum_experience == 5
    assert updated_job.preferred_skills == []

    assert updated_job.department == original_department
    assert updated_job.location == original_location
    assert updated_job.required_skills == original_required_skills

    db_session.expire_all()

    persisted_job = get_job_by_id(
        session=db_session,
        job_id=original_id,
    )

    assert persisted_job is not None
    assert persisted_job.title == "Senior Backend Engineer"
    assert persisted_job.minimum_experience == 5
    assert persisted_job.preferred_skills == []


def test_delete_job_removes_job_from_database_session(
    db_session: Session,
) -> None:
    job = create_job(
        session=db_session,
        payload=build_job_payload(),
    )

    job_id = job.id

    delete_result = delete_job(
        session=db_session,
        job=job,
    )

    deleted_job = get_job_by_id(
        session=db_session,
        job_id=job_id,
    )

    assert delete_result is None
    assert deleted_job is None