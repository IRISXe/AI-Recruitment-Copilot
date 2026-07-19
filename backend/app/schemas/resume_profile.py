from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


ResumeParsingStatus = Literal[
    "pending",
    "completed",
    "failed",
]


class ResumeEducationEntry(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    institution: str | None = Field(
        default=None,
        max_length=300,
    )
    degree: str | None = Field(
        default=None,
        max_length=200,
    )
    field_of_study: str | None = Field(
        default=None,
        max_length=200,
    )
    start_date: str | None = Field(
        default=None,
        max_length=50,
    )
    end_date: str | None = Field(
        default=None,
        max_length=50,
    )
    description: str | None = Field(
        default=None,
        max_length=2000,
    )


class ResumeExperienceEntry(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    company: str | None = Field(
        default=None,
        max_length=300,
    )
    role: str | None = Field(
        default=None,
        max_length=200,
    )
    location: str | None = Field(
        default=None,
        max_length=200,
    )
    start_date: str | None = Field(
        default=None,
        max_length=50,
    )
    end_date: str | None = Field(
        default=None,
        max_length=50,
    )
    is_current: bool = False
    highlights: list[str] = Field(
        default_factory=list,
    )


class ResumeProjectEntry(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str | None = Field(
        default=None,
        max_length=300,
    )
    description: str | None = Field(
        default=None,
        max_length=3000,
    )
    technologies: list[str] = Field(
        default_factory=list,
    )
    url: str | None = Field(
        default=None,
        max_length=500,
    )


class ResumeCertificationEntry(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str | None = Field(
        default=None,
        max_length=300,
    )
    issuer: str | None = Field(
        default=None,
        max_length=300,
    )
    issued_date: str | None = Field(
        default=None,
        max_length=50,
    )
    credential_id: str | None = Field(
        default=None,
        max_length=200,
    )


class ResumeProfileData(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    full_name: str | None = Field(
        default=None,
        max_length=200,
    )
    email: str | None = Field(
        default=None,
        max_length=320,
    )
    phone: str | None = Field(
        default=None,
        max_length=50,
    )
    location: str | None = Field(
        default=None,
        max_length=200,
    )
    current_role: str | None = Field(
        default=None,
        max_length=200,
    )
    professional_summary: str | None = Field(
        default=None,
        max_length=5000,
    )
    total_experience_months: int | None = Field(
        default=None,
        ge=0,
    )
    skills: list[str] = Field(
        default_factory=list,
    )
    education: list[ResumeEducationEntry] = Field(
        default_factory=list,
    )
    work_experience: list[ResumeExperienceEntry] = Field(
        default_factory=list,
    )
    projects: list[ResumeProjectEntry] = Field(
        default_factory=list,
    )
    certifications: list[ResumeCertificationEntry] = Field(
        default_factory=list,
    )
    languages: list[str] = Field(
        default_factory=list,
    )


class ResumeProfileResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: UUID
    resume_id: UUID
    profile_data: ResumeProfileData | None
    parsing_status: ResumeParsingStatus
    parsing_error: str | None
    parser_version: str | None
    source_text_sha256: str | None
    parsed_at: datetime | None
    created_at: datetime
    updated_at: datetime