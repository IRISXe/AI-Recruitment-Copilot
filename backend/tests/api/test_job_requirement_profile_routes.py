from datetime import UTC, datetime
from unittest.mock import patch
from uuid import UUID, uuid4

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.core.exceptions import AppException
from app.models.job_requirement_profile import (
    JobRequirementProfile,
)
from app.parsing.job_description_parser import (
    PARSER_VERSION,
)
from app.schemas.job_requirement_profile import (
    JobRequirementProfileData,
)


JOBS_URL = "/api/v1/jobs"


def build_completed_job_requirement_profile(
    *,
    job_id: UUID,
) -> JobRequirementProfile:
    timestamp = datetime(
        2026,
        7,
        24,
        12,
        0,
        tzinfo=UTC,
    )

    profile_data = JobRequirementProfileData(
        job_title="Frontend Engineer",
        location="Hyderabad",
        work_mode="hybrid",
        required_skills=[
            "React",
            "TypeScript",
            "REST APIs",
        ],
        preferred_skills=[
            "AWS",
            "Docker",
        ],
        minimum_experience_years=2,
        confidence=0.90,
    )

    return JobRequirementProfile(
        id=uuid4(),
        job_id=job_id,
        profile_data=profile_data.model_dump(
            mode="json"
        ),
        parsing_status="completed",
        parsing_error=None,
        parser_version=PARSER_VERSION,
        source_description_sha256="a" * 64,
        parsed_at=timestamp,
        created_at=timestamp,
        updated_at=timestamp,
    )


def test_parse_job_requirement_profile_returns_completed_profile(
    client: TestClient,
) -> None:
    job_id = uuid4()

    profile = build_completed_job_requirement_profile(
        job_id=job_id
    )

    with patch(
        "app.api.routes.job_requirement_profiles."
        "parse_profile_service",
        return_value=profile,
    ) as parse_service:
        response = client.post(
            f"{JOBS_URL}/{job_id}/parse-requirements"
        )

    assert response.status_code == 200

    parse_service.assert_called_once()

    assert parse_service.call_args.args[0] is not None

    assert parse_service.call_args.kwargs == {
        "job_id": job_id,
        "force": False,
    }

    body = response.json()

    assert body["id"] == str(profile.id)
    assert body["job_id"] == str(job_id)
    assert body["parsing_status"] == "completed"
    assert body["parsing_error"] is None
    assert body["parser_version"] == PARSER_VERSION

    assert (
        body["source_description_sha256"]
        == "a" * 64
    )

    assert body["profile_data"]["job_title"] == (
        "Frontend Engineer"
    )
    assert body["profile_data"]["location"] == (
        "Hyderabad"
    )
    assert body["profile_data"]["work_mode"] == (
        "hybrid"
    )

    assert body["profile_data"]["required_skills"] == [
        "React",
        "TypeScript",
        "REST APIs",
    ]

    assert body["profile_data"]["preferred_skills"] == [
        "AWS",
        "Docker",
    ]

    assert (
        body["profile_data"]["minimum_experience_years"]
        == 2
    )
    assert body["profile_data"]["confidence"] == 0.9

    assert body["parsed_at"] is not None
    assert body["created_at"] is not None
    assert body["updated_at"] is not None


def test_parse_job_requirement_profile_accepts_force_true(
    client: TestClient,
) -> None:
    job_id = uuid4()

    profile = build_completed_job_requirement_profile(
        job_id=job_id
    )

    with patch(
        "app.api.routes.job_requirement_profiles."
        "parse_profile_service",
        return_value=profile,
    ) as parse_service:
        response = client.post(
            f"{JOBS_URL}/{job_id}/parse-requirements",
            params={
                "force": "true",
            },
        )

    assert response.status_code == 200

    parse_service.assert_called_once()

    assert parse_service.call_args.kwargs == {
        "job_id": job_id,
        "force": True,
    }


def test_get_job_requirement_profile_returns_profile(
    client: TestClient,
) -> None:
    job_id = uuid4()

    profile = build_completed_job_requirement_profile(
        job_id=job_id
    )

    with patch(
        "app.api.routes.job_requirement_profiles."
        "get_profile_service",
        return_value=profile,
    ) as get_service:
        response = client.get(
            f"{JOBS_URL}/{job_id}/requirement-profile"
        )

    assert response.status_code == 200

    get_service.assert_called_once()

    assert get_service.call_args.args[0] is not None
    assert get_service.call_args.args[1] == job_id

    body = response.json()

    assert body["id"] == str(profile.id)
    assert body["job_id"] == str(job_id)
    assert body["parsing_status"] == "completed"
    assert body["profile_data"]["job_title"] == (
        "Frontend Engineer"
    )


@pytest.mark.parametrize(
    (
        "method",
        "url",
        "expected_location",
    ),
    [
        (
            "post",
            (
                f"{JOBS_URL}/not-a-valid-uuid/"
                "parse-requirements"
            ),
            [
                "path",
                "job_id",
            ],
        ),
        (
            "get",
            (
                f"{JOBS_URL}/not-a-valid-uuid/"
                "requirement-profile"
            ),
            [
                "path",
                "job_id",
            ],
        ),
    ],
)
def test_job_requirement_profile_routes_reject_malformed_uuid(
    client: TestClient,
    method: str,
    url: str,
    expected_location: list[str],
) -> None:
    with (
        patch(
            "app.api.routes.job_requirement_profiles."
            "parse_profile_service",
        ) as parse_service,
        patch(
            "app.api.routes.job_requirement_profiles."
            "get_profile_service",
        ) as get_service,
    ):
        request_method = getattr(
            client,
            method,
        )

        response = request_method(url)

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

    parse_service.assert_not_called()
    get_service.assert_not_called()


def test_parse_job_requirement_profile_rejects_invalid_force(
    client: TestClient,
) -> None:
    job_id = uuid4()

    with patch(
        "app.api.routes.job_requirement_profiles."
        "parse_profile_service",
    ) as parse_service:
        response = client.post(
            f"{JOBS_URL}/{job_id}/parse-requirements",
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

    parse_service.assert_not_called()


@pytest.mark.parametrize(
    (
        "expected_status",
        "expected_code",
        "expected_message",
    ),
    [
        (
            status.HTTP_404_NOT_FOUND,
            "job_not_found",
            "The requested job does not exist.",
        ),
        (
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "job_description_empty",
            (
                "The job description is empty and "
                "cannot be processed."
            ),
        ),
        (
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "job_description_parsing_failed",
            (
                "The job description could not be parsed "
                "into structured requirements."
            ),
        ),
        (
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "job_requirement_profile_persistence_failed",
            (
                "The structured job requirement profile "
                "could not be saved."
            ),
        ),
    ],
)
def test_parse_job_requirement_profile_returns_service_error(
    client: TestClient,
    expected_status: int,
    expected_code: str,
    expected_message: str,
) -> None:
    job_id = uuid4()

    with patch(
        "app.api.routes.job_requirement_profiles."
        "parse_profile_service",
        side_effect=AppException(
            status_code=expected_status,
            code=expected_code,
            message=expected_message,
        ),
    ) as parse_service:
        response = client.post(
            f"{JOBS_URL}/{job_id}/parse-requirements"
        )

    assert response.status_code == expected_status

    assert response.json() == {
        "error": {
            "code": expected_code,
            "message": expected_message,
            "details": None,
        }
    }

    parse_service.assert_called_once()

    assert parse_service.call_args.kwargs == {
        "job_id": job_id,
        "force": False,
    }


@pytest.mark.parametrize(
    (
        "expected_status",
        "expected_code",
        "expected_message",
    ),
    [
        (
            status.HTTP_404_NOT_FOUND,
            "job_not_found",
            "The requested job does not exist.",
        ),
        (
            status.HTTP_404_NOT_FOUND,
            "job_requirement_profile_not_found",
            (
                "A structured requirement profile is not "
                "available for this job."
            ),
        ),
        (
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "job_requirement_profile_retrieval_failed",
            (
                "The structured job requirement profile "
                "could not be retrieved."
            ),
        ),
    ],
)
def test_get_job_requirement_profile_returns_service_error(
    client: TestClient,
    expected_status: int,
    expected_code: str,
    expected_message: str,
) -> None:
    job_id = uuid4()

    with patch(
        "app.api.routes.job_requirement_profiles."
        "get_profile_service",
        side_effect=AppException(
            status_code=expected_status,
            code=expected_code,
            message=expected_message,
        ),
    ) as get_service:
        response = client.get(
            f"{JOBS_URL}/{job_id}/requirement-profile"
        )

    assert response.status_code == expected_status

    assert response.json() == {
        "error": {
            "code": expected_code,
            "message": expected_message,
            "details": None,
        }
    }

    get_service.assert_called_once()

    assert get_service.call_args.args[1] == job_id