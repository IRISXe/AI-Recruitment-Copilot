from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from unittest.mock import patch

from app.core.exceptions import AppException
from app.matching.candidate_job_matcher import (
    SCORING_VERSION,
)
from app.parsing.job_description_parser import (
    PARSER_VERSION as JOB_PARSER_VERSION,
)
from app.parsing.resume_parser import (
    PARSER_VERSION as RESUME_PARSER_VERSION,
)
from app.schemas.candidate_evaluation import (
    CandidateEvaluationResponse,
    CandidateEvaluationStages,
)
from app.schemas.candidate_job_match import (
    CandidateJobMatchResponse,
)
from app.schemas.job_requirement_profile import (
    JobRequirementProfileData,
    JobRequirementProfileResponse,
)
from app.schemas.resume_content import (
    ResumeContentResponse,
)
from app.schemas.resume_profile import (
    ResumeProfileData,
    ResumeProfileResponse,
)


def build_evaluation_response(
    *,
    force: bool = False,
) -> CandidateEvaluationResponse:
    candidate_id = uuid4()
    job_id = uuid4()
    resume_id = uuid4()
    timestamp = datetime(
        2026,
        7,
        24,
        12,
        0,
        tzinfo=UTC,
    )

    resume_profile_data = ResumeProfileData(
        full_name="Harsha Vardhan",
        location="Hyderabad",
        total_experience_months=24,
        skills=[
            "React.js",
            "TypeScript",
            "REST APIs",
        ],
        confidence=0.90,
    )

    job_profile_data = JobRequirementProfileData(
        job_title="Frontend Engineer",
        location="Hyderabad",
        work_mode="hybrid",
        required_skills=[
            "React",
            "TypeScript",
            "REST APIs",
        ],
        minimum_experience_years=2,
        confidence=0.90,
    )

    action = "processed" if force else "reused"

    return CandidateEvaluationResponse(
        candidate_id=candidate_id,
        job_id=job_id,
        resume_id=resume_id,
        force=force,
        evaluated_at=timestamp,
        stages=CandidateEvaluationStages(
            resume_content=action,
            resume_profile=action,
            job_requirement_profile=action,
            candidate_job_match=action,
        ),
        resume_content=ResumeContentResponse(
            id=uuid4(),
            resume_id=resume_id,
            extracted_text="React TypeScript REST APIs",
            extraction_status="completed",
            extraction_error=None,
            extractor_version="rule-based-v1",
            extracted_at=timestamp,
            created_at=timestamp,
            updated_at=timestamp,
        ),
        resume_profile=ResumeProfileResponse(
            id=uuid4(),
            resume_id=resume_id,
            profile_data=resume_profile_data,
            parsing_status="completed",
            parsing_error=None,
            parser_version=RESUME_PARSER_VERSION,
            source_text_sha256="a" * 64,
            parsed_at=timestamp,
            created_at=timestamp,
            updated_at=timestamp,
        ),
        job_requirement_profile=(
            JobRequirementProfileResponse(
                id=uuid4(),
                job_id=job_id,
                profile_data=job_profile_data,
                parsing_status="completed",
                parsing_error=None,
                parser_version=JOB_PARSER_VERSION,
                source_description_sha256="b" * 64,
                parsed_at=timestamp,
                created_at=timestamp,
                updated_at=timestamp,
            )
        ),
        candidate_job_match=CandidateJobMatchResponse(
            id=uuid4(),
            candidate_id=candidate_id,
            job_id=job_id,
            resume_id=resume_id,
            resume_profile_id=uuid4(),
            job_requirement_profile_id=uuid4(),
            overall_score=88.5,
            skill_score=90.0,
            experience_score=85.0,
            education_score=80.0,
            certification_score=75.0,
            location_score=100.0,
            work_mode_score=90.0,
            confidence_score=90.0,
            recommendation="strong_match",
            analysis_data={},
            scoring_version=SCORING_VERSION,
            source_resume_text_sha256="a" * 64,
            source_resume_parser_version=(
                RESUME_PARSER_VERSION
            ),
            source_job_description_sha256="b" * 64,
            source_job_parser_version=(
                JOB_PARSER_VERSION
            ),
            matched_at=timestamp,
            created_at=timestamp,
            updated_at=timestamp,
        ),
    )


def test_evaluate_candidate_returns_completed_evaluation(
    client: TestClient,
) -> None:
    evaluation = build_evaluation_response()

    with patch(
        "app.api.routes.candidate_evaluations."
        "evaluate_candidate_service",
        return_value=evaluation,
    ) as evaluate_service:
        response = client.post(
            f"/api/v1/candidates/"
            f"{evaluation.candidate_id}/jobs/"
            f"{evaluation.job_id}/evaluate"
        )

    assert response.status_code == 200

    evaluate_service.assert_called_once()

    assert evaluate_service.call_args.kwargs == {
        "candidate_id": evaluation.candidate_id,
        "job_id": evaluation.job_id,
        "force": False,
    }
    assert evaluate_service.call_args.args[0] is not None

    body = response.json()

    assert body["status"] == "completed"
    assert body["candidate_id"] == str(
        evaluation.candidate_id
    )
    assert body["job_id"] == str(evaluation.job_id)
    assert body["resume_id"] == str(
        evaluation.resume_id
    )
    assert body["force"] is False

    assert body["stages"] == {
        "resume_content": "reused",
        "resume_profile": "reused",
        "job_requirement_profile": "reused",
        "candidate_job_match": "reused",
    }

    assert (
        body["resume_content"]["extraction_status"]
        == "completed"
    )
    assert (
        body["resume_profile"]["parsing_status"]
        == "completed"
    )
    assert (
        body["job_requirement_profile"][
            "parsing_status"
        ]
        == "completed"
    )
    assert (
        body["candidate_job_match"]["overall_score"]
        == 88.5
    )
    assert (
        body["candidate_job_match"]["recommendation"]
        == "strong_match"
    )


def test_evaluate_candidate_accepts_force_true(
    client: TestClient,
) -> None:
    evaluation = build_evaluation_response(
        force=True
    )

    with patch(
        "app.api.routes.candidate_evaluations."
        "evaluate_candidate_service",
        return_value=evaluation,
    ) as evaluate_service:
        response = client.post(
            f"/api/v1/candidates/"
            f"{evaluation.candidate_id}/jobs/"
            f"{evaluation.job_id}/evaluate",
            params={
                "force": "true",
            },
        )

    assert response.status_code == 200

    assert evaluate_service.call_args.kwargs == {
        "candidate_id": evaluation.candidate_id,
        "job_id": evaluation.job_id,
        "force": True,
    }

    assert response.json()["force"] is True

    assert response.json()["stages"] == {
        "resume_content": "processed",
        "resume_profile": "processed",
        "job_requirement_profile": "processed",
        "candidate_job_match": "processed",
    }


@pytest.mark.parametrize(
    (
        "candidate_id",
        "job_id",
        "expected_location",
    ),
    [
        (
            "not-a-valid-uuid",
            str(uuid4()),
            [
                "path",
                "candidate_id",
            ],
        ),
        (
            str(uuid4()),
            "not-a-valid-uuid",
            [
                "path",
                "job_id",
            ],
        ),
    ],
)
def test_evaluate_candidate_rejects_malformed_uuid(
    client: TestClient,
    candidate_id: str,
    job_id: str,
    expected_location: list[str],
) -> None:
    with patch(
        "app.api.routes.candidate_evaluations."
        "evaluate_candidate_service",
    ) as evaluate_service:
        response = client.post(
            f"/api/v1/candidates/{candidate_id}/"
            f"jobs/{job_id}/evaluate"
        )

    assert response.status_code == 422
    assert (
        response.json()["error"]["code"]
        == "validation_error"
    )

    assert any(
        detail["loc"] == expected_location
        for detail in response.json()["error"]["details"]
    )

    evaluate_service.assert_not_called()


def test_evaluate_candidate_rejects_invalid_force(
    client: TestClient,
) -> None:
    candidate_id = uuid4()
    job_id = uuid4()

    with patch(
        "app.api.routes.candidate_evaluations."
        "evaluate_candidate_service",
    ) as evaluate_service:
        response = client.post(
            f"/api/v1/candidates/{candidate_id}/"
            f"jobs/{job_id}/evaluate",
            params={
                "force": "not-a-boolean",
            },
        )

    assert response.status_code == 422
    assert (
        response.json()["error"]["code"]
        == "validation_error"
    )

    assert any(
        detail["loc"] == [
            "query",
            "force",
        ]
        for detail in response.json()["error"]["details"]
    )

    evaluate_service.assert_not_called()


@pytest.mark.parametrize(
    (
        "expected_status",
        "expected_code",
        "expected_message",
    ),
    [
        (
            status.HTTP_404_NOT_FOUND,
            "candidate_not_found",
            "The requested candidate does not exist.",
        ),
        (
            status.HTTP_404_NOT_FOUND,
            "job_not_found",
            "The requested job does not exist.",
        ),
        (
            status.HTTP_409_CONFLICT,
            "primary_resume_not_found",
            (
                "The candidate must have an explicitly selected "
                "primary Resume before matching."
            ),
        ),
        (
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "resume_extraction_failed",
            "The Resume text could not be extracted.",
        ),
        (
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "candidate_evaluation_failed",
            (
                "The Candidate evaluation could not be "
                "completed."
            ),
        ),
    ],
)
def test_evaluate_candidate_returns_service_error(
    client: TestClient,
    expected_status: int,
    expected_code: str,
    expected_message: str,
) -> None:
    candidate_id = uuid4()
    job_id = uuid4()

    with patch(
        "app.api.routes.candidate_evaluations."
        "evaluate_candidate_service",
        side_effect=AppException(
            status_code=expected_status,
            code=expected_code,
            message=expected_message,
        ),
    ) as evaluate_service:
        response = client.post(
            f"/api/v1/candidates/{candidate_id}/"
            f"jobs/{job_id}/evaluate"
        )

    assert response.status_code == expected_status

    assert response.json() == {
        "error": {
            "code": expected_code,
            "message": expected_message,
            "details": None,
        }
    }

    evaluate_service.assert_called_once()

    assert evaluate_service.call_args.kwargs == {
        "candidate_id": candidate_id,
        "job_id": job_id,
        "force": False,
    }