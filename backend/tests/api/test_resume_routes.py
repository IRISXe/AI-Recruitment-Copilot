from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.resume import Resume


CANDIDATES_URL = "/api/v1/candidates"
RESUMES_URL = "/api/v1/resumes"


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


def valid_resume_payload(
    candidate_id: str,
    *,
    original_filename: str = "Harsha_Resume.pdf",
    stored_filename: str = "harsha-resume.pdf",
    is_primary: bool = False,
) -> dict[str, object]:
    return {
        "candidate_id": candidate_id,
        "original_filename": original_filename,
        "stored_filename": stored_filename,
        "storage_path": f"uploads/resumes/{stored_filename}",
        "content_type": "application/pdf",
        "file_size_bytes": 245760,
        "is_primary": is_primary,
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


def create_resume_through_api(
    client: TestClient,
    *,
    candidate_id: str,
    stored_filename: str = "harsha-resume.pdf",
    is_primary: bool = False,
) -> dict[str, object]:
    response = client.post(
        RESUMES_URL,
        json=valid_resume_payload(
            candidate_id,
            stored_filename=stored_filename,
            is_primary=is_primary,
        ),
    )

    assert response.status_code == 201

    return response.json()


def test_create_resume_returns_201_and_persists_resume(
    client: TestClient,
    db_session: Session,
) -> None:
    candidate = create_candidate_through_api(client)

    response = client.post(
        RESUMES_URL,
        json=valid_resume_payload(
            str(candidate["id"]),
        ),
    )

    assert response.status_code == 201

    body = response.json()
    resume_id = UUID(body["id"])

    assert body["candidate_id"] == candidate["id"]
    assert body["original_filename"] == "Harsha_Resume.pdf"
    assert body["stored_filename"] == "harsha-resume.pdf"
    assert (
        body["storage_path"]
        == "uploads/resumes/harsha-resume.pdf"
    )
    assert body["content_type"] == "application/pdf"
    assert body["file_size_bytes"] == 245760
    assert body["is_primary"] is False
    assert body["created_at"] is not None
    assert body["updated_at"] is not None

    db_session.expire_all()

    persisted_resume = db_session.get(
        Resume,
        resume_id,
    )

    assert persisted_resume is not None
    assert persisted_resume.candidate_id == UUID(
        str(candidate["id"])
    )
    assert persisted_resume.stored_filename == "harsha-resume.pdf"
    assert persisted_resume.is_primary is False


def test_create_resume_returns_404_for_unknown_candidate(
    client: TestClient,
) -> None:
    response = client.post(
        RESUMES_URL,
        json=valid_resume_payload(
            str(uuid4()),
        ),
    )

    assert response.status_code == 404
    assert (
        response.json()["error"]["code"]
        == "candidate_not_found"
    )


@pytest.mark.parametrize(
    "invalid_payload",
    [
        {},
        {
            "candidate_id": "not-a-valid-uuid",
            "original_filename": "Resume.pdf",
            "stored_filename": "resume.pdf",
            "storage_path": "uploads/resumes/resume.pdf",
            "content_type": "application/pdf",
            "file_size_bytes": 100,
        },
        {
            "candidate_id": str(uuid4()),
            "original_filename": "../../Resume.pdf",
            "stored_filename": "resume.pdf",
            "storage_path": "uploads/resumes/resume.pdf",
            "content_type": "application/pdf",
            "file_size_bytes": 100,
        },
        {
            "candidate_id": str(uuid4()),
            "original_filename": "Resume.pdf",
            "stored_filename": "resume.pdf",
            "storage_path": "uploads/resumes/resume.pdf",
            "content_type": "application/pdf",
            "file_size_bytes": -1,
        },
    ],
)
def test_create_resume_rejects_invalid_body(
    client: TestClient,
    db_session: Session,
    invalid_payload: dict[str, object],
) -> None:
    response = client.post(
        RESUMES_URL,
        json=invalid_payload,
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"

    count = db_session.scalar(
        select(func.count()).select_from(Resume)
    )

    assert count == 0


def test_create_primary_resume_demotes_existing_primary(
    client: TestClient,
    db_session: Session,
) -> None:
    candidate = create_candidate_through_api(client)

    first_resume = create_resume_through_api(
        client,
        candidate_id=str(candidate["id"]),
        stored_filename="first-resume.pdf",
        is_primary=True,
    )

    second_resume = create_resume_through_api(
        client,
        candidate_id=str(candidate["id"]),
        stored_filename="second-resume.pdf",
        is_primary=True,
    )

    assert first_resume["is_primary"] is True
    assert second_resume["is_primary"] is True

    db_session.expire_all()

    persisted_first = db_session.get(
        Resume,
        UUID(first_resume["id"]),
    )
    persisted_second = db_session.get(
        Resume,
        UUID(second_resume["id"]),
    )

    assert persisted_first is not None
    assert persisted_second is not None
    assert persisted_first.is_primary is False
    assert persisted_second.is_primary is True


def test_list_resumes_supports_pagination_and_candidate_filtering(
    client: TestClient,
    db_session: Session,
) -> None:
    first_candidate = create_candidate_through_api(client)

    second_candidate = create_candidate_through_api(
        client,
        full_name="Second Candidate",
        email="second@example.com",
    )

    first = create_resume_through_api(
        client,
        candidate_id=str(first_candidate["id"]),
        stored_filename="first-resume.pdf",
    )

    second = create_resume_through_api(
        client,
        candidate_id=str(first_candidate["id"]),
        stored_filename="second-resume.pdf",
    )

    third = create_resume_through_api(
        client,
        candidate_id=str(second_candidate["id"]),
        stored_filename="third-resume.pdf",
    )

    db_session.expire_all()

    first_resume = db_session.get(
        Resume,
        UUID(first["id"]),
    )
    second_resume = db_session.get(
        Resume,
        UUID(second["id"]),
    )
    third_resume = db_session.get(
        Resume,
        UUID(third["id"]),
    )

    assert first_resume is not None
    assert second_resume is not None
    assert third_resume is not None

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

    db_session.commit()

    first_page = client.get(
        RESUMES_URL,
        params={
            "offset": 0,
            "limit": 2,
        },
    )

    second_page = client.get(
        RESUMES_URL,
        params={
            "offset": 2,
            "limit": 1,
        },
    )

    candidate_resumes = client.get(
        RESUMES_URL,
        params={
            "candidate_id": first_candidate["id"],
        },
    )

    assert first_page.status_code == 200
    assert second_page.status_code == 200
    assert candidate_resumes.status_code == 200

    assert [
        resume["id"]
        for resume in first_page.json()
    ] == [
        third["id"],
        second["id"],
    ]

    assert [
        resume["id"]
        for resume in second_page.json()
    ] == [
        first["id"],
    ]

    assert [
        resume["id"]
        for resume in candidate_resumes.json()
    ] == [
        second["id"],
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
def test_list_resumes_rejects_invalid_pagination(
    client: TestClient,
    query_string: str,
) -> None:
    response = client.get(
        f"{RESUMES_URL}{query_string}"
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert response.json()["error"]["details"][0]["loc"][0] == "query"


def test_list_resumes_rejects_malformed_candidate_id(
    client: TestClient,
) -> None:
    response = client.get(
        RESUMES_URL,
        params={
            "candidate_id": "not-a-valid-uuid",
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert response.json()["error"]["details"][0]["loc"] == [
        "query",
        "candidate_id",
    ]


def test_get_resume_by_id_returns_existing_resume(
    client: TestClient,
) -> None:
    candidate = create_candidate_through_api(client)

    created_resume = create_resume_through_api(
        client,
        candidate_id=str(candidate["id"]),
    )

    response = client.get(
        f"{RESUMES_URL}/{created_resume['id']}"
    )

    assert response.status_code == 200
    assert response.json()["id"] == created_resume["id"]
    assert response.json()["candidate_id"] == candidate["id"]
    assert (
        response.json()["stored_filename"]
        == "harsha-resume.pdf"
    )


def test_get_resume_by_id_returns_404_for_unknown_uuid(
    client: TestClient,
) -> None:
    response = client.get(
        f"{RESUMES_URL}/{uuid4()}"
    )

    assert response.status_code == 404
    assert (
        response.json()["error"]["code"]
        == "resume_not_found"
    )


def test_get_resume_by_id_rejects_malformed_uuid(
    client: TestClient,
) -> None:
    response = client.get(
        f"{RESUMES_URL}/not-a-valid-uuid"
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert response.json()["error"]["details"][0]["loc"] == [
        "path",
        "resume_id",
    ]


def test_update_resume_persists_primary_flag(
    client: TestClient,
    db_session: Session,
) -> None:
    candidate = create_candidate_through_api(client)

    created_resume = create_resume_through_api(
        client,
        candidate_id=str(candidate["id"]),
    )

    resume_id = UUID(created_resume["id"])

    response = client.patch(
        f"{RESUMES_URL}/{resume_id}",
        json={
            "is_primary": True,
        },
    )

    assert response.status_code == 200
    assert response.json()["is_primary"] is True
    assert response.json()["stored_filename"] == "harsha-resume.pdf"

    db_session.expire_all()

    persisted_resume = db_session.get(
        Resume,
        resume_id,
    )

    assert persisted_resume is not None
    assert persisted_resume.is_primary is True


def test_update_primary_resume_demotes_previous_primary(
    client: TestClient,
    db_session: Session,
) -> None:
    candidate = create_candidate_through_api(client)

    first_resume = create_resume_through_api(
        client,
        candidate_id=str(candidate["id"]),
        stored_filename="first-resume.pdf",
        is_primary=True,
    )

    second_resume = create_resume_through_api(
        client,
        candidate_id=str(candidate["id"]),
        stored_filename="second-resume.pdf",
    )

    response = client.patch(
        f"{RESUMES_URL}/{second_resume['id']}",
        json={
            "is_primary": True,
        },
    )

    assert response.status_code == 200
    assert response.json()["is_primary"] is True

    db_session.expire_all()

    persisted_first = db_session.get(
        Resume,
        UUID(first_resume["id"]),
    )
    persisted_second = db_session.get(
        Resume,
        UUID(second_resume["id"]),
    )

    assert persisted_first is not None
    assert persisted_second is not None
    assert persisted_first.is_primary is False
    assert persisted_second.is_primary is True


@pytest.mark.parametrize(
    "invalid_payload",
    [
        {},
        {
            "is_primary": None,
        },
    ],
)
def test_update_resume_rejects_invalid_body(
    client: TestClient,
    invalid_payload: dict[str, object],
) -> None:
    candidate = create_candidate_through_api(client)

    created_resume = create_resume_through_api(
        client,
        candidate_id=str(candidate["id"]),
    )

    response = client.patch(
        f"{RESUMES_URL}/{created_resume['id']}",
        json=invalid_payload,
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_update_resume_returns_404_for_unknown_uuid(
    client: TestClient,
) -> None:
    response = client.patch(
        f"{RESUMES_URL}/{uuid4()}",
        json={
            "is_primary": True,
        },
    )

    assert response.status_code == 404
    assert (
        response.json()["error"]["code"]
        == "resume_not_found"
    )


def test_delete_resume_returns_204_and_removes_resume(
    client: TestClient,
    db_session: Session,
) -> None:
    candidate = create_candidate_through_api(client)

    created_resume = create_resume_through_api(
        client,
        candidate_id=str(candidate["id"]),
    )

    resume_id = UUID(created_resume["id"])

    response = client.delete(
        f"{RESUMES_URL}/{resume_id}"
    )

    assert response.status_code == 204
    assert response.content == b""

    db_session.expire_all()

    assert db_session.get(
        Resume,
        resume_id,
    ) is None

    repeated_response = client.delete(
        f"{RESUMES_URL}/{resume_id}"
    )

    assert repeated_response.status_code == 404
    assert (
        repeated_response.json()["error"]["code"]
        == "resume_not_found"
    )


def test_delete_resume_rejects_malformed_uuid(
    client: TestClient,
) -> None:
    response = client.delete(
        f"{RESUMES_URL}/not-a-valid-uuid"
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert response.json()["error"]["details"][0]["loc"] == [
        "path",
        "resume_id",
    ]