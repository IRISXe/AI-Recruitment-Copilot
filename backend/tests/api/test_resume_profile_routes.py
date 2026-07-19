from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.candidate import Candidate
from app.models.resume import Resume
from app.models.resume_content import ResumeContent
from app.models.resume_profile import ResumeProfile


RESUMES_URL = "/api/v1/resumes"


def persist_candidate_and_resume(
    db_session: Session,
) -> Resume:
    candidate = Candidate(
        full_name="Resume Parsing Candidate",
        email=f"resume-parsing-{uuid4()}@example.com",
        phone="+91 9876543210",
        current_location="Hyderabad",
        current_role="Backend Developer",
        total_experience_months=18,
        skills=["Python", "FastAPI"],
    )

    db_session.add(candidate)
    db_session.flush()

    resume_id = uuid4()

    resume = Resume(
        id=resume_id,
        candidate_id=candidate.id,
        original_filename="candidate-resume.pdf",
        stored_filename=f"{resume_id}.pdf",
        storage_path=f"uploads/resumes/{resume_id}.pdf",
        content_type="application/pdf",
        file_size_bytes=1024,
        is_primary=True,
    )

    db_session.add(resume)
    db_session.flush()

    return resume


def persist_resume_content(
    db_session: Session,
    *,
    resume: Resume,
    extracted_text: str | None,
    extraction_status: str = "completed",
) -> ResumeContent:
    resume_content = ResumeContent(
        resume_id=resume.id,
        extracted_text=extracted_text,
        extraction_status=extraction_status,
        extraction_error=None,
        extractor_version="test-extractor-v1",
    )

    db_session.add(resume_content)
    db_session.flush()

    return resume_content


def test_parse_resume_profile_returns_structured_profile(
    client: TestClient,
    db_session: Session,
) -> None:
    resume = persist_candidate_and_resume(db_session)

    persist_resume_content(
        db_session,
        resume=resume,
        extracted_text="""
        Harsha Vardhan
        harsha.vardhan@example.com
        +91 98765 43210

        Professional Summary
        Backend developer experienced in API development.

        Technical Skills
        Python, FastAPI, PostgreSQL, React.js,
        TypeScript, AWS, Docker and Git
        """,
    )

    response = client.post(
        f"{RESUMES_URL}/{resume.id}/parse"
    )

    assert response.status_code == 200

    body = response.json()

    assert UUID(body["resume_id"]) == resume.id
    assert body["parsing_status"] == "completed"
    assert body["parsing_error"] is None
    assert body["parser_version"] == "rule-based-v1"
    assert len(body["source_text_sha256"]) == 64
    assert body["parsed_at"] is not None

    profile_data = body["profile_data"]

    assert profile_data["full_name"] == "Harsha Vardhan"
    assert (
        profile_data["email"]
        == "harsha.vardhan@example.com"
    )
    assert profile_data["phone"] == "+919876543210"
    assert profile_data["skills"] == [
        "AWS",
        "Docker",
        "FastAPI",
        "Git",
        "PostgreSQL",
        "Python",
        "React.js",
        "TypeScript",
    ]

    db_session.expire_all()

    persisted_profile = (
        db_session.query(ResumeProfile)
        .filter(
            ResumeProfile.resume_id == resume.id
        )
        .one_or_none()
    )

    assert persisted_profile is not None
    assert persisted_profile.parsing_status == "completed"
    assert persisted_profile.profile_data == profile_data


def test_get_resume_profile_returns_parsed_profile(
    client: TestClient,
    db_session: Session,
) -> None:
    resume = persist_candidate_and_resume(db_session)

    persist_resume_content(
        db_session,
        resume=resume,
        extracted_text="""
        Harsha Vardhan
        harsha@example.com

        Skills
        Python and FastAPI
        """,
    )

    parse_response = client.post(
        f"{RESUMES_URL}/{resume.id}/parse"
    )

    assert parse_response.status_code == 200

    response = client.get(
        f"{RESUMES_URL}/{resume.id}/profile"
    )

    assert response.status_code == 200
    assert response.json()["id"] == parse_response.json()["id"]
    assert response.json()["resume_id"] == str(resume.id)
    assert response.json()["parsing_status"] == "completed"
    assert response.json()["profile_data"]["skills"] == [
        "FastAPI",
        "Python",
    ]


def test_parse_resume_profile_returns_404_for_unknown_resume(
    client: TestClient,
) -> None:
    response = client.post(
        f"{RESUMES_URL}/{uuid4()}/parse"
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "resume_not_found"


def test_parse_resume_profile_requires_extracted_content(
    client: TestClient,
    db_session: Session,
) -> None:
    resume = persist_candidate_and_resume(db_session)

    response = client.post(
        f"{RESUMES_URL}/{resume.id}/parse"
    )

    assert response.status_code == 404
    assert (
        response.json()["error"]["code"]
        == "resume_content_not_found"
    )


def test_parse_resume_profile_requires_completed_extraction(
    client: TestClient,
    db_session: Session,
) -> None:
    resume = persist_candidate_and_resume(db_session)

    persist_resume_content(
        db_session,
        resume=resume,
        extracted_text=None,
        extraction_status="pending",
    )

    response = client.post(
        f"{RESUMES_URL}/{resume.id}/parse"
    )

    assert response.status_code == 409
    assert (
        response.json()["error"]["code"]
        == "resume_content_not_ready"
    )


def test_parse_resume_profile_rejects_empty_content(
    client: TestClient,
    db_session: Session,
) -> None:
    resume = persist_candidate_and_resume(db_session)

    persist_resume_content(
        db_session,
        resume=resume,
        extracted_text=" \n\t ",
    )

    response = client.post(
        f"{RESUMES_URL}/{resume.id}/parse"
    )

    assert response.status_code == 422
    assert (
        response.json()["error"]["code"]
        == "resume_content_empty"
    )


def test_get_resume_profile_returns_404_before_parsing(
    client: TestClient,
    db_session: Session,
) -> None:
    resume = persist_candidate_and_resume(db_session)

    response = client.get(
        f"{RESUMES_URL}/{resume.id}/profile"
    )

    assert response.status_code == 404
    assert (
        response.json()["error"]["code"]
        == "resume_profile_not_found"
    )


@pytest.mark.parametrize(
    "endpoint",
    [
        "parse",
        "profile",
    ],
)
def test_resume_profile_routes_reject_malformed_uuid(
    client: TestClient,
    endpoint: str,
) -> None:
    method = (
        client.post
        if endpoint == "parse"
        else client.get
    )

    response = method(
        f"{RESUMES_URL}/not-a-valid-uuid/{endpoint}"
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert response.json()["error"]["details"][0]["loc"] == [
        "path",
        "resume_id",
    ]