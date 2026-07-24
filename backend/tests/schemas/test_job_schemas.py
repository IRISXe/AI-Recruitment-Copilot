from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.job import (
    JobCreate,
    JobResponse,
    JobUpdate,
)


JOB_DESCRIPTION = (
    "We are looking for a Backend Engineer with "
    "Python, FastAPI, PostgreSQL, and Docker experience."
)


def valid_job_data() -> dict[str, object]:
    return {
        "title": "Backend Engineer",
        "description": JOB_DESCRIPTION,
        "department": "Engineering",
        "location": "Hyderabad",
        "employment_type": "full_time",
        "minimum_experience": 2,
        "required_skills": [
            "Python",
            "FastAPI",
        ],
        "preferred_skills": [
            "PostgreSQL",
        ],
    }


def test_job_create_accepts_valid_data() -> None:
    job = JobCreate(**valid_job_data())

    assert job.title == "Backend Engineer"
    assert job.description == JOB_DESCRIPTION
    assert job.department == "Engineering"
    assert job.location == "Hyderabad"
    assert job.employment_type == "full_time"
    assert job.minimum_experience == 2
    assert job.required_skills == [
        "Python",
        "FastAPI",
    ]
    assert job.preferred_skills == [
        "PostgreSQL",
    ]


def test_job_create_allows_missing_description() -> None:
    data = valid_job_data()
    data.pop("description")

    job = JobCreate(**data)

    assert job.description is None


def test_job_create_strips_surrounding_whitespace() -> None:
    data = valid_job_data()
    data["title"] = "  Backend Engineer  "
    data["description"] = (
        "  Backend engineering position.  "
    )
    data["department"] = "  Engineering  "
    data["location"] = "  Hyderabad  "

    job = JobCreate(**data)

    assert job.title == "Backend Engineer"
    assert (
        job.description
        == "Backend engineering position."
    )
    assert job.department == "Engineering"
    assert job.location == "Hyderabad"


def test_job_create_defaults_preferred_skills_to_empty_list(
) -> None:
    data = valid_job_data()
    data.pop("preferred_skills")

    job = JobCreate(**data)

    assert job.preferred_skills == []


@pytest.mark.parametrize(
    (
        "field_name",
        "invalid_value",
    ),
    [
        (
            "employment_type",
            "temporary",
        ),
        (
            "minimum_experience",
            -1,
        ),
        (
            "minimum_experience",
            51,
        ),
        (
            "required_skills",
            [],
        ),
        (
            "description",
            "   ",
        ),
    ],
)
def test_job_create_rejects_invalid_values(
    field_name: str,
    invalid_value: object,
) -> None:
    data = valid_job_data()
    data[field_name] = invalid_value

    with pytest.raises(ValidationError):
        JobCreate(**data)


def test_job_update_accepts_partial_update() -> None:
    update = JobUpdate(
        title="  Senior Backend Engineer  ",
        minimum_experience=4,
    )

    assert update.model_dump(
        exclude_unset=True,
    ) == {
        "title": "Senior Backend Engineer",
        "minimum_experience": 4,
    }


def test_job_update_accepts_description_update() -> None:
    description = (
        "We are hiring a Senior Frontend Engineer "
        "with React and TypeScript experience."
    )

    update = JobUpdate(
        description=description,
    )

    assert update.model_dump(
        exclude_unset=True,
    ) == {
        "description": description,
    }


def test_job_update_strips_description_whitespace() -> None:
    update = JobUpdate(
        description=(
            "  Updated job description.  "
        ),
    )

    assert update.description == (
        "Updated job description."
    )


def test_job_update_rejects_blank_description() -> None:
    with pytest.raises(ValidationError):
        JobUpdate(
            description="   ",
        )


def test_job_update_rejects_empty_body() -> None:
    with pytest.raises(
        ValidationError,
        match=(
            "At least one field must be "
            "provided for update"
        ),
    ):
        JobUpdate()


def test_job_update_rejects_explicit_null() -> None:
    with pytest.raises(
        ValidationError,
        match="Updated fields cannot be null: title",
    ):
        JobUpdate(
            title=None,
        )


def test_job_update_rejects_null_description() -> None:
    with pytest.raises(
        ValidationError,
        match=(
            "Updated fields cannot be null: "
            "description"
        ),
    ):
        JobUpdate(
            description=None,
        )


def test_job_update_allows_clearing_preferred_skills(
) -> None:
    update = JobUpdate(
        preferred_skills=[],
    )

    assert update.model_dump(
        exclude_unset=True,
    ) == {
        "preferred_skills": [],
    }


def test_job_response_serializes_attribute_object() -> None:
    job_id = uuid4()
    created_at = datetime.now(UTC)
    updated_at = datetime.now(UTC)

    orm_like_job = SimpleNamespace(
        id=job_id,
        title="Backend Engineer",
        description=JOB_DESCRIPTION,
        department="Engineering",
        location="Hyderabad",
        employment_type="full_time",
        minimum_experience=2,
        required_skills=[
            "Python",
            "FastAPI",
        ],
        preferred_skills=[
            "PostgreSQL",
        ],
        created_at=created_at,
        updated_at=updated_at,
    )

    response = JobResponse.model_validate(
        orm_like_job
    )

    assert response.id == job_id
    assert response.title == "Backend Engineer"
    assert response.description == JOB_DESCRIPTION
    assert response.created_at == created_at
    assert response.updated_at == updated_at