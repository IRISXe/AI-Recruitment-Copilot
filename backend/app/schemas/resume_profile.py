from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
)


ResumeParsingStatus = Literal[
    "pending",
    "completed",
    "failed",
]

CandidateMergeField = Literal[
    "full_name",
    "email",
    "phone",
    "current_location",
    "current_role",
    "total_experience_months",
    "skills",
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
        max_length=100,
    )


class ResumeProjectEntry(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str | None = Field(
        default=None,
        max_length=300,
    )
    description: str | None = Field(
        default=None,
        max_length=2000,
    )
    technologies: list[str] = Field(
        default_factory=list,
        max_length=100,
    )
    url: str | None = Field(
        default=None,
        max_length=1000,
    )
    highlights: list[str] = Field(
        default_factory=list,
        max_length=100,
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
    issue_date: str | None = Field(
        default=None,
        max_length=50,
    )
    expiry_date: str | None = Field(
        default=None,
        max_length=50,
    )
    credential_id: str | None = Field(
        default=None,
        max_length=300,
    )
    credential_url: str | None = Field(
        default=None,
        max_length=1000,
    )


class ResumeProfileData(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    full_name: str | None = Field(
        default=None,
        max_length=150,
    )
    email: EmailStr | None = None
    phone: str | None = Field(
        default=None,
        max_length=30,
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
        le=720,
    )
    skills: list[str] = Field(
        default_factory=list,
        max_length=100,
    )
    education: list[ResumeEducationEntry] = Field(
        default_factory=list,
        max_length=50,
    )
    work_experience: list[ResumeExperienceEntry] = Field(
        default_factory=list,
        max_length=100,
    )
    projects: list[ResumeProjectEntry] = Field(
        default_factory=list,
        max_length=100,
    )
    certifications: list[ResumeCertificationEntry] = Field(
        default_factory=list,
        max_length=100,
    )
    languages: list[str] = Field(
        default_factory=list,
        max_length=100,
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


class ResumeProfileResponse(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
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


class ResumeCandidateMergeRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    fields: list[CandidateMergeField] = Field(
        min_length=1,
        max_length=7,
    )
    overwrite_existing: bool = False

    @field_validator("fields")
    @classmethod
    def remove_duplicate_fields(
        cls,
        fields: list[CandidateMergeField],
    ) -> list[CandidateMergeField]:
        return list(dict.fromkeys(fields))