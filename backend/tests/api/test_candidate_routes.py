from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.candidate import Candidate


CANDIDATES_URL = "/api/v1/candidates"


def valid_candidate_payload(
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


def test_create_candidate_returns_201_and_persists_candidate(
    client: TestClient,
    db_session: Session,
) -> None:
    response = client.post(
        CANDIDATES_URL,
        json=valid_candidate_payload(),
    )

    assert response.status_code == 201

    body = response.json()
    candidate_id = UUID(body["id"])

    assert body["full_name"] == "Harsha Vardhan"
    assert body["email"] == "harsha@example.com"
    assert body["current_location"] == "Hyderabad"
    assert body["current_role"] == "Backend Developer"
    assert body["total_experience_months"] == 18
    assert body["skills"] == ["Python", "FastAPI", "PostgreSQL"]
    assert body["created_at"] is not None
    assert body["updated_at"] is not None

    db_session.expire_all()

    persisted_candidate = db_session.get(
        Candidate,
        candidate_id,
    )

    assert persisted_candidate is not None
    assert persisted_candidate.full_name == "Harsha Vardhan"
    assert persisted_candidate.email == "harsha@example.com"


def test_create_candidate_rejects_invalid_body(
    client: TestClient,
    db_session: Session,
) -> None:
    payload = valid_candidate_payload()
    payload["full_name"] = "A"

    response = client.post(
        CANDIDATES_URL,
        json=payload,
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert response.json()["error"]["details"][0]["loc"] == [
        "body",
        "full_name",
    ]

    count = db_session.scalar(
        select(func.count()).select_from(Candidate)
    )

    assert count == 0


def test_list_candidates_returns_newest_candidates_with_pagination(
    client: TestClient,
    db_session: Session,
) -> None:
    first = create_candidate_through_api(
        client,
        full_name="First Candidate",
        email="first@example.com",
    )
    second = create_candidate_through_api(
        client,
        full_name="Second Candidate",
        email="second@example.com",
    )
    third = create_candidate_through_api(
        client,
        full_name="Third Candidate",
        email="third@example.com",
    )

    db_session.expire_all()

    first_candidate = db_session.get(Candidate, UUID(first["id"]))
    second_candidate = db_session.get(Candidate, UUID(second["id"]))
    third_candidate = db_session.get(Candidate, UUID(third["id"]))

    assert first_candidate is not None
    assert second_candidate is not None
    assert third_candidate is not None

    first_candidate.created_at = datetime(
        9999,
        1,
        1,
        tzinfo=UTC,
    )
    second_candidate.created_at = datetime(
        9999,
        1,
        2,
        tzinfo=UTC,
    )
    third_candidate.created_at = datetime(
        9999,
        1,
        3,
        tzinfo=UTC,
    )

    # This commits only a savepoint. The fixture still rolls
    # back the outer transaction after the test.
    db_session.commit()

    first_page = client.get(
        CANDIDATES_URL,
        params={
            "offset": 0,
            "limit": 2,
        },
    )

    second_page = client.get(
        CANDIDATES_URL,
        params={
            "offset": 2,
            "limit": 1,
        },
    )

    assert first_page.status_code == 200
    assert second_page.status_code == 200

    assert [
        candidate["full_name"]
        for candidate in first_page.json()
    ] == [
        "Third Candidate",
        "Second Candidate",
    ]

    assert [
        candidate["full_name"]
        for candidate in second_page.json()
    ] == [
        "First Candidate",
    ]


@pytest.mark.parametrize(
    "query_string",
    [
        "?offset=-1&limit=20",
        "?offset=0&limit=0",
        "?offset=0&limit=101",
    ],
)
def test_list_candidates_rejects_invalid_pagination(
    client: TestClient,
    query_string: str,
) -> None:
    response = client.get(
        f"{CANDIDATES_URL}{query_string}"
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert response.json()["error"]["details"][0]["loc"][0] == "query"


def test_get_candidate_by_id_returns_existing_candidate(
    client: TestClient,
) -> None:
    created_candidate = create_candidate_through_api(client)

    response = client.get(
        f"{CANDIDATES_URL}/{created_candidate['id']}"
    )

    assert response.status_code == 200
    assert response.json()["id"] == created_candidate["id"]
    assert response.json()["full_name"] == "Harsha Vardhan"


def test_get_candidate_by_id_returns_404_for_unknown_uuid(
    client: TestClient,
) -> None:
    response = client.get(
        f"{CANDIDATES_URL}/{uuid4()}"
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "candidate_not_found"


def test_get_candidate_by_id_rejects_malformed_uuid(
    client: TestClient,
) -> None:
    response = client.get(
        f"{CANDIDATES_URL}/not-a-valid-uuid"
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert response.json()["error"]["details"][0]["loc"] == [
        "path",
        "candidate_id",
    ]


def test_update_candidate_partially_updates_and_persists_changes(
    client: TestClient,
    db_session: Session,
) -> None:
    created_candidate = create_candidate_through_api(client)
    candidate_id = UUID(created_candidate["id"])

    response = client.patch(
        f"{CANDIDATES_URL}/{candidate_id}",
        json={
            "full_name": "Harsha Updated",
            "current_role": "Senior Backend Developer",
            "total_experience_months": 24,
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["full_name"] == "Harsha Updated"
    assert body["current_role"] == "Senior Backend Developer"
    assert body["total_experience_months"] == 24

    assert body["email"] == "harsha@example.com"
    assert body["phone"] == "+91 9876543210"
    assert body["current_location"] == "Hyderabad"
    assert body["skills"] == ["Python", "FastAPI", "PostgreSQL"]

    db_session.expire_all()

    persisted_candidate = db_session.get(
        Candidate,
        candidate_id,
    )

    assert persisted_candidate is not None
    assert persisted_candidate.full_name == "Harsha Updated"
    assert persisted_candidate.current_role == "Senior Backend Developer"
    assert persisted_candidate.total_experience_months == 24


@pytest.mark.parametrize(
    "invalid_payload",
    [
        {},
        {"full_name": None},
        {"full_name": "A"},
    ],
)
def test_update_candidate_rejects_invalid_body(
    client: TestClient,
    invalid_payload: dict[str, object],
) -> None:
    created_candidate = create_candidate_through_api(client)

    response = client.patch(
        f"{CANDIDATES_URL}/{created_candidate['id']}",
        json=invalid_payload,
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_update_candidate_returns_404_for_unknown_uuid(
    client: TestClient,
) -> None:
    response = client.patch(
        f"{CANDIDATES_URL}/{uuid4()}",
        json={
            "current_role": "Unknown Candidate",
        },
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "candidate_not_found"


def test_delete_candidate_returns_204_and_removes_candidate(
    client: TestClient,
    db_session: Session,
) -> None:
    created_candidate = create_candidate_through_api(client)
    candidate_id = UUID(created_candidate["id"])

    response = client.delete(
        f"{CANDIDATES_URL}/{candidate_id}"
    )

    assert response.status_code == 204
    assert response.content == b""

    db_session.expire_all()

    assert db_session.get(Candidate, candidate_id) is None

    repeated_response = client.delete(
        f"{CANDIDATES_URL}/{candidate_id}"
    )

    assert repeated_response.status_code == 404
    assert (
        repeated_response.json()["error"]["code"]
        == "candidate_not_found"
    )


def test_delete_candidate_rejects_malformed_uuid(
    client: TestClient,
) -> None:
    response = client.delete(
        f"{CANDIDATES_URL}/not-a-valid-uuid"
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert response.json()["error"]["details"][0]["loc"] == [
        "path",
        "candidate_id",
    ]