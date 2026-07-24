from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.job import Job


JOBS_URL = "/api/v1/jobs"

JOB_DESCRIPTION = (
    "We are looking for a Backend Engineer with "
    "Python, FastAPI, PostgreSQL, and Docker experience."
)


def valid_job_payload(
    title: str = "Backend Engineer",
) -> dict[str, object]:
    return {
        "title": title,
        "description": JOB_DESCRIPTION,
        "department": "Engineering",
        "location": "Hyderabad",
        "employment_type": "full_time",
        "minimum_experience": 2,
        "required_skills": [
            "Python",
            "FastAPI",
        ],
        "preferred_skills": [
            "PostgreSQL",
        ],
    }


def create_job_through_api(
    client: TestClient,
    *,
    title: str = "Backend Engineer",
) -> dict[str, object]:
    response = client.post(
        JOBS_URL,
        json=valid_job_payload(
            title,
        ),
    )

    assert response.status_code == 201

    return response.json()


def test_validate_job_returns_200_without_inserting_row(
    client: TestClient,
    db_session: Session,
) -> None:
    response = client.post(
        f"{JOBS_URL}/validate",
        json=valid_job_payload(),
    )

    assert response.status_code == 200
    assert (
        response.json()["message"]
        == "Job information is valid."
    )
    assert (
        response.json()["job"]["title"]
        == "Backend Engineer"
    )
    assert (
        response.json()["job"]["description"]
        == JOB_DESCRIPTION
    )

    count = db_session.scalar(
        select(func.count()).select_from(Job)
    )

    assert count == 0


def test_create_job_returns_201_and_persists_job(
    client: TestClient,
    db_session: Session,
) -> None:
    response = client.post(
        JOBS_URL,
        json=valid_job_payload(),
    )

    assert response.status_code == 201

    body = response.json()
    job_id = UUID(str(body["id"]))

    assert body["title"] == "Backend Engineer"
    assert body["description"] == JOB_DESCRIPTION
    assert body["department"] == "Engineering"
    assert body["required_skills"] == [
        "Python",
        "FastAPI",
    ]
    assert body["created_at"] is not None
    assert body["updated_at"] is not None

    db_session.expire_all()

    persisted_job = db_session.get(
        Job,
        job_id,
    )

    assert persisted_job is not None
    assert (
        persisted_job.title
        == "Backend Engineer"
    )
    assert (
        persisted_job.description
        == JOB_DESCRIPTION
    )


def test_create_job_allows_missing_description(
    client: TestClient,
    db_session: Session,
) -> None:
    payload = valid_job_payload()
    payload.pop("description")

    response = client.post(
        JOBS_URL,
        json=payload,
    )

    assert response.status_code == 201
    assert response.json()["description"] is None

    job_id = UUID(
        str(response.json()["id"])
    )

    db_session.expire_all()

    persisted_job = db_session.get(
        Job,
        job_id,
    )

    assert persisted_job is not None
    assert persisted_job.description is None


def test_create_job_rejects_invalid_body(
    client: TestClient,
    db_session: Session,
) -> None:
    payload = valid_job_payload()
    payload["required_skills"] = []

    response = client.post(
        JOBS_URL,
        json=payload,
    )

    assert response.status_code == 422
    assert (
        response.json()["error"]["code"]
        == "validation_error"
    )
    assert (
        response.json()["error"]["details"][0]["loc"]
        == [
            "body",
            "required_skills",
        ]
    )

    count = db_session.scalar(
        select(func.count()).select_from(Job)
    )

    assert count == 0


def test_list_jobs_returns_newest_jobs_with_pagination(
    client: TestClient,
    db_session: Session,
) -> None:
    first = create_job_through_api(
        client,
        title="First API Test",
    )
    second = create_job_through_api(
        client,
        title="Second API Test",
    )
    third = create_job_through_api(
        client,
        title="Third API Test",
    )

    db_session.expire_all()

    first_job = db_session.get(
        Job,
        UUID(str(first["id"])),
    )
    second_job = db_session.get(
        Job,
        UUID(str(second["id"])),
    )
    third_job = db_session.get(
        Job,
        UUID(str(third["id"])),
    )

    assert first_job is not None
    assert second_job is not None
    assert third_job is not None

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

    # The fixture keeps an outer transaction active.
    # This commit creates only a nested savepoint.
    db_session.commit()

    first_page = client.get(
        JOBS_URL,
        params={
            "offset": 0,
            "limit": 2,
        },
    )

    second_page = client.get(
        JOBS_URL,
        params={
            "offset": 2,
            "limit": 1,
        },
    )

    assert first_page.status_code == 200
    assert second_page.status_code == 200

    assert [
        job["title"]
        for job in first_page.json()
    ] == [
        "Third API Test",
        "Second API Test",
    ]

    assert [
        job["title"]
        for job in second_page.json()
    ] == [
        "First API Test",
    ]


@pytest.mark.parametrize(
    "query_string",
    [
        "?offset=-1&limit=20",
        "?offset=0&limit=0",
        "?offset=0&limit=101",
    ],
)
def test_list_jobs_rejects_invalid_pagination(
    client: TestClient,
    query_string: str,
) -> None:
    response = client.get(
        f"{JOBS_URL}{query_string}"
    )

    assert response.status_code == 422
    assert (
        response.json()["error"]["code"]
        == "validation_error"
    )
    assert (
        response.json()["error"]["details"][0]["loc"][0]
        == "query"
    )


def test_get_job_by_id_returns_existing_job(
    client: TestClient,
) -> None:
    created_job = create_job_through_api(
        client
    )

    response = client.get(
        f"{JOBS_URL}/{created_job['id']}"
    )

    assert response.status_code == 200
    assert (
        response.json()["id"]
        == created_job["id"]
    )
    assert (
        response.json()["title"]
        == "Backend Engineer"
    )
    assert (
        response.json()["description"]
        == JOB_DESCRIPTION
    )


def test_get_job_by_id_returns_404_for_unknown_uuid(
    client: TestClient,
) -> None:
    response = client.get(
        f"{JOBS_URL}/{uuid4()}"
    )

    assert response.status_code == 404
    assert (
        response.json()["error"]["code"]
        == "job_not_found"
    )


def test_get_job_by_id_rejects_malformed_uuid(
    client: TestClient,
) -> None:
    response = client.get(
        f"{JOBS_URL}/not-a-valid-uuid"
    )

    assert response.status_code == 422
    assert (
        response.json()["error"]["code"]
        == "validation_error"
    )
    assert (
        response.json()["error"]["details"][0]["loc"]
        == [
            "path",
            "job_id",
        ]
    )


def test_update_job_partially_updates_and_persists_changes(
    client: TestClient,
    db_session: Session,
) -> None:
    created_job = create_job_through_api(
        client
    )
    job_id = UUID(
        str(created_job["id"])
    )

    response = client.patch(
        f"{JOBS_URL}/{job_id}",
        json={
            "title": "Senior Backend Engineer",
            "minimum_experience": 5,
            "preferred_skills": [],
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert (
        body["title"]
        == "Senior Backend Engineer"
    )
    assert body["minimum_experience"] == 5
    assert body["preferred_skills"] == []

    assert body["description"] == JOB_DESCRIPTION
    assert body["department"] == "Engineering"
    assert body["location"] == "Hyderabad"
    assert body["required_skills"] == [
        "Python",
        "FastAPI",
    ]

    db_session.expire_all()

    persisted_job = db_session.get(
        Job,
        job_id,
    )

    assert persisted_job is not None
    assert (
        persisted_job.title
        == "Senior Backend Engineer"
    )
    assert persisted_job.minimum_experience == 5
    assert persisted_job.preferred_skills == []
    assert (
        persisted_job.description
        == JOB_DESCRIPTION
    )


def test_update_job_updates_description_and_persists_change(
    client: TestClient,
    db_session: Session,
) -> None:
    created_job = create_job_through_api(
        client
    )
    job_id = UUID(
        str(created_job["id"])
    )

    updated_description = (
        "Job Title: Senior Frontend Engineer\n"
        "Department: Engineering\n"
        "Location: Hyderabad\n"
        "Employment Type: Full-time\n"
        "Work Mode: Hybrid\n\n"
        "Required Skills\n"
        "- React\n"
        "- TypeScript\n"
        "- Jest\n\n"
        "Experience\n"
        "Minimum 3 years of frontend experience."
    )

    response = client.patch(
        f"{JOBS_URL}/{job_id}",
        json={
            "description": updated_description,
        },
    )

    assert response.status_code == 200, response.text

    body = response.json()

    assert (
        body["description"]
        == updated_description
    )

    assert (
        body["title"]
        == "Backend Engineer"
    )
    assert body["department"] == "Engineering"

    db_session.expire_all()

    persisted_job = db_session.get(
        Job,
        job_id,
    )

    assert persisted_job is not None
    assert (
        persisted_job.description
        == updated_description
    )


@pytest.mark.parametrize(
    "invalid_payload",
    [
        {},
        {
            "title": None,
        },
        {
            "title": "A",
        },
        {
            "description": None,
        },
        {
            "description": "   ",
        },
    ],
)
def test_update_job_rejects_invalid_body(
    client: TestClient,
    invalid_payload: dict[str, object],
) -> None:
    created_job = create_job_through_api(
        client
    )

    response = client.patch(
        f"{JOBS_URL}/{created_job['id']}",
        json=invalid_payload,
    )

    assert response.status_code == 422
    assert (
        response.json()["error"]["code"]
        == "validation_error"
    )


def test_update_job_returns_404_for_unknown_uuid(
    client: TestClient,
) -> None:
    response = client.patch(
        f"{JOBS_URL}/{uuid4()}",
        json={
            "title": "Unknown Job",
        },
    )

    assert response.status_code == 404
    assert (
        response.json()["error"]["code"]
        == "job_not_found"
    )


def test_delete_job_returns_204_and_removes_job(
    client: TestClient,
    db_session: Session,
) -> None:
    created_job = create_job_through_api(
        client
    )
    job_id = UUID(
        str(created_job["id"])
    )

    response = client.delete(
        f"{JOBS_URL}/{job_id}"
    )

    assert response.status_code == 204
    assert response.content == b""

    db_session.expire_all()

    assert db_session.get(
        Job,
        job_id,
    ) is None

    repeated_response = client.delete(
        f"{JOBS_URL}/{job_id}"
    )

    assert repeated_response.status_code == 404
    assert (
        repeated_response.json()["error"]["code"]
        == "job_not_found"
    )


def test_delete_job_rejects_malformed_uuid(
    client: TestClient,
) -> None:
    response = client.delete(
        f"{JOBS_URL}/not-a-valid-uuid"
    )

    assert response.status_code == 422
    assert (
        response.json()["error"]["code"]
        == "validation_error"
    )
    assert (
        response.json()["error"]["details"][0]["loc"]
        == [
            "path",
            "job_id",
        ]
    )