from datetime import datetime
from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


EmploymentType = Literal[
    "full_time",
    "part_time",
    "contract",
    "internship",
]


class JobValidationRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(
        min_length=2,
        max_length=100,
        examples=["Frontend Developer"],
    )
    department: str = Field(
        min_length=2,
        max_length=100,
        examples=["Engineering"],
    )
    location: str = Field(
        min_length=2,
        max_length=100,
        examples=["Hyderabad"],
    )
    employment_type: EmploymentType
    minimum_experience: int = Field(
        ge=0,
        le=50,
        examples=[2],
    )
    required_skills: list[str] = Field(
        min_length=1,
        max_length=20,
        examples=[["React", "TypeScript", "REST APIs"]],
    )
    preferred_skills: list[str] = Field(
        default_factory=list,
        max_length=20,
    )


class JobCreate(JobValidationRequest):
    pass


class JobUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str | None = Field(
        default=None,
        min_length=2,
        max_length=100,
        examples=["Senior Frontend Developer"],
    )
    department: str | None = Field(
        default=None,
        min_length=2,
        max_length=100,
        examples=["Engineering"],
    )
    location: str | None = Field(
        default=None,
        min_length=2,
        max_length=100,
        examples=["Bengaluru"],
    )
    employment_type: EmploymentType | None = None
    minimum_experience: int | None = Field(
        default=None,
        ge=0,
        le=50,
        examples=[3],
    )
    required_skills: list[str] | None = Field(
        default=None,
        min_length=1,
        max_length=20,
        examples=[["React", "TypeScript"]],
    )
    preferred_skills: list[str] | None = Field(
        default=None,
        max_length=20,
    )

    @model_validator(mode="after")
    def validate_update_fields(self) -> Self:
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided for update.")

        null_fields = [
            field_name
            for field_name in self.model_fields_set
            if getattr(self, field_name) is None
        ]

        if null_fields:
            fields = ", ".join(sorted(null_fields))
            raise ValueError(
                f"Updated fields cannot be null: {fields}."
            )

        return self


class JobResponse(JobValidationRequest):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        from_attributes=True,
    )

    id: UUID
    created_at: datetime
    updated_at: datetime


class JobValidationResponse(BaseModel):
    message: str
    job: JobValidationRequest