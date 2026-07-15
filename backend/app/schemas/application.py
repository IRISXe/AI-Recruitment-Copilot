from datetime import datetime
from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


ApplicationStatus = Literal[
    "applied",
    "screening",
    "shortlisted",
    "rejected",
    "hired",
    "withdrawn",
]


class ApplicationCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    job_id: UUID
    candidate_id: UUID
    status: ApplicationStatus = "applied"
    source: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
        examples=["LinkedIn"],
    )
    notes: str | None = Field(
        default=None,
        min_length=1,
        max_length=5000,
        examples=["Candidate applied through the careers page."],
    )


class ApplicationUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    status: ApplicationStatus | None = None
    source: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
        examples=["Employee referral"],
    )
    notes: str | None = Field(
        default=None,
        min_length=1,
        max_length=5000,
        examples=["Candidate moved to the screening stage."],
    )

    @model_validator(mode="after")
    def validate_update_fields(self) -> Self:
        if not self.model_fields_set:
            raise ValueError(
                "At least one field must be provided for update."
            )

        if "status" in self.model_fields_set and self.status is None:
            raise ValueError(
                "Updated field cannot be null: status."
            )

        return self


class ApplicationResponse(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        from_attributes=True,
    )

    id: UUID
    job_id: UUID
    candidate_id: UUID
    status: ApplicationStatus
    source: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime