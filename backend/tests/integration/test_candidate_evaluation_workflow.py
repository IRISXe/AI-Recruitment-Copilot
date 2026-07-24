from io import BytesIO
from pathlib import Path
from uuid import UUID, uuid4

from docx import Document
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.candidate_job_match import (
    CandidateJobMatch,
)
from app.models.job_requirement_profile import (
    JobRequirementProfile,
)
from app.models.resume_content import ResumeContent
from app.models.resume_profile import ResumeProfile


JOBS_URL = "/api/v1/jobs"
CANDIDATES_URL = "/api/v1/candidates"
RESUMES_URL = "/api/v1/resumes"

DOCX_CONTENT_TYPE = (
    "application/vnd.openxmlformats-officedocument."
    "wordprocessingml.document"
)

VALID_RECOMMENDATIONS = {
    "strong_match",
    "good_match",
    "partial_match",
    "weak_match",
    "insufficient_data",
}


def initial_job_description() -> str:
    return """
Job Title: Frontend Engineer
Department: Engineering
Location: Hyderabad
Employment Type: Full-time
Work Mode: Hybrid
Seniority Level: Mid

Summary
We are hiring a Frontend Engineer to build scalable
web applications using React and TypeScript.

Responsibilities
- Build reusable React components.
- Integrate REST APIs.
- Improve frontend performance.
- Collaborate with backend engineers.

Required Skills
- React
- TypeScript
- REST APIs

Preferred Skills
- AWS
- Docker

Experience
Minimum 1 year of frontend development experience.

Education
Bachelor's degree in Computer Science or a related field.
""".strip()


def updated_job_description() -> str:
    return """
Job Title: Senior Frontend Engineer
Department: Engineering
Location: Hyderabad
Employment Type: Full-time
Work Mode: Hybrid
Seniority Level: Senior

Summary
We are hiring a Senior Frontend Engineer to build,
test, and maintain scalable React applications.

Responsibilities
- Build reusable React components.
- Integrate REST APIs.
- Write automated frontend tests.
- Improve performance and accessibility.
- Mentor junior frontend developers.

Required Skills
- React
- TypeScript
- REST APIs
- Jest

Preferred Skills
- AWS
- Docker
- React Testing Library

Experience
Minimum 3 years of frontend development experience.

Education
Bachelor's degree in Computer Science or a related field.
""".strip()


def resume_text() -> str:
    return """
Harsha Vardhan
harsha.phase13@example.com
+91 9876543210
Location: Hyderabad
Current Role: Frontend Engineer

Professional Summary
Frontend Engineer experienced in building React and
TypeScript applications and integrating REST APIs.

Skills
React, TypeScript, REST APIs, AWS, Docker

Work Experience
Company: Acme Technologies
Role: Frontend Engineer
January 2023 - June 2024
- Built reusable React components.
- Integrated REST APIs.
- Improved frontend performance.
- Deployed applications using AWS.

Education
Institution: JNTU Hyderabad
Degree: Bachelor of Technology
Field of Study: Computer Science
Dates: 2019 - 2023

Projects
Project: AI Recruitment Copilot
Description: Recruitment workflow automation platform
Technologies: React, TypeScript, FastAPI, PostgreSQL
- Built reusable frontend components.
- Integrated backend REST APIs.

Certifications
Certification: AWS Cloud Practitioner
Issuer: Amazon Web Services
Issue Date: January 2024

Languages
English
Hindi
Telugu
""".strip()


def build_resume_docx() -> bytes:
    document = Document()

    for line in resume_text().splitlines():
        document.add_paragraph(line)

    buffer = BytesIO()
    document.save(buffer)

    return buffer.getvalue()


def create_job_through_api(
    client: TestClient,
    *,
    description: str | None = None,
) -> dict[str, object]:
    response = client.post(
        JOBS_URL,
        json={
            "title": "Frontend Engineer",
            "description": (
                description or initial_job_description()
            ),
            "department": "Engineering",
            "location": "Hyderabad",
            "employment_type": "full_time",
            "minimum_experience": 1,
            "required_skills": [
                "React",
                "TypeScript",
                "REST APIs",
            ],
            "preferred_skills": [
                "AWS",
                "Docker",
            ],
        },
    )

    assert response.status_code == 201, response.text

    return response.json()


def create_candidate_through_api(
    client: TestClient,
) -> dict[str, object]:
    unique_email = (
        f"phase13-{uuid4().hex}@example.com"
    )

    response = client.post(
        CANDIDATES_URL,
        json={
            "full_name": "Harsha Vardhan",
            "email": unique_email,
            "phone": "+91 9876543210",
            "current_location": "Hyderabad",
            "current_role": "Frontend Engineer",
            "total_experience_months": 18,
            "skills": [
                "React",
                "TypeScript",
                "REST APIs",
                "AWS",
                "Docker",
            ],
        },
    )

    assert response.status_code == 201, response.text

    return response.json()


def upload_primary_resume_through_api(
    client: TestClient,
    *,
    candidate_id: UUID,
) -> dict[str, object]:
    response = client.post(
        f"{RESUMES_URL}/upload",
        data={
            "candidate_id": str(candidate_id),
            "is_primary": "true",
        },
        files={
            "file": (
                "Harsha_Phase13_Resume.docx",
                build_resume_docx(),
                DOCX_CONTENT_TYPE,
            ),
        },
    )

    assert response.status_code == 201, response.text

    body = response.json()

    assert body["candidate_id"] == str(candidate_id)
    assert body["is_primary"] is True
    assert body["content_type"] == DOCX_CONTENT_TYPE

    return body


def evaluation_url(
    *,
    candidate_id: UUID,
    job_id: UUID,
) -> str:
    return (
        f"/api/v1/candidates/{candidate_id}/"
        f"jobs/{job_id}/evaluate"
    )


def remove_uploaded_file(
    uploaded_resume: dict[str, object] | None,
) -> None:
    if uploaded_resume is None:
        return

    storage_path = uploaded_resume.get(
        "storage_path"
    )

    if not storage_path:
        return

    Path(str(storage_path)).unlink(
        missing_ok=True
    )


def get_persisted_pipeline(
    db_session: Session,
    *,
    candidate_id: UUID,
    job_id: UUID,
    resume_id: UUID,
) -> tuple[
    ResumeContent,
    ResumeProfile,
    JobRequirementProfile,
    CandidateJobMatch,
]:
    db_session.expire_all()

    resume_content = db_session.scalar(
        select(ResumeContent).where(
            ResumeContent.resume_id == resume_id
        )
    )

    resume_profile = db_session.scalar(
        select(ResumeProfile).where(
            ResumeProfile.resume_id == resume_id
        )
    )

    job_profile = db_session.scalar(
        select(JobRequirementProfile).where(
            JobRequirementProfile.job_id == job_id
        )
    )

    candidate_job_match = db_session.scalar(
        select(CandidateJobMatch).where(
            CandidateJobMatch.candidate_id
            == candidate_id,
            CandidateJobMatch.job_id == job_id,
        )
    )

    assert resume_content is not None
    assert resume_profile is not None
    assert job_profile is not None
    assert candidate_job_match is not None

    return (
        resume_content,
        resume_profile,
        job_profile,
        candidate_job_match,
    )


def assert_single_pipeline_rows(
    db_session: Session,
    *,
    candidate_id: UUID,
    job_id: UUID,
    resume_id: UUID,
) -> None:
    resume_content_count = db_session.scalar(
        select(func.count())
        .select_from(ResumeContent)
        .where(
            ResumeContent.resume_id == resume_id
        )
    )

    resume_profile_count = db_session.scalar(
        select(func.count())
        .select_from(ResumeProfile)
        .where(
            ResumeProfile.resume_id == resume_id
        )
    )

    job_profile_count = db_session.scalar(
        select(func.count())
        .select_from(JobRequirementProfile)
        .where(
            JobRequirementProfile.job_id == job_id
        )
    )

    match_count = db_session.scalar(
        select(func.count())
        .select_from(CandidateJobMatch)
        .where(
            CandidateJobMatch.candidate_id
            == candidate_id,
            CandidateJobMatch.job_id == job_id,
        )
    )

    assert resume_content_count == 1
    assert resume_profile_count == 1
    assert job_profile_count == 1
    assert match_count == 1


def assert_completed_evaluation(
    body: dict[str, object],
    *,
    candidate_id: UUID,
    job_id: UUID,
    resume_id: UUID,
) -> None:
    assert body["status"] == "completed"
    assert body["candidate_id"] == str(
        candidate_id
    )
    assert body["job_id"] == str(job_id)
    assert body["resume_id"] == str(resume_id)
    assert body["evaluated_at"] is not None

    resume_content = body["resume_content"]
    assert isinstance(resume_content, dict)

    assert (
        resume_content["extraction_status"]
        == "completed"
    )
    assert resume_content["extraction_error"] is None
    assert resume_content["extracted_text"]
    assert (
        "Harsha Vardhan"
        in str(resume_content["extracted_text"])
    )

    resume_profile = body["resume_profile"]
    assert isinstance(resume_profile, dict)

    assert (
        resume_profile["parsing_status"]
        == "completed"
    )
    assert resume_profile["parsing_error"] is None

    resume_profile_data = resume_profile[
        "profile_data"
    ]

    assert isinstance(
        resume_profile_data,
        dict,
    )
    assert (
        resume_profile_data["full_name"]
        == "Harsha Vardhan"
    )
    assert resume_profile_data["skills"]
    assert (
        resume_profile_data[
            "total_experience_months"
        ]
        >= 12
    )

    job_profile = body[
        "job_requirement_profile"
    ]
    assert isinstance(job_profile, dict)

    assert (
        job_profile["parsing_status"]
        == "completed"
    )
    assert job_profile["parsing_error"] is None

    job_profile_data = job_profile[
        "profile_data"
    ]

    assert isinstance(job_profile_data, dict)
    assert (
        job_profile_data["job_title"]
        is not None
    )
    assert job_profile_data["required_skills"]

    candidate_job_match = body[
        "candidate_job_match"
    ]
    assert isinstance(
        candidate_job_match,
        dict,
    )

    assert (
        candidate_job_match["candidate_id"]
        == str(candidate_id)
    )
    assert (
        candidate_job_match["job_id"]
        == str(job_id)
    )
    assert (
        candidate_job_match["resume_id"]
        == str(resume_id)
    )

    overall_score = float(
        candidate_job_match["overall_score"]
    )

    assert 0.0 <= overall_score <= 100.0
    assert (
        candidate_job_match["recommendation"]
        in VALID_RECOMMENDATIONS
    )
    assert isinstance(
        candidate_job_match["analysis_data"],
        dict,
    )


def pipeline_record_ids(
    body: dict[str, object],
) -> dict[str, str]:
    resume_content = body["resume_content"]
    resume_profile = body["resume_profile"]
    job_profile = body[
        "job_requirement_profile"
    ]
    candidate_job_match = body[
        "candidate_job_match"
    ]

    assert isinstance(resume_content, dict)
    assert isinstance(resume_profile, dict)
    assert isinstance(job_profile, dict)
    assert isinstance(
        candidate_job_match,
        dict,
    )

    return {
        "resume_content": str(
            resume_content["id"]
        ),
        "resume_profile": str(
            resume_profile["id"]
        ),
        "job_requirement_profile": str(
            job_profile["id"]
        ),
        "candidate_job_match": str(
            candidate_job_match["id"]
        ),
    }


def test_real_candidate_evaluation_processes_reuses_and_forces(
    client: TestClient,
    db_session: Session,
) -> None:
    uploaded_resume: dict[str, object] | None = None

    try:
        job = create_job_through_api(client)
        candidate = create_candidate_through_api(
            client
        )

        candidate_id = UUID(
            str(candidate["id"])
        )
        job_id = UUID(str(job["id"]))

        uploaded_resume = (
            upload_primary_resume_through_api(
                client,
                candidate_id=candidate_id,
            )
        )

        resume_id = UUID(
            str(uploaded_resume["id"])
        )

        url = evaluation_url(
            candidate_id=candidate_id,
            job_id=job_id,
        )

        first_response = client.post(url)

        assert (
            first_response.status_code == 200
        ), first_response.text

        first_body = first_response.json()

        assert first_body["force"] is False
        assert first_body["stages"] == {
            "resume_content": "processed",
            "resume_profile": "processed",
            "job_requirement_profile": (
                "processed"
            ),
            "candidate_job_match": "processed",
        }

        assert_completed_evaluation(
            first_body,
            candidate_id=candidate_id,
            job_id=job_id,
            resume_id=resume_id,
        )

        first_ids = pipeline_record_ids(
            first_body
        )

        (
            persisted_content,
            persisted_resume_profile,
            persisted_job_profile,
            persisted_match,
        ) = get_persisted_pipeline(
            db_session,
            candidate_id=candidate_id,
            job_id=job_id,
            resume_id=resume_id,
        )

        assert str(persisted_content.id) == (
            first_ids["resume_content"]
        )
        assert str(
            persisted_resume_profile.id
        ) == first_ids["resume_profile"]
        assert str(
            persisted_job_profile.id
        ) == first_ids[
            "job_requirement_profile"
        ]
        assert str(persisted_match.id) == (
            first_ids["candidate_job_match"]
        )

        assert_single_pipeline_rows(
            db_session,
            candidate_id=candidate_id,
            job_id=job_id,
            resume_id=resume_id,
        )

        second_response = client.post(url)

        assert (
            second_response.status_code == 200
        ), second_response.text

        second_body = second_response.json()

        assert second_body["force"] is False
        assert second_body["stages"] == {
            "resume_content": "reused",
            "resume_profile": "reused",
            "job_requirement_profile": (
                "reused"
            ),
            "candidate_job_match": "reused",
        }

        assert pipeline_record_ids(
            second_body
        ) == first_ids

        forced_response = client.post(
            url,
            params={
                "force": "true",
            },
        )

        assert (
            forced_response.status_code == 200
        ), forced_response.text

        forced_body = forced_response.json()

        assert forced_body["force"] is True
        assert forced_body["stages"] == {
            "resume_content": "processed",
            "resume_profile": "processed",
            "job_requirement_profile": (
                "processed"
            ),
            "candidate_job_match": "processed",
        }

        assert pipeline_record_ids(
            forced_body
        ) == first_ids

        assert_completed_evaluation(
            forced_body,
            candidate_id=candidate_id,
            job_id=job_id,
            resume_id=resume_id,
        )

        assert_single_pipeline_rows(
            db_session,
            candidate_id=candidate_id,
            job_id=job_id,
            resume_id=resume_id,
        )

    finally:
        remove_uploaded_file(uploaded_resume)


def test_real_candidate_evaluation_requires_primary_resume(
    client: TestClient,
    db_session: Session,
) -> None:
    job = create_job_through_api(client)
    candidate = create_candidate_through_api(
        client
    )

    candidate_id = UUID(str(candidate["id"]))
    job_id = UUID(str(job["id"]))

    response = client.post(
        evaluation_url(
            candidate_id=candidate_id,
            job_id=job_id,
        )
    )

    assert response.status_code == 409
    assert response.json() == {
        "error": {
            "code": "primary_resume_not_found",
            "message": (
                "The candidate must have an explicitly "
                "selected primary Resume before matching."
            ),
            "details": None,
        }
    }

    db_session.expire_all()

    job_profile = db_session.scalar(
        select(JobRequirementProfile).where(
            JobRequirementProfile.job_id == job_id
        )
    )

    candidate_job_match = db_session.scalar(
        select(CandidateJobMatch).where(
            CandidateJobMatch.candidate_id
            == candidate_id,
            CandidateJobMatch.job_id == job_id,
        )
    )

    assert job_profile is None
    assert candidate_job_match is None


def test_real_candidate_evaluation_reprocesses_stale_job_only(
    client: TestClient,
    db_session: Session,
) -> None:
    uploaded_resume: dict[str, object] | None = None

    try:
        job = create_job_through_api(client)
        candidate = create_candidate_through_api(
            client
        )

        candidate_id = UUID(
            str(candidate["id"])
        )
        job_id = UUID(str(job["id"]))

        uploaded_resume = (
            upload_primary_resume_through_api(
                client,
                candidate_id=candidate_id,
            )
        )

        resume_id = UUID(
            str(uploaded_resume["id"])
        )

        url = evaluation_url(
            candidate_id=candidate_id,
            job_id=job_id,
        )

        first_response = client.post(url)

        assert (
            first_response.status_code == 200
        ), first_response.text

        first_body = first_response.json()
        first_ids = pipeline_record_ids(
            first_body
        )

        first_job_profile = first_body[
            "job_requirement_profile"
        ]
        first_match = first_body[
            "candidate_job_match"
        ]

        assert isinstance(
            first_job_profile,
            dict,
        )
        assert isinstance(first_match, dict)

        first_job_hash = first_job_profile[
            "source_description_sha256"
        ]

        update_response = client.patch(
            f"{JOBS_URL}/{job_id}",
            json={
                "description": (
                    updated_job_description()
                ),
            },
        )

        assert (
            update_response.status_code == 200
        ), update_response.text

        second_response = client.post(url)

        assert (
            second_response.status_code == 200
        ), second_response.text

        second_body = second_response.json()

        assert second_body["stages"] == {
            "resume_content": "reused",
            "resume_profile": "reused",
            "job_requirement_profile": (
                "processed"
            ),
            "candidate_job_match": "processed",
        }

        second_ids = pipeline_record_ids(
            second_body
        )

        assert (
            second_ids["resume_content"]
            == first_ids["resume_content"]
        )
        assert (
            second_ids["resume_profile"]
            == first_ids["resume_profile"]
        )
        assert (
            second_ids[
                "job_requirement_profile"
            ]
            == first_ids[
                "job_requirement_profile"
            ]
        )
        assert (
            second_ids["candidate_job_match"]
            == first_ids["candidate_job_match"]
        )

        second_job_profile = second_body[
            "job_requirement_profile"
        ]
        second_match = second_body[
            "candidate_job_match"
        ]

        assert isinstance(
            second_job_profile,
            dict,
        )
        assert isinstance(second_match, dict)

        second_job_hash = second_job_profile[
            "source_description_sha256"
        ]

        assert second_job_hash != first_job_hash

        assert (
            second_match[
                "source_job_description_sha256"
            ]
            == second_job_hash
        )

        assert_completed_evaluation(
            second_body,
            candidate_id=candidate_id,
            job_id=job_id,
            resume_id=resume_id,
        )

        assert_single_pipeline_rows(
            db_session,
            candidate_id=candidate_id,
            job_id=job_id,
            resume_id=resume_id,
        )

    finally:
        remove_uploaded_file(uploaded_resume)