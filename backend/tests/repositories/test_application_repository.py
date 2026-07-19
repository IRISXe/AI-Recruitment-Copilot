from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models.application import Application
from app.repositories.application_repository import (
    create_application,
    delete_application,
    get_application_by_id,
    get_application_by_job_and_candidate,
    list_applications,
    update_application,
)
from app.repositories.candidate_repository import create_candidate
from app.repositories.job_repository import create_job
from app.schemas.application import (
    ApplicationCreate,
    ApplicationUpdate,
)
from app.schemas.candidate import CandidateCreate
from app.schemas.job import JobCreate


def build_job_payload() -> JobCreate:
    return JobCreate(
        title="Backend Engineer",
        department="Engineering",
        location="Hyderabad",
        employment_type="full_time",
        minimum_experience=2,
        required_skills=["Python", "FastAPI"],
        preferred_skills=["PostgreSQL"],
    )


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


def test_create_application_adds_application_to_database_session(
    db_session: Session,
) -> None:
    job = create_job(
        session=db_session,
        payload=build_job_payload(),
    )
    candidate = create_candidate(
        session=db_session,
        payload=build_candidate_payload(),
    )

    application = create_application(
        session=db_session,
        payload=ApplicationCreate(
            job_id=job.id,
            candidate_id=candidate.id,
            source="LinkedIn",
            notes="Candidate applied for the backend role.",
        ),
    )

    persisted_application = db_session.get(
        Application,
        application.id,
    )

    assert application.id is not None
    assert persisted_application is not None
    assert persisted_application.id == application.id
    assert persisted_application.job_id == job.id
    assert persisted_application.candidate_id == candidate.id
    assert persisted_application.status == "applied"
    assert persisted_application.source == "LinkedIn"
    assert (
        persisted_application.notes
        == "Candidate applied for the backend role."
    )


def test_get_application_by_id_returns_application_or_none(
    db_session: Session,
) -> None:
    job = create_job(
        session=db_session,
        payload=build_job_payload(),
    )
    candidate = create_candidate(
        session=db_session,
        payload=build_candidate_payload(),
    )
    created_application = create_application(
        session=db_session,
        payload=ApplicationCreate(
            job_id=job.id,
            candidate_id=candidate.id,
        ),
    )

    existing_application = get_application_by_id(
        session=db_session,
        application_id=created_application.id,
    )
    missing_application = get_application_by_id(
        session=db_session,
        application_id=uuid4(),
    )

    assert existing_application is not None
    assert existing_application.id == created_application.id
    assert existing_application.job_id == job.id
    assert existing_application.candidate_id == candidate.id
    assert missing_application is None


def test_get_application_by_job_and_candidate_returns_application_or_none(
    db_session: Session,
) -> None:
    job = create_job(
        session=db_session,
        payload=build_job_payload(),
    )
    candidate = create_candidate(
        session=db_session,
        payload=build_candidate_payload(),
    )
    created_application = create_application(
        session=db_session,
        payload=ApplicationCreate(
            job_id=job.id,
            candidate_id=candidate.id,
        ),
    )

    existing_application = get_application_by_job_and_candidate(
        session=db_session,
        job_id=job.id,
        candidate_id=candidate.id,
    )
    missing_application = get_application_by_job_and_candidate(
        session=db_session,
        job_id=uuid4(),
        candidate_id=uuid4(),
    )

    assert existing_application is not None
    assert existing_application.id == created_application.id
    assert existing_application.job_id == job.id
    assert existing_application.candidate_id == candidate.id
    assert missing_application is None


def test_list_applications_returns_newest_with_pagination(
    db_session: Session,
) -> None:
    job = create_job(
        session=db_session,
        payload=build_job_payload(),
    )

    first_candidate = create_candidate(
        session=db_session,
        payload=build_candidate_payload(
            full_name="First Candidate",
            email="first@example.com",
        ),
    )
    second_candidate = create_candidate(
        session=db_session,
        payload=build_candidate_payload(
            full_name="Second Candidate",
            email="second@example.com",
        ),
    )
    third_candidate = create_candidate(
        session=db_session,
        payload=build_candidate_payload(
            full_name="Third Candidate",
            email="third@example.com",
        ),
    )

    first_application = create_application(
        session=db_session,
        payload=ApplicationCreate(
            job_id=job.id,
            candidate_id=first_candidate.id,
        ),
    )
    second_application = create_application(
        session=db_session,
        payload=ApplicationCreate(
            job_id=job.id,
            candidate_id=second_candidate.id,
        ),
    )
    third_application = create_application(
        session=db_session,
        payload=ApplicationCreate(
            job_id=job.id,
            candidate_id=third_candidate.id,
        ),
    )

    first_application.created_at = datetime(
        9999,
        1,
        1,
        tzinfo=UTC,
    )
    second_application.created_at = datetime(
        9999,
        1,
        2,
        tzinfo=UTC,
    )
    third_application.created_at = datetime(
        9999,
        1,
        3,
        tzinfo=UTC,
    )

    db_session.flush()

    first_page = list_applications(
        session=db_session,
        offset=0,
        limit=2,
    )
    second_page = list_applications(
        session=db_session,
        offset=2,
        limit=1,
    )

    assert [application.id for application in first_page] == [
        third_application.id,
        second_application.id,
    ]
    assert [application.id for application in second_page] == [
        first_application.id,
    ]


def test_update_application_changes_only_provided_fields(
    db_session: Session,
) -> None:
    job = create_job(
        session=db_session,
        payload=build_job_payload(),
    )
    candidate = create_candidate(
        session=db_session,
        payload=build_candidate_payload(),
    )
    application = create_application(
        session=db_session,
        payload=ApplicationCreate(
            job_id=job.id,
            candidate_id=candidate.id,
            source="LinkedIn",
            notes="Initial application note.",
        ),
    )

    original_id = application.id
    original_job_id = application.job_id
    original_candidate_id = application.candidate_id
    original_source = application.source

    updated_application = update_application(
        session=db_session,
        application=application,
        payload=ApplicationUpdate(
            status="screening",
            notes="Candidate moved to screening.",
        ),
    )

    assert updated_application is application
    assert updated_application.id == original_id
    assert updated_application.status == "screening"
    assert (
        updated_application.notes
        == "Candidate moved to screening."
    )

    assert updated_application.job_id == original_job_id
    assert updated_application.candidate_id == original_candidate_id
    assert updated_application.source == original_source

    db_session.expire_all()

    persisted_application = get_application_by_id(
        session=db_session,
        application_id=original_id,
    )

    assert persisted_application is not None
    assert persisted_application.status == "screening"
    assert (
        persisted_application.notes
        == "Candidate moved to screening."
    )
    assert persisted_application.source == "LinkedIn"


def test_delete_application_removes_application_from_database_session(
    db_session: Session,
) -> None:
    job = create_job(
        session=db_session,
        payload=build_job_payload(),
    )
    candidate = create_candidate(
        session=db_session,
        payload=build_candidate_payload(),
    )
    application = create_application(
        session=db_session,
        payload=ApplicationCreate(
            job_id=job.id,
            candidate_id=candidate.id,
        ),
    )

    application_id = application.id

    delete_result = delete_application(
        session=db_session,
        application=application,
    )

    deleted_application = get_application_by_id(
        session=db_session,
        application_id=application_id,
    )

    assert delete_result is None
    assert deleted_application is None


def test_list_applications_filters_by_job_candidate_and_status(
    db_session: Session,
) -> None:
    first_job = create_job(
        session=db_session,
        payload=build_job_payload(),
    )
    second_job = create_job(
        session=db_session,
        payload=build_job_payload(),
    )

    first_candidate = create_candidate(
        session=db_session,
        payload=build_candidate_payload(
            full_name="First Filter Candidate",
            email="first-filter-repository@example.com",
        ),
    )
    second_candidate = create_candidate(
        session=db_session,
        payload=build_candidate_payload(
            full_name="Second Filter Candidate",
            email="second-filter-repository@example.com",
        ),
    )

    matching_application = create_application(
        session=db_session,
        payload=ApplicationCreate(
            job_id=first_job.id,
            candidate_id=first_candidate.id,
            status="screening",
        ),
    )
    create_application(
        session=db_session,
        payload=ApplicationCreate(
            job_id=first_job.id,
            candidate_id=second_candidate.id,
            status="screening",
        ),
    )
    create_application(
        session=db_session,
        payload=ApplicationCreate(
            job_id=second_job.id,
            candidate_id=first_candidate.id,
            status="screening",
        ),
    )
    create_application(
        session=db_session,
        payload=ApplicationCreate(
            job_id=second_job.id,
            candidate_id=second_candidate.id,
            status="applied",
        ),
    )

    results = list_applications(
        session=db_session,
        offset=0,
        limit=20,
        job_id=first_job.id,
        candidate_id=first_candidate.id,
        application_status="screening",
    )

    assert [application.id for application in results] == [
        matching_application.id,
    ]
