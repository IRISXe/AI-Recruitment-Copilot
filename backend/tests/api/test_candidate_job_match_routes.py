from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import patch
from uuid import UUID, uuid4

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.core.exceptions import AppException
from app.matching.candidate_job_matcher import (
    SCORING_VERSION,
)
from app.models.candidate_job_match import CandidateJobMatch


MATCHES_URL = "/api/v1/candidate-job-matches"


def build_candidate_job_match(
    *,
    candidate_id: UUID,
    job_id: UUID,
) -> CandidateJobMatch:
    timestamp = datetime(
        2026,
        7,
        24,
        12,
        0,
        tzinfo=UTC,
    )

    return CandidateJobMatch(
        id=uuid4(),
        candidate_id=candidate_id,
        job_id=job_id,
        resume_id=uuid4(),
        resume_profile_id=uuid4(),
        job_requirement_profile_id=uuid4(),
        overall_score=Decimal("88.50"),
        skill_score=Decimal("90.00"),
        experience_score=Decimal("85.00"),
        education_score=Decimal("80.00"),
        certification_score=Decimal("75.00"),
        location_score=Decimal("100.00"),
        work_mode_score=Decimal("90.00"),
        confidence_score=Decimal("84.00"),
        recommendation="strong_match",
        analysis_data={
            "matched_required_skills": [
                "React",
                "PostgreSQL",
            ],
            "missing_required_skills": [],
            "matched_preferred_skills": [
                "AWS",
            ],
            "missing_preferred_skills": [
                "Docker",
            ],
            "experience_analysis": (
                "The candidate meets the experience requirement."
            ),
            "location_analysis": (
                "Bangalore and Bengaluru were treated as equivalent."
            ),
            "strengths": [
                "Strong required-skill alignment.",
            ],
            "gaps": [
                "Docker was not found.",
            ],
        },
        scoring_version=SCORING_VERSION,
        source_resume_text_sha256="a" * 64,
        source_resume_parser_version="resume-parser-v1",
        source_job_description_sha256="b" * 64,
        source_job_parser_version="job-parser-v1",
        matched_at=timestamp,
        created_at=timestamp,
        updated_at=timestamp,
    )


def test_generate_candidate_job_match_returns_match(
    client: TestClient,
) -> None:
    candidate_id = uuid4()
    job_id = uuid4()

    candidate_job_match = build_candidate_job_match(
        candidate_id=candidate_id,
        job_id=job_id,
    )

    with patch(
        "app.api.routes.candidate_job_matches."
        "generate_match_service",
        return_value=candidate_job_match,
    ) as generate_service:
        response = client.post(
            f"{MATCHES_URL}/candidates/"
            f"{candidate_id}/jobs/{job_id}"
        )

    assert response.status_code == 200

    generate_service.assert_called_once()

    call_args = generate_service.call_args

    assert call_args.kwargs == {
        "candidate_id": candidate_id,
        "job_id": job_id,
        "force": False,
    }
    assert call_args.args[0] is not None

    body = response.json()

    assert body["id"] == str(candidate_job_match.id)
    assert body["candidate_id"] == str(candidate_id)
    assert body["job_id"] == str(job_id)

    assert body["resume_id"] == str(
        candidate_job_match.resume_id
    )
    assert body["resume_profile_id"] == str(
        candidate_job_match.resume_profile_id
    )
    assert body["job_requirement_profile_id"] == str(
        candidate_job_match.job_requirement_profile_id
    )

    assert body["overall_score"] == 88.5
    assert body["skill_score"] == 90.0
    assert body["confidence_score"] == 84.0
    assert body["recommendation"] == "strong_match"
    assert body["scoring_version"] == SCORING_VERSION

    assert body["analysis_data"][
        "matched_required_skills"
    ] == [
        "React",
        "PostgreSQL",
    ]

    assert body["analysis_data"]["gaps"] == [
        "Docker was not found.",
    ]

    assert body["matched_at"] is not None
    assert body["created_at"] is not None
    assert body["updated_at"] is not None


def test_generate_candidate_job_match_accepts_force_true(
    client: TestClient,
) -> None:
    candidate_id = uuid4()
    job_id = uuid4()

    candidate_job_match = build_candidate_job_match(
        candidate_id=candidate_id,
        job_id=job_id,
    )

    with patch(
        "app.api.routes.candidate_job_matches."
        "generate_match_service",
        return_value=candidate_job_match,
    ) as generate_service:
        response = client.post(
            f"{MATCHES_URL}/candidates/"
            f"{candidate_id}/jobs/{job_id}",
            params={
                "force": "true",
            },
        )

    assert response.status_code == 200

    generate_service.assert_called_once()

    assert generate_service.call_args.kwargs == {
        "candidate_id": candidate_id,
        "job_id": job_id,
        "force": True,
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
def test_generate_candidate_job_match_rejects_malformed_uuid(
    client: TestClient,
    candidate_id: str,
    job_id: str,
    expected_location: list[str],
) -> None:
    with patch(
        "app.api.routes.candidate_job_matches."
        "generate_match_service",
    ) as generate_service:
        response = client.post(
            f"{MATCHES_URL}/candidates/"
            f"{candidate_id}/jobs/{job_id}"
        )

    assert response.status_code == 422

    assert (
        response.json()["error"]["code"]
        == "validation_error"
    )

    details = response.json()["error"]["details"]

    assert any(
        detail["loc"] == expected_location
        for detail in details
    )

    generate_service.assert_not_called()


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
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "candidate_job_match_persistence_failed",
            (
                "The Candidate–Job match could not be "
                "generated or saved."
            ),
        ),
    ],
)
def test_generate_candidate_job_match_returns_service_error(
    client: TestClient,
    expected_status: int,
    expected_code: str,
    expected_message: str,
) -> None:
    candidate_id = uuid4()
    job_id = uuid4()

    with patch(
        "app.api.routes.candidate_job_matches."
        "generate_match_service",
        side_effect=AppException(
            status_code=expected_status,
            code=expected_code,
            message=expected_message,
        ),
    ) as generate_service:
        response = client.post(
            f"{MATCHES_URL}/candidates/"
            f"{candidate_id}/jobs/{job_id}"
        )

    assert response.status_code == expected_status

    assert response.json() == {
        "error": {
            "code": expected_code,
            "message": expected_message,
            "details": None,
        }
    }

    generate_service.assert_called_once()

    assert generate_service.call_args.kwargs == {
        "candidate_id": candidate_id,
        "job_id": job_id,
        "force": False,
    }