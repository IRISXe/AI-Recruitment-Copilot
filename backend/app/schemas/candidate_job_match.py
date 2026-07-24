from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)


CandidateJobMatchRecommendation = Literal[
    "strong_match",
    "good_match",
    "partial_match",
    "weak_match",
    "insufficient_data",
]


class CandidateJobMatchAnalysisData(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    matched_required_skills: list[str] = Field(
        default_factory=list,
        max_length=100,
    )
    missing_required_skills: list[str] = Field(
        default_factory=list,
        max_length=100,
    )
    matched_preferred_skills: list[str] = Field(
        default_factory=list,
        max_length=100,
    )
    missing_preferred_skills: list[str] = Field(
        default_factory=list,
        max_length=100,
    )

    experience_analysis: str = Field(
        default="",
        max_length=2000,
    )

    matched_required_education: list[str] = Field(
        default_factory=list,
        max_length=50,
    )
    missing_required_education: list[str] = Field(
        default_factory=list,
        max_length=50,
    )
    matched_preferred_education: list[str] = Field(
        default_factory=list,
        max_length=50,
    )
    missing_preferred_education: list[str] = Field(
        default_factory=list,
        max_length=50,
    )
    education_analysis: str = Field(
        default="",
        max_length=2000,
    )

    matched_required_certifications: list[str] = Field(
        default_factory=list,
        max_length=50,
    )
    missing_required_certifications: list[str] = Field(
        default_factory=list,
        max_length=50,
    )
    matched_preferred_certifications: list[str] = Field(
        default_factory=list,
        max_length=50,
    )
    missing_preferred_certifications: list[str] = Field(
        default_factory=list,
        max_length=50,
    )
    certification_analysis: str = Field(
        default="",
        max_length=2000,
    )

    location_analysis: str = Field(
        default="",
        max_length=2000,
    )
    work_mode_analysis: str = Field(
        default="",
        max_length=2000,
    )

    additional_alignment: list[str] = Field(
        default_factory=list,
        max_length=100,
    )
    strengths: list[str] = Field(
        default_factory=list,
        max_length=100,
    )
    gaps: list[str] = Field(
        default_factory=list,
        max_length=100,
    )
    warnings: list[str] = Field(
        default_factory=list,
        max_length=100,
    )
    missing_data: list[str] = Field(
        default_factory=list,
        max_length=100,
    )

    @field_validator(
        "matched_required_skills",
        "missing_required_skills",
        "matched_preferred_skills",
        "missing_preferred_skills",
        "matched_required_education",
        "missing_required_education",
        "matched_preferred_education",
        "missing_preferred_education",
        "matched_required_certifications",
        "missing_required_certifications",
        "matched_preferred_certifications",
        "missing_preferred_certifications",
        "additional_alignment",
        "strengths",
        "gaps",
        "warnings",
        "missing_data",
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


class CandidateJobMatchValues(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    resume_id: UUID
    resume_profile_id: UUID
    job_requirement_profile_id: UUID

    overall_score: float = Field(
        ge=0.0,
        le=100.0,
    )
    skill_score: float = Field(
        ge=0.0,
        le=100.0,
    )
    experience_score: float = Field(
        ge=0.0,
        le=100.0,
    )
    education_score: float = Field(
        ge=0.0,
        le=100.0,
    )
    certification_score: float = Field(
        ge=0.0,
        le=100.0,
    )
    location_score: float = Field(
        ge=0.0,
        le=100.0,
    )
    work_mode_score: float = Field(
        ge=0.0,
        le=100.0,
    )
    confidence_score: float = Field(
        ge=0.0,
        le=100.0,
    )

    recommendation: CandidateJobMatchRecommendation

    analysis_data: CandidateJobMatchAnalysisData

    scoring_version: str = Field(
        min_length=1,
        max_length=50,
    )

    source_resume_text_sha256: str = Field(
        min_length=64,
        max_length=64,
    )
    source_resume_parser_version: str = Field(
        min_length=1,
        max_length=50,
    )

    source_job_description_sha256: str = Field(
        min_length=64,
        max_length=64,
    )
    source_job_parser_version: str = Field(
        min_length=1,
        max_length=50,
    )

    matched_at: datetime


class CandidateJobMatchCreate(CandidateJobMatchValues):
    candidate_id: UUID
    job_id: UUID


class CandidateJobMatchUpdate(CandidateJobMatchValues):
    pass


class CandidateJobMatchResponse(CandidateJobMatchCreate):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        from_attributes=True,
    )

    id: UUID
    created_at: datetime
    updated_at: datetime