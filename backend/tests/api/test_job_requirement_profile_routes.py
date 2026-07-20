from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.job_requirement_profile import JobRequirementProfile


JOBS_URL = "/api/v1/jobs"


FULL_JOB_DESCRIPTION = """
Job Title: Senior Backend Engineer
Department: Engineering
Location: Hyderabad
Work mode: Hybrid
Employment type: Full-time

About the Role
We are looking for a Senior Backend Engineer to build scalable
cloud applications.

Responsibilities
- Design and develop REST APIs using Python and FastAPI.
- Maintain PostgreSQL databases.
- Deploy applications using Docker and AWS.

Required Skills
- Python
- FastAPI
- PostgreSQL
- Docker
- Minimum 3 years of experience
- Bachelor's degree in Computer Science

Preferred Skills
- Kubernetes
- AWS Certified Developer certification preferred
"""


def valid_job_payload(
    *,
    title: str = "Senior Backend Engineer",
    description: str | None = FULL_JOB_DESCRIPTION,
) -> dict[str, object]:
    return {
        "title": title,
        "description": description,
        "department": "Engineering",
        "location": "Hyderabad",
        "employment_type": "full_time",
        "minimum_experience": 3,
        "required_skills": [
            "Python",
            "FastAPI",
            "PostgreSQL",
        ],
        "preferred_skills": [
            "Docker",
            "Kubernetes",
        ],
    }


def create_job(
    client: TestClient,
    *,
    description: str | None = FULL_JOB_DESCRIPTION,
) -> dict[str, object]:
    response = client.post(
        JOBS_URL,
        json=valid_job_payload(
            description=description,
        ),
    )

    assert response.status_code == 201

    return response.json()


def test_parse_job_requirement_profile_returns_completed_profile(
    client: TestClient,
    db_session: Session,
) -> None:
    created_job = create_job(client)
    job_id = UUID(created_job["id"])

    response = client.post(
        f"{JOBS_URL}/{job_id}/parse"
    )

    assert response.status_code == 200

    body = response.json()

    assert UUID(body["job_id"]) == job_id
    assert body["parsing_status"] == "completed"
    assert body["parsing_error"] is None
    assert body["parser_version"] == "job-rule-based-v1"
    assert len(body["source_description_sha256"]) == 64
    assert body["parsed_at"] is not None

    profile_data = body["profile_data"]

    assert profile_data["job_title"] == "Senior Backend Engineer"
    assert profile_data["department"] == "Engineering"
    assert profile_data["location"] == "Hyderabad"
    assert profile_data["employment_type"] == "full_time"
    assert profile_data["work_mode"] == "hybrid"
    assert profile_data["seniority_level"] == "senior"
    assert profile_data["minimum_experience_years"] == 3

    assert "Python" in profile_data["required_skills"]
    assert "FastAPI" in profile_data["required_skills"]
    assert "PostgreSQL" in profile_data["required_skills"]
    assert "Kubernetes" in profile_data["preferred_skills"]

    db_session.expire_all()

    statement = select(JobRequirementProfile).where(
        JobRequirementProfile.job_id == job_id
    )

    persisted_profile = db_session.scalar(statement)

    assert persisted_profile is not None
    assert persisted_profile.parsing_status == "completed"
    assert persisted_profile.parser_version == "job-rule-based-v1"
    assert persisted_profile.profile_data is not None
    assert (
        persisted_profile.profile_data["job_title"]
        == "Senior Backend Engineer"
    )


def test_get_job_requirement_profile_returns_existing_profile(
    client: TestClient,
) -> None:
    created_job = create_job(client)
    job_id = created_job["id"]

    parsed_response = client.post(
        f"{JOBS_URL}/{job_id}/parse"
    )

    assert parsed_response.status_code == 200

    response = client.get(
        f"{JOBS_URL}/{job_id}/profile"
    )

    assert response.status_code == 200
    assert response.json()["id"] == parsed_response.json()["id"]
    assert response.json()["job_id"] == job_id
    assert response.json()["parsing_status"] == "completed"


def test_get_job_requirement_profile_returns_404_before_parsing(
    client: TestClient,
) -> None:
    created_job = create_job(client)

    response = client.get(
        f"{JOBS_URL}/{created_job['id']}/profile"
    )

    assert response.status_code == 404
    assert (
        response.json()["error"]["code"]
        == "job_requirement_profile_not_found"
    )


def test_parse_job_requirement_profile_rejects_empty_description(
    client: TestClient,
) -> None:
    created_job = create_job(
        client,
        description=None,
    )

    response = client.post(
        f"{JOBS_URL}/{created_job['id']}/parse"
    )

    assert response.status_code == 422
    assert (
        response.json()["error"]["code"]
        == "job_description_empty"
    )


@pytest.mark.parametrize(
    "endpoint_suffix",
    [
        "parse",
        "profile",
    ],
)
def test_job_requirement_profile_routes_return_404_for_unknown_job(
    client: TestClient,
    endpoint_suffix: str,
) -> None:
    job_id = uuid4()

    if endpoint_suffix == "parse":
        response = client.post(
            f"{JOBS_URL}/{job_id}/parse"
        )
    else:
        response = client.get(
            f"{JOBS_URL}/{job_id}/profile"
        )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "job_not_found"


def test_force_true_reprocesses_existing_profile(
    client: TestClient,
) -> None:
    created_job = create_job(client)
    job_id = created_job["id"]

    first_response = client.post(
        f"{JOBS_URL}/{job_id}/parse"
    )

    second_response = client.post(
        f"{JOBS_URL}/{job_id}/parse",
        params={
            "force": True,
        },
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200

    assert second_response.json()["id"] == first_response.json()["id"]
    assert second_response.json()["parsing_status"] == "completed"
    assert (
        second_response.json()["source_description_sha256"]
        == first_response.json()["source_description_sha256"]
    )
