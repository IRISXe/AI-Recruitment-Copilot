from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.application import Application


APPLICATIONS_URL = "/api/v1/applications"
JOBS_URL = "/api/v1/jobs"
CANDIDATES_URL = "/api/v1/candidates"


def valid_job_payload(
    title: str = "Backend Engineer",
) -> dict[str, object]:
    return {
        "title": title,
        "department": "Engineering",
        "location": "Hyderabad",
        "employment_type": "full_time",
        "minimum_experience": 2,
        "required_skills": ["Python", "FastAPI"],
        "preferred_skills": ["PostgreSQL"],
    }


def valid_candidate_payload(
    *,
    full_name: str = "Harsha Vardhan",
    email: str = "harsha@example.com",
) -> dict[str, object]:
    return {
        "full_name": full_name,
        "email": email,
        "phone": "+91 9876543210",
        "current_location": "Hyderabad",
        "current_role": "Backend Developer",
        "total_experience_months": 18,
        "skills": ["Python", "FastAPI", "PostgreSQL"],
    }


def create_job_through_api(
    client: TestClient,
    *,
    title: str = "Backend Engineer",
) -> dict[str, object]:
    response = client.post(
        JOBS_URL,
        json=valid_job_payload(title),
    )

    assert response.status_code == 201

    return response.json()


def create_candidate_through_api(
    client: TestClient,
    *,
    full_name: str = "Harsha Vardhan",
    email: str = "harsha@example.com",
) -> dict[str, object]:
    response = client.post(
        CANDIDATES_URL,
        json=valid_candidate_payload(
            full_name=full_name,
            email=email,
        ),
    )

    assert response.status_code == 201

    return response.json()


def create_application_through_api(
    client: TestClient,
    *,
    job_id: str,
    candidate_id: str,
    source: str | None = "LinkedIn",
    notes: str | None = "Candidate applied for the backend role.",
) -> dict[str, object]:
    response = client.post(
        APPLICATIONS_URL,
        json={
            "job_id": job_id,
            "candidate_id": candidate_id,
            "source": source,
            "notes": notes,
        },
    )

    assert response.status_code == 201

    return response.json()


def test_create_application_returns_201_and_persists_application(
    client: TestClient,
    db_session: Session,
) -> None:
    job = create_job_through_api(client)
    candidate = create_candidate_through_api(client)

    response = client.post(
        APPLICATIONS_URL,
        json={
            "job_id": job["id"],
            "candidate_id": candidate["id"],
            "source": "LinkedIn",
            "notes": "Candidate applied for the backend role.",
        },
    )

    assert response.status_code == 201

    body = response.json()
    application_id = UUID(body["id"])

    assert body["job_id"] == job["id"]
    assert body["candidate_id"] == candidate["id"]
    assert body["status"] == "applied"
    assert body["source"] == "LinkedIn"
    assert body["notes"] == "Candidate applied for the backend role."
    assert body["created_at"] is not None
    assert body["updated_at"] is not None

    db_session.expire_all()

    persisted_application = db_session.get(
        Application,
        application_id,
    )

    assert persisted_application is not None
    assert persisted_application.job_id == UUID(job["id"])
    assert persisted_application.candidate_id == UUID(
        candidate["id"]
    )
    assert persisted_application.status == "applied"


def test_create_application_accepts_explicit_status(
    client: TestClient,
) -> None:
    job = create_job_through_api(client)
    candidate = create_candidate_through_api(client)

    response = client.post(
        APPLICATIONS_URL,
        json={
            "job_id": job["id"],
            "candidate_id": candidate["id"],
            "status": "screening",
        },
    )

    assert response.status_code == 201
    assert response.json()["status"] == "screening"


@pytest.mark.parametrize(
    "invalid_payload",
    [
        {},
        {
            "job_id": "not-a-valid-uuid",
            "candidate_id": str(uuid4()),
        },
        {
            "job_id": str(uuid4()),
            "candidate_id": str(uuid4()),
            "status": "invalid",
        },
    ],
)
def test_create_application_rejects_invalid_body(
    client: TestClient,
    db_session: Session,
    invalid_payload: dict[str, object],
) -> None:
    response = client.post(
        APPLICATIONS_URL,
        json=invalid_payload,
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"

    count = db_session.scalar(
        select(func.count()).select_from(Application)
    )

    assert count == 0


def test_create_application_returns_404_for_unknown_job(
    client: TestClient,
) -> None:
    candidate = create_candidate_through_api(client)

    response = client.post(
        APPLICATIONS_URL,
        json={
            "job_id": str(uuid4()),
            "candidate_id": candidate["id"],
        },
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "job_not_found"


def test_create_application_returns_404_for_unknown_candidate(
    client: TestClient,
) -> None:
    job = create_job_through_api(client)

    response = client.post(
        APPLICATIONS_URL,
        json={
            "job_id": job["id"],
            "candidate_id": str(uuid4()),
        },
    )

    assert response.status_code == 404
    assert (
        response.json()["error"]["code"]
        == "candidate_not_found"
    )


def test_create_application_rejects_duplicate_candidate_and_job(
    client: TestClient,
) -> None:
    job = create_job_through_api(client)
    candidate = create_candidate_through_api(client)

    first_response = client.post(
        APPLICATIONS_URL,
        json={
            "job_id": job["id"],
            "candidate_id": candidate["id"],
        },
    )

    duplicate_response = client.post(
        APPLICATIONS_URL,
        json={
            "job_id": job["id"],
            "candidate_id": candidate["id"],
        },
    )

    assert first_response.status_code == 201
    assert duplicate_response.status_code == 409
    assert (
        duplicate_response.json()["error"]["code"]
        == "application_already_exists"
    )


def test_list_applications_returns_newest_with_pagination(
    client: TestClient,
    db_session: Session,
) -> None:
    job = create_job_through_api(client)

    first_candidate = create_candidate_through_api(
        client,
        full_name="First Candidate",
        email="first@example.com",
    )

    second_candidate = create_candidate_through_api(
        client,
        full_name="Second Candidate",
        email="second@example.com",
    )

    third_candidate = create_candidate_through_api(
        client,
        full_name="Third Candidate",
        email="third@example.com",
    )

    first = create_application_through_api(
        client,
        job_id=str(job["id"]),
        candidate_id=str(first_candidate["id"]),
    )

    second = create_application_through_api(
        client,
        job_id=str(job["id"]),
        candidate_id=str(second_candidate["id"]),
    )

    third = create_application_through_api(
        client,
        job_id=str(job["id"]),
        candidate_id=str(third_candidate["id"]),
    )

    db_session.expire_all()

    first_application = db_session.get(
        Application,
        UUID(first["id"]),
    )

    second_application = db_session.get(
        Application,
        UUID(second["id"]),
    )

    third_application = db_session.get(
        Application,
        UUID(third["id"]),
    )

    assert first_application is not None
    assert second_application is not None
    assert third_application is not None

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

    db_session.commit()

    first_page = client.get(
        APPLICATIONS_URL,
        params={
            "offset": 0,
            "limit": 2,
        },
    )

    second_page = client.get(
        APPLICATIONS_URL,
        params={
            "offset": 2,
            "limit": 1,
        },
    )

    assert first_page.status_code == 200
    assert second_page.status_code == 200

    assert [
        application["id"]
        for application in first_page.json()
    ] == [
        third["id"],
        second["id"],
    ]

    assert [
        application["id"]
        for application in second_page.json()
    ] == [
        first["id"],
    ]


@pytest.mark.parametrize(
    "query_string",
    [
        "?offset=-1&limit=20",
        "?offset=0&limit=0",
        "?offset=0&limit=101",
    ],
)
def test_list_applications_rejects_invalid_pagination(
    client: TestClient,
    query_string: str,
) -> None:
    response = client.get(
        f"{APPLICATIONS_URL}{query_string}"
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert response.json()["error"]["details"][0]["loc"][0] == "query"


def test_get_application_by_id_returns_existing_application(
    client: TestClient,
) -> None:
    job = create_job_through_api(client)
    candidate = create_candidate_through_api(client)

    created_application = create_application_through_api(
        client,
        job_id=str(job["id"]),
        candidate_id=str(candidate["id"]),
    )

    response = client.get(
        f"{APPLICATIONS_URL}/{created_application['id']}"
    )

    assert response.status_code == 200
    assert response.json()["id"] == created_application["id"]
    assert response.json()["job_id"] == job["id"]
    assert response.json()["candidate_id"] == candidate["id"]


def test_get_application_by_id_returns_404_for_unknown_uuid(
    client: TestClient,
) -> None:
    response = client.get(
        f"{APPLICATIONS_URL}/{uuid4()}"
    )

    assert response.status_code == 404
    assert (
        response.json()["error"]["code"]
        == "application_not_found"
    )


def test_get_application_by_id_rejects_malformed_uuid(
    client: TestClient,
) -> None:
    response = client.get(
        f"{APPLICATIONS_URL}/not-a-valid-uuid"
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert response.json()["error"]["details"][0]["loc"] == [
        "path",
        "application_id",
    ]


def test_update_application_partially_updates_and_persists_changes(
    client: TestClient,
    db_session: Session,
) -> None:
    job = create_job_through_api(client)
    candidate = create_candidate_through_api(client)

    created_application = create_application_through_api(
        client,
        job_id=str(job["id"]),
        candidate_id=str(candidate["id"]),
    )

    application_id = UUID(created_application["id"])

    response = client.patch(
        f"{APPLICATIONS_URL}/{application_id}",
        json={
            "status": "screening",
            "notes": "Candidate moved to screening.",
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "screening"
    assert body["notes"] == "Candidate moved to screening."
    assert body["source"] == "LinkedIn"
    assert body["job_id"] == job["id"]
    assert body["candidate_id"] == candidate["id"]

    db_session.expire_all()

    persisted_application = db_session.get(
        Application,
        application_id,
    )

    assert persisted_application is not None
    assert persisted_application.status == "screening"
    assert (
        persisted_application.notes
        == "Candidate moved to screening."
    )
    assert persisted_application.source == "LinkedIn"


def test_update_application_can_clear_nullable_fields(
    client: TestClient,
) -> None:
    job = create_job_through_api(client)
    candidate = create_candidate_through_api(client)

    created_application = create_application_through_api(
        client,
        job_id=str(job["id"]),
        candidate_id=str(candidate["id"]),
    )

    response = client.patch(
        f"{APPLICATIONS_URL}/{created_application['id']}",
        json={
            "source": None,
            "notes": None,
        },
    )

    assert response.status_code == 200
    assert response.json()["source"] is None
    assert response.json()["notes"] is None


@pytest.mark.parametrize(
    "invalid_payload",
    [
        {},
        {"status": None},
        {"status": "invalid"},
        {"source": ""},
        {"notes": ""},
    ],
)
def test_update_application_rejects_invalid_body(
    client: TestClient,
    invalid_payload: dict[str, object],
) -> None:
    job = create_job_through_api(client)
    candidate = create_candidate_through_api(client)

    created_application = create_application_through_api(
        client,
        job_id=str(job["id"]),
        candidate_id=str(candidate["id"]),
    )

    response = client.patch(
        f"{APPLICATIONS_URL}/{created_application['id']}",
        json=invalid_payload,
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_update_application_returns_404_for_unknown_uuid(
    client: TestClient,
) -> None:
    response = client.patch(
        f"{APPLICATIONS_URL}/{uuid4()}",
        json={
            "status": "screening",
        },
    )

    assert response.status_code == 404
    assert (
        response.json()["error"]["code"]
        == "application_not_found"
    )


def test_delete_application_returns_204_and_removes_application(
    client: TestClient,
    db_session: Session,
) -> None:
    job = create_job_through_api(client)
    candidate = create_candidate_through_api(client)

    created_application = create_application_through_api(
        client,
        job_id=str(job["id"]),
        candidate_id=str(candidate["id"]),
    )

    application_id = UUID(created_application["id"])

    response = client.delete(
        f"{APPLICATIONS_URL}/{application_id}"
    )

    assert response.status_code == 204
    assert response.content == b""

    db_session.expire_all()

    assert db_session.get(
        Application,
        application_id,
    ) is None

    repeated_response = client.delete(
        f"{APPLICATIONS_URL}/{application_id}"
    )

    assert repeated_response.status_code == 404
    assert (
        repeated_response.json()["error"]["code"]
        == "application_not_found"
    )


def test_delete_application_rejects_malformed_uuid(
    client: TestClient,
) -> None:
    response = client.delete(
        f"{APPLICATIONS_URL}/not-a-valid-uuid"
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert response.json()["error"]["details"][0]["loc"] == [
        "path",
        "application_id",
    ]