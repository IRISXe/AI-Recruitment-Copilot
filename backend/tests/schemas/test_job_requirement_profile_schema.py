from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.job_requirement_profile import (
    JobRequirementProfileData,
    JobRequirementProfileResponse,
)


def test_profile_data_accepts_valid_requirements() -> None:
    profile = JobRequirementProfileData(
        job_title="Backend Engineer",
        employment_type="full_time",
        work_mode="hybrid",
        seniority_level="senior",
        required_skills=[
            "Python",
            "FastAPI",
        ],
        minimum_experience_years=3,
        maximum_experience_years=5,
        confidence=0.8,
    )

    assert profile.job_title == "Backend Engineer"
    assert profile.employment_type == "full_time"
    assert profile.work_mode == "hybrid"
    assert profile.seniority_level == "senior"
    assert profile.minimum_experience_years == 3
    assert profile.maximum_experience_years == 5
    assert profile.confidence == 0.8


def test_profile_data_normalizes_and_deduplicates_lists() -> None:
    profile = JobRequirementProfileData(
        required_skills=[
            "Python",
            " python ",
            "",
            "FastAPI",
            "FASTAPI",
        ],
        warnings=[
            "Missing education",
            " missing education ",
        ],
    )

    assert profile.required_skills == [
        "Python",
        "FastAPI",
    ]
    assert profile.warnings == [
        "Missing education",
    ]


def test_profile_data_rejects_invalid_experience_range() -> None:
    with pytest.raises(
        ValidationError,
        match=(
            "Maximum experience cannot be less than "
            "minimum experience"
        ),
    ):
        JobRequirementProfileData(
            minimum_experience_years=5,
            maximum_experience_years=3,
        )


@pytest.mark.parametrize(
    ("field_name", "invalid_value"),
    [
        ("minimum_experience_years", -1),
        ("minimum_experience_years", 51),
        ("maximum_experience_years", -1),
        ("maximum_experience_years", 51),
        ("confidence", -0.1),
        ("confidence", 1.1),
        ("employment_type", "temporary"),
        ("work_mode", "flexible"),
        ("seniority_level", "principal"),
    ],
)
def test_profile_data_rejects_invalid_values(
    field_name: str,
    invalid_value: object,
) -> None:
    with pytest.raises(ValidationError):
        JobRequirementProfileData(
            **{
                field_name: invalid_value,
            }
        )


def test_profile_response_serializes_attribute_object() -> None:
    profile_id = uuid4()
    job_id = uuid4()
    now = datetime.now(UTC)

    orm_like_profile = SimpleNamespace(
        id=profile_id,
        job_id=job_id,
        profile_data={
            "job_title": "Backend Engineer",
            "required_skills": [
                "Python",
                "FastAPI",
            ],
            "confidence": 0.5,
        },
        parsing_status="completed",
        parsing_error=None,
        parser_version="job-rule-based-v1",
        source_description_sha256="a" * 64,
        parsed_at=now,
        created_at=now,
        updated_at=now,
    )

    response = JobRequirementProfileResponse.model_validate(
        orm_like_profile
    )

    assert response.id == profile_id
    assert response.job_id == job_id
    assert response.parsing_status == "completed"
    assert response.profile_data is not None
    assert response.profile_data.job_title == "Backend Engineer"
    assert response.profile_data.required_skills == [
        "Python",
        "FastAPI",
    ]