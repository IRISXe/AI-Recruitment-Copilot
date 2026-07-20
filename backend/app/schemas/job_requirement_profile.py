from datetime import datetime
from typing import Literal, Self
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from app.schemas.job import EmploymentType


JobRequirementParsingStatus = Literal[
    "pending",
    "completed",
    "failed",
]

JobWorkMode = Literal[
    "onsite",
    "remote",
    "hybrid",
]

JobSeniorityLevel = Literal[
    "intern",
    "entry",
    "junior",
    "mid",
    "senior",
    "lead",
    "manager",
    "director",
    "executive",
]


class JobRequirementProfileData(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    job_title: str | None = Field(
        default=None,
        max_length=200,
    )
    department: str | None = Field(
        default=None,
        max_length=200,
    )
    location: str | None = Field(
        default=None,
        max_length=300,
    )
    employment_type: EmploymentType | None = None
    work_mode: JobWorkMode | None = None
    seniority_level: JobSeniorityLevel | None = None

    summary: str | None = Field(
        default=None,
        max_length=5000,
    )

    responsibilities: list[str] = Field(
        default_factory=list,
        max_length=100,
    )

    required_skills: list[str] = Field(
        default_factory=list,
        max_length=100,
    )
    preferred_skills: list[str] = Field(
        default_factory=list,
        max_length=100,
    )

    minimum_experience_years: int | None = Field(
        default=None,
        ge=0,
        le=50,
    )
    maximum_experience_years: int | None = Field(
        default=None,
        ge=0,
        le=50,
    )

    required_education: list[str] = Field(
        default_factory=list,
        max_length=50,
    )
    preferred_education: list[str] = Field(
        default_factory=list,
        max_length=50,
    )

    required_certifications: list[str] = Field(
        default_factory=list,
        max_length=50,
    )
    preferred_certifications: list[str] = Field(
        default_factory=list,
        max_length=50,
    )

    keywords: list[str] = Field(
        default_factory=list,
        max_length=200,
    )

    warnings: list[str] = Field(
        default_factory=list,
        max_length=100,
    )
    missing_sections: list[str] = Field(
        default_factory=list,
        max_length=20,
    )
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
    )

    @field_validator(
        "responsibilities",
        "required_skills",
        "preferred_skills",
        "required_education",
        "preferred_education",
        "required_certifications",
        "preferred_certifications",
        "keywords",
        "warnings",
        "missing_sections",
    )
    @classmethod
    def normalize_string_lists(
        cls,
        values: list[str],
    ) -> list[str]:
        normalized_values: list[str] = []
        seen_values: set[str] = set()

        for value in values:
            normalized_value = value.strip()

            if not normalized_value:
                continue

            comparison_value = normalized_value.casefold()

            if comparison_value in seen_values:
                continue

            seen_values.add(comparison_value)
            normalized_values.append(normalized_value)

        return normalized_values

    @model_validator(mode="after")
    def validate_experience_range(self) -> Self:
        if (
            self.minimum_experience_years is not None
            and self.maximum_experience_years is not None
            and self.maximum_experience_years
            < self.minimum_experience_years
        ):
            raise ValueError(
                "Maximum experience cannot be less than "
                "minimum experience."
            )

        return self


class JobRequirementProfileResponse(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        from_attributes=True,
    )

    id: UUID
    job_id: UUID
    profile_data: JobRequirementProfileData | None
    parsing_status: JobRequirementParsingStatus
    parsing_error: str | None
    parser_version: str | None
    source_description_sha256: str | None
    parsed_at: datetime | None
    created_at: datetime
    updated_at: datetime