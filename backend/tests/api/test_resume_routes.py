from datetime import UTC, datetime
from unittest.mock import patch
from uuid import UUID, uuid4
from pathlib import Path
import pytest
from fastapi import UploadFile
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.candidate import Candidate
from app.models.resume import Resume
from app.core.config import Settings

CANDIDATES_URL = "/api/v1/candidates"
RESUMES_URL = "/api/v1/resumes"

PDF_BYTES = b"%PDF-1.4\nResume content"


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
        "skills": [
            "Python",
            "FastAPI",
            "PostgreSQL",
        ],
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


def valid_resume_payload(
    *,
    candidate_id: str | None = None,
    stored_filename: str = "harsha-resume.pdf",
    is_primary: bool = False,
) -> dict[str, object]:
    return {
        "candidate_id": candidate_id or str(uuid4()),
        "original_filename": "Harsha_Resume.pdf",
        "stored_filename": stored_filename,
        "storage_path": (
            f"uploads/resumes/{stored_filename}"
        ),
        "content_type": "application/pdf",
        "file_size_bytes": 245760,
        "is_primary": is_primary,
    }


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
            candidate_id=candidate_id,
            stored_filename=stored_filename,
            is_primary=is_primary,
        ),
    )

    assert response.status_code == 201

    return response.json()


def build_uploaded_resume(
    *,
    candidate_id: UUID,
    is_primary: bool = False,
) -> Resume:
    timestamp = datetime.now(UTC)

    return Resume(
        id=uuid4(),
        candidate_id=candidate_id,
        original_filename="Harsha_Resume.pdf",
        stored_filename="stored-resume.pdf",
        storage_path=(
            "local_storage/resumes/stored-resume.pdf"
        ),
        content_type="application/pdf",
        file_size_bytes=len(PDF_BYTES),
        is_primary=is_primary,
        created_at=timestamp,
        updated_at=timestamp,
    )


def test_create_resume_returns_201_and_persists_resume(
    client: TestClient,
    db_session: Session,
) -> None:
    candidate = create_candidate_through_api(client)

    response = client.post(
        RESUMES_URL,
        json=valid_resume_payload(
            candidate_id=str(candidate["id"]),
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
    assert (
        persisted_resume.candidate_id
        == UUID(str(candidate["id"]))
    )
    assert (
        persisted_resume.original_filename
        == "Harsha_Resume.pdf"
    )
    assert (
        persisted_resume.stored_filename
        == "harsha-resume.pdf"
    )


@pytest.mark.parametrize(
    "invalid_payload",
    [
        {},
        {
            **valid_resume_payload(),
            "candidate_id": "not-a-valid-uuid",
        },
        {
            **valid_resume_payload(),
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
    assert (
        response.json()["error"]["code"]
        == "validation_error"
    )

    count = db_session.scalar(
        select(func.count()).select_from(Resume)
    )

    assert count == 0


def test_create_resume_returns_404_for_unknown_candidate(
    client: TestClient,
) -> None:
    response = client.post(
        RESUMES_URL,
        json=valid_resume_payload(
            candidate_id=str(uuid4()),
        ),
    )

    assert response.status_code == 404
    assert (
        response.json()["error"]["code"]
        == "candidate_not_found"
    )


def test_create_primary_resume_demotes_existing_primary(
    client: TestClient,
    db_session: Session,
) -> None:
    candidate = create_candidate_through_api(client)

    first = create_resume_through_api(
        client,
        candidate_id=str(candidate["id"]),
        stored_filename="first-resume.pdf",
        is_primary=True,
    )

    second = create_resume_through_api(
        client,
        candidate_id=str(candidate["id"]),
        stored_filename="second-resume.pdf",
        is_primary=True,
    )

    first_response = client.get(
        f"{RESUMES_URL}/{first['id']}"
    )
    second_response = client.get(
        f"{RESUMES_URL}/{second['id']}"
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200

    assert first_response.json()["is_primary"] is False
    assert second_response.json()["is_primary"] is True

    db_session.expire_all()

    first_resume = db_session.get(
        Resume,
        UUID(str(first["id"])),
    )
    second_resume = db_session.get(
        Resume,
        UUID(str(second["id"])),
    )

    assert first_resume is not None
    assert second_resume is not None
    assert first_resume.is_primary is False
    assert second_resume.is_primary is True


def test_list_resumes_returns_newest_with_pagination(
    client: TestClient,
    db_session: Session,
) -> None:
    candidate = create_candidate_through_api(client)

    first = create_resume_through_api(
        client,
        candidate_id=str(candidate["id"]),
        stored_filename="first-resume.pdf",
    )
    second = create_resume_through_api(
        client,
        candidate_id=str(candidate["id"]),
        stored_filename="second-resume.pdf",
    )
    third = create_resume_through_api(
        client,
        candidate_id=str(candidate["id"]),
        stored_filename="third-resume.pdf",
    )

    db_session.expire_all()

    first_resume = db_session.get(
        Resume,
        UUID(str(first["id"])),
    )
    second_resume = db_session.get(
        Resume,
        UUID(str(second["id"])),
    )
    third_resume = db_session.get(
        Resume,
        UUID(str(third["id"])),
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

    assert first_page.status_code == 200
    assert second_page.status_code == 200

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
    assert (
        response.json()["error"]["code"]
        == "validation_error"
    )
    assert (
        response.json()["error"]["details"][0]["loc"][0]
        == "query"
    )


def test_list_resumes_filters_by_candidate_id(
    client: TestClient,
) -> None:
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

    first_resume = create_resume_through_api(
        client,
        candidate_id=str(first_candidate["id"]),
        stored_filename="first-candidate-resume.pdf",
    )

    create_resume_through_api(
        client,
        candidate_id=str(second_candidate["id"]),
        stored_filename="second-candidate-resume.pdf",
    )

    response = client.get(
        RESUMES_URL,
        params={
            "candidate_id": first_candidate["id"],
        },
    )

    assert response.status_code == 200
    assert len(response.json()) == 1

    assert response.json()[0]["id"] == first_resume["id"]
    assert (
        response.json()[0]["candidate_id"]
        == first_candidate["id"]
    )


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
    assert (
        response.json()["error"]["code"]
        == "validation_error"
    )
    assert response.json()["error"]["details"][0]["loc"] == [
        "query",
        "candidate_id",
    ]


def test_get_resume_by_id_returns_existing_resume(
    client: TestClient,
) -> None:
    candidate = create_candidate_through_api(client)

    resume = create_resume_through_api(
        client,
        candidate_id=str(candidate["id"]),
    )

    response = client.get(
        f"{RESUMES_URL}/{resume['id']}"
    )

    assert response.status_code == 200
    assert response.json()["id"] == resume["id"]
    assert (
        response.json()["candidate_id"]
        == candidate["id"]
    )
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
    assert (
        response.json()["error"]["code"]
        == "validation_error"
    )
    assert response.json()["error"]["details"][0]["loc"] == [
        "path",
        "resume_id",
    ]


def test_update_resume_sets_primary_and_demotes_previous_primary(
    client: TestClient,
    db_session: Session,
) -> None:
    candidate = create_candidate_through_api(client)

    first = create_resume_through_api(
        client,
        candidate_id=str(candidate["id"]),
        stored_filename="first-resume.pdf",
        is_primary=True,
    )

    second = create_resume_through_api(
        client,
        candidate_id=str(candidate["id"]),
        stored_filename="second-resume.pdf",
        is_primary=False,
    )

    response = client.patch(
        f"{RESUMES_URL}/{second['id']}",
        json={
            "is_primary": True,
        },
    )

    assert response.status_code == 200
    assert response.json()["is_primary"] is True
    assert response.json()["id"] == second["id"]

    first_response = client.get(
        f"{RESUMES_URL}/{first['id']}"
    )

    assert first_response.status_code == 200
    assert first_response.json()["is_primary"] is False

    db_session.expire_all()

    first_resume = db_session.get(
        Resume,
        UUID(str(first["id"])),
    )
    second_resume = db_session.get(
        Resume,
        UUID(str(second["id"])),
    )

    assert first_resume is not None
    assert second_resume is not None
    assert first_resume.is_primary is False
    assert second_resume.is_primary is True


@pytest.mark.parametrize(
    "invalid_payload",
    [
        {},
        {
            "is_primary": "not-a-boolean",
        },
    ],
)
def test_update_resume_rejects_invalid_body(
    client: TestClient,
    invalid_payload: dict[str, object],
) -> None:
    candidate = create_candidate_through_api(client)

    resume = create_resume_through_api(
        client,
        candidate_id=str(candidate["id"]),
    )

    response = client.patch(
        f"{RESUMES_URL}/{resume['id']}",
        json=invalid_payload,
    )

    assert response.status_code == 422
    assert (
        response.json()["error"]["code"]
        == "validation_error"
    )


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


def test_update_resume_rejects_malformed_uuid(
    client: TestClient,
) -> None:
    response = client.patch(
        f"{RESUMES_URL}/not-a-valid-uuid",
        json={
            "is_primary": True,
        },
    )

    assert response.status_code == 422
    assert (
        response.json()["error"]["code"]
        == "validation_error"
    )
    assert response.json()["error"]["details"][0]["loc"] == [
        "path",
        "resume_id",
    ]


def test_delete_resume_returns_204_and_removes_resume(
    client: TestClient,
    db_session: Session,
) -> None:
    candidate = create_candidate_through_api(client)

    resume = create_resume_through_api(
        client,
        candidate_id=str(candidate["id"]),
    )

    resume_id = UUID(str(resume["id"]))

    response = client.delete(
        f"{RESUMES_URL}/{resume_id}"
    )

    assert response.status_code == 204
    assert response.content == b""

    db_session.expire_all()

    assert db_session.get(Resume, resume_id) is None

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
    assert (
        response.json()["error"]["code"]
        == "validation_error"
    )
    assert response.json()["error"]["details"][0]["loc"] == [
        "path",
        "resume_id",
    ]


def test_upload_resume_accepts_multipart_file_and_returns_201(
    client: TestClient,
) -> None:
    expected_candidate_id = uuid4()

    resume = build_uploaded_resume(
        candidate_id=expected_candidate_id,
        is_primary=True,
    )

    captured: dict[str, object] = {}

    def fake_upload_service(
        session: Session,
        *,
        candidate_id: UUID,
        uploaded_file: UploadFile,
        is_primary: bool,
    ) -> Resume:
        captured["session"] = session
        captured["candidate_id"] = candidate_id
        captured["filename"] = uploaded_file.filename
        captured["content_type"] = uploaded_file.content_type
        captured["content"] = uploaded_file.file.read()
        captured["is_primary"] = is_primary

        return resume

    with patch(
        "app.api.routes.resumes.upload_resume_service",
        side_effect=fake_upload_service,
    ) as upload_service:
        response = client.post(
            f"{RESUMES_URL}/upload",
            data={
                "candidate_id": str(expected_candidate_id),
                "is_primary": "true",
            },
            files={
                "file": (
                    "Harsha_Resume.pdf",
                    PDF_BYTES,
                    "application/pdf",
                ),
            },
        )

    assert response.status_code == 201

    upload_service.assert_called_once()

    assert captured["candidate_id"] == expected_candidate_id
    assert captured["filename"] == "Harsha_Resume.pdf"
    assert captured["content_type"] == "application/pdf"
    assert captured["content"] == PDF_BYTES
    assert captured["is_primary"] is True

    body = response.json()

    assert body["id"] == str(resume.id)
    assert body["candidate_id"] == str(expected_candidate_id)
    assert body["original_filename"] == "Harsha_Resume.pdf"
    assert body["stored_filename"] == "stored-resume.pdf"
    assert body["content_type"] == "application/pdf"
    assert body["file_size_bytes"] == len(PDF_BYTES)
    assert body["is_primary"] is True


def test_upload_resume_defaults_is_primary_to_false(
    client: TestClient,
) -> None:
    candidate_id = uuid4()

    resume = build_uploaded_resume(
        candidate_id=candidate_id,
    )

    with patch(
        "app.api.routes.resumes.upload_resume_service",
        return_value=resume,
    ) as upload_service:
        response = client.post(
            f"{RESUMES_URL}/upload",
            data={
                "candidate_id": str(candidate_id),
            },
            files={
                "file": (
                    "Harsha_Resume.pdf",
                    PDF_BYTES,
                    "application/pdf",
                ),
            },
        )

    assert response.status_code == 201

    upload_service.assert_called_once()

    _, call_kwargs = upload_service.call_args

    assert call_kwargs["candidate_id"] == candidate_id
    assert call_kwargs["is_primary"] is False
    assert (
        call_kwargs["uploaded_file"].filename
        == "Harsha_Resume.pdf"
    )

    assert response.json()["is_primary"] is False


def test_upload_resume_rejects_malformed_candidate_uuid(
    client: TestClient,
) -> None:
    with patch(
        "app.api.routes.resumes.upload_resume_service",
    ) as upload_service:
        response = client.post(
            f"{RESUMES_URL}/upload",
            data={
                "candidate_id": "not-a-valid-uuid",
                "is_primary": "false",
            },
            files={
                "file": (
                    "Harsha_Resume.pdf",
                    PDF_BYTES,
                    "application/pdf",
                ),
            },
        )

    assert response.status_code == 422
    assert (
        response.json()["error"]["code"]
        == "validation_error"
    )

    details = response.json()["error"]["details"]

    assert any(
        detail["loc"] == ["body", "candidate_id"]
        for detail in details
    )

    upload_service.assert_not_called()


def test_upload_resume_requires_candidate_id(
    client: TestClient,
) -> None:
    with patch(
        "app.api.routes.resumes.upload_resume_service",
    ) as upload_service:
        response = client.post(
            f"{RESUMES_URL}/upload",
            data={
                "is_primary": "false",
            },
            files={
                "file": (
                    "Harsha_Resume.pdf",
                    PDF_BYTES,
                    "application/pdf",
                ),
            },
        )

    assert response.status_code == 422
    assert (
        response.json()["error"]["code"]
        == "validation_error"
    )

    details = response.json()["error"]["details"]

    assert any(
        detail["loc"] == ["body", "candidate_id"]
        for detail in details
    )

    upload_service.assert_not_called()


def test_upload_resume_requires_file(
    client: TestClient,
) -> None:
    with patch(
        "app.api.routes.resumes.upload_resume_service",
    ) as upload_service:
        response = client.post(
            f"{RESUMES_URL}/upload",
            data={
                "candidate_id": str(uuid4()),
                "is_primary": "false",
            },
        )

    assert response.status_code == 422
    assert (
        response.json()["error"]["code"]
        == "validation_error"
    )

    details = response.json()["error"]["details"]

    assert any(
        detail["loc"] == ["body", "file"]
        for detail in details
    )

    upload_service.assert_not_called()
def test_upload_and_delete_resume_manages_real_local_file(
    client: TestClient,
    db_session: Session,
    tmp_path: Path,
) -> None:
    candidate = create_candidate_through_api(client)

    settings = Settings(
        database_url=(
            "postgresql+psycopg://"
            "user:password@localhost/test"
        ),
        resume_storage_directory=(
            tmp_path / "resumes"
        ),
    )

    with patch(
        "app.services.resume_service.get_settings",
        return_value=settings,
    ):
        upload_response = client.post(
            f"{RESUMES_URL}/upload",
            data={
                "candidate_id": str(candidate["id"]),
                "is_primary": "true",
            },
            files={
                "file": (
                    "Harsha_Resume.pdf",
                    PDF_BYTES,
                    "application/pdf",
                ),
            },
        )

        assert upload_response.status_code == 201

        uploaded_resume = upload_response.json()
        resume_id = UUID(uploaded_resume["id"])
        stored_path = Path(
            uploaded_resume["storage_path"]
        )

        assert stored_path.exists()
        assert stored_path.is_file()
        assert stored_path.read_bytes() == PDF_BYTES

        assert (
            stored_path.parent
            == settings.resume_storage_directory
        )

        assert (
            uploaded_resume["candidate_id"]
            == candidate["id"]
        )
        assert (
            uploaded_resume["original_filename"]
            == "Harsha_Resume.pdf"
        )
        assert (
            uploaded_resume["content_type"]
            == "application/pdf"
        )
        assert (
            uploaded_resume["file_size_bytes"]
            == len(PDF_BYTES)
        )
        assert uploaded_resume["is_primary"] is True

        db_session.expire_all()

        persisted_resume = db_session.get(
            Resume,
            resume_id,
        )

        assert persisted_resume is not None
        assert (
            persisted_resume.storage_path
            == stored_path.as_posix()
        )

        delete_response = client.delete(
            f"{RESUMES_URL}/{resume_id}"
        )

        assert delete_response.status_code == 204
        assert delete_response.content == b""

        assert not stored_path.exists()

        db_session.expire_all()

        assert (
            db_session.get(
                Resume,
                resume_id,
            )
            is None
        )