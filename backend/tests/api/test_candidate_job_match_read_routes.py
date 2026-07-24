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
    overall_score: str = "88.50",
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
        overall_score=Decimal(overall_score),
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
            "strengths": [
                "Strong required-skill alignment.",
            ],
            "gaps": [],
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


def test_get_candidate_job_match_returns_match(
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
        "get_match_service",
        return_value=candidate_job_match,
    ) as get_service:
        response = client.get(
            f"{MATCHES_URL}/{candidate_job_match.id}"
        )

    assert response.status_code == 200

    get_service.assert_called_once()

    assert (
        get_service.call_args.args[1]
        == candidate_job_match.id
    )

    body = response.json()

    assert body["id"] == str(candidate_job_match.id)
    assert body["candidate_id"] == str(candidate_id)
    assert body["job_id"] == str(job_id)
    assert body["overall_score"] == 88.5
    assert body["recommendation"] == "strong_match"


def test_list_candidate_job_matches_uses_default_query_values(
    client: TestClient,
) -> None:
    with patch(
        "app.api.routes.candidate_job_matches."
        "list_matches_service",
        return_value=[],
    ) as list_service:
        response = client.get(
            MATCHES_URL
        )

    assert response.status_code == 200
    assert response.json() == []

    assert list_service.call_args.kwargs == {
        "offset": 0,
        "limit": 20,
        "candidate_id": None,
        "job_id": None,
        "minimum_score": None,
        "minimum_confidence": None,
        "recommendation": None,
        "sort_by": "overall_score",
        "sort_order": "desc",
    }


def test_list_candidate_job_matches_passes_filters(
    client: TestClient,
) -> None:
    candidate_id = uuid4()
    job_id = uuid4()

    matches = [
        build_candidate_job_match(
            candidate_id=candidate_id,
            job_id=job_id,
            overall_score="92.00",
        ),
        build_candidate_job_match(
            candidate_id=candidate_id,
            job_id=job_id,
            overall_score="80.00",
        ),
    ]

    with patch(
        "app.api.routes.candidate_job_matches."
        "list_matches_service",
        return_value=matches,
    ) as list_service:
        response = client.get(
            MATCHES_URL,
            params={
                "offset": 5,
                "limit": 10,
                "candidate_id": str(candidate_id),
                "job_id": str(job_id),
                "minimum_score": 70,
                "minimum_confidence": 60,
                "recommendation": "good_match",
                "sort_by": "confidence_score",
                "sort_order": "asc",
            },
        )

    assert response.status_code == 200

    assert list_service.call_args.kwargs == {
        "offset": 5,
        "limit": 10,
        "candidate_id": candidate_id,
        "job_id": job_id,
        "minimum_score": 70.0,
        "minimum_confidence": 60.0,
        "recommendation": "good_match",
        "sort_by": "confidence_score",
        "sort_order": "asc",
    }

    body = response.json()

    assert len(body) == 2
    assert body[0]["overall_score"] == 92.0
    assert body[1]["overall_score"] == 80.0


def test_list_candidate_matches_for_job(
    client: TestClient,
) -> None:
    job_id = uuid4()

    matches = [
        build_candidate_job_match(
            candidate_id=uuid4(),
            job_id=job_id,
        ),
    ]

    with patch(
        "app.api.routes.candidate_job_matches."
        "list_job_candidates_service",
        return_value=matches,
    ) as list_service:
        response = client.get(
            f"/api/v1/jobs/{job_id}/candidate-matches",
            params={
                "minimum_score": 75,
                "recommendation": "strong_match",
            },
        )

    assert response.status_code == 200

    assert list_service.call_args.kwargs == {
        "job_id": job_id,
        "offset": 0,
        "limit": 20,
        "minimum_score": 75.0,
        "minimum_confidence": None,
        "recommendation": "strong_match",
        "sort_by": "overall_score",
        "sort_order": "desc",
    }

    assert response.json()[0]["job_id"] == str(job_id)


def test_list_job_matches_for_candidate(
    client: TestClient,
) -> None:
    candidate_id = uuid4()

    matches = [
        build_candidate_job_match(
            candidate_id=candidate_id,
            job_id=uuid4(),
        ),
    ]

    with patch(
        "app.api.routes.candidate_job_matches."
        "list_candidate_jobs_service",
        return_value=matches,
    ) as list_service:
        response = client.get(
            f"/api/v1/candidates/{candidate_id}/job-matches"
        )

    assert response.status_code == 200

    assert list_service.call_args.kwargs == {
        "candidate_id": candidate_id,
        "offset": 0,
        "limit": 20,
        "minimum_score": None,
        "minimum_confidence": None,
        "recommendation": None,
        "sort_by": "overall_score",
        "sort_order": "desc",
    }

    assert (
        response.json()[0]["candidate_id"]
        == str(candidate_id)
    )


@pytest.mark.parametrize(
    (
        "url",
        "expected_location",
    ),
    [
        (
            f"{MATCHES_URL}/not-a-valid-uuid",
            [
                "path",
                "match_id",
            ],
        ),
        (
            "/api/v1/jobs/not-a-valid-uuid/candidate-matches",
            [
                "path",
                "job_id",
            ],
        ),
        (
            "/api/v1/candidates/not-a-valid-uuid/job-matches",
            [
                "path",
                "candidate_id",
            ],
        ),
    ],
)
def test_read_routes_reject_malformed_uuid(
    client: TestClient,
    url: str,
    expected_location: list[str],
) -> None:
    response = client.get(url)

    assert response.status_code == 422

    assert (
        response.json()["error"]["code"]
        == "validation_error"
    )

    assert any(
        detail["loc"] == expected_location
        for detail in response.json()["error"]["details"]
    )


@pytest.mark.parametrize(
    (
        "params",
        "expected_location",
    ),
    [
        (
            {
                "minimum_score": 101,
            },
            [
                "query",
                "minimum_score",
            ],
        ),
        (
            {
                "minimum_score": -1,
            },
            [
                "query",
                "minimum_score",
            ],
        ),
        (
            {
                "minimum_confidence": 101,
            },
            [
                "query",
                "minimum_confidence",
            ],
        ),
        (
            {
                "minimum_confidence": -1,
            },
            [
                "query",
                "minimum_confidence",
            ],
        ),
        (
            {
                "offset": -1,
            },
            [
                "query",
                "offset",
            ],
        ),
        (
            {
                "limit": 0,
            },
            [
                "query",
                "limit",
            ],
        ),
        (
            {
                "limit": 101,
            },
            [
                "query",
                "limit",
            ],
        ),
        (
            {
                "candidate_id": "not-a-valid-uuid",
            },
            [
                "query",
                "candidate_id",
            ],
        ),
        (
            {
                "job_id": "not-a-valid-uuid",
            },
            [
                "query",
                "job_id",
            ],
        ),
        (
            {
                "recommendation": "excellent_match",
            },
            [
                "query",
                "recommendation",
            ],
        ),
        (
            {
                "sort_by": "unknown",
            },
            [
                "query",
                "sort_by",
            ],
        ),
        (
            {
                "sort_order": "sideways",
            },
            [
                "query",
                "sort_order",
            ],
        ),
    ],
)
def test_list_candidate_job_matches_rejects_invalid_query(
    client: TestClient,
    params: dict[str, object],
    expected_location: list[str],
) -> None:
    with patch(
        "app.api.routes.candidate_job_matches."
        "list_matches_service",
    ) as list_service:
        response = client.get(
            MATCHES_URL,
            params=params,
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

    list_service.assert_not_called()


@pytest.mark.parametrize(
    (
        "url",
        "expected_status",
        "expected_code",
        "expected_message",
        "patch_target",
    ),
    [
        (
            f"{MATCHES_URL}/{uuid4()}",
            status.HTTP_404_NOT_FOUND,
            "candidate_job_match_not_found",
            (
                "The requested Candidate-Job match "
                "does not exist."
            ),
            "get_match_service",
        ),
        (
            f"/api/v1/jobs/{uuid4()}/candidate-matches",
            status.HTTP_404_NOT_FOUND,
            "job_not_found",
            "The requested job does not exist.",
            "list_job_candidates_service",
        ),
        (
            f"/api/v1/candidates/{uuid4()}/job-matches",
            status.HTTP_404_NOT_FOUND,
            "candidate_not_found",
            "The requested candidate does not exist.",
            "list_candidate_jobs_service",
        ),
        (
            MATCHES_URL,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "candidate_job_match_listing_failed",
            (
                "The Candidate-Job matches could not "
                "be retrieved."
            ),
            "list_matches_service",
        ),
    ],
)
def test_read_routes_return_service_error(
    client: TestClient,
    url: str,
    expected_status: int,
    expected_code: str,
    expected_message: str,
    patch_target: str,
) -> None:
    with patch(
        "app.api.routes.candidate_job_matches."
        f"{patch_target}",
        side_effect=AppException(
            status_code=expected_status,
            code=expected_code,
            message=expected_message,
        ),
    ):
        response = client.get(url)

    assert response.status_code == expected_status

    assert response.json() == {
        "error": {
            "code": expected_code,
            "message": expected_message,
            "details": None,
        }
    }