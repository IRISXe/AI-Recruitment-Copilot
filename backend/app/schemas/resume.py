from datetime import datetime
from pathlib import PurePath
from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ResumeCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    candidate_id: UUID

    original_filename: str = Field(
        min_length=1,
        max_length=255,
        examples=["Harsha_Vardhan_Resume.pdf"],
    )

    stored_filename: str = Field(
        min_length=1,
        max_length=255,
        examples=["5b1b7e5e-645d-4aa4-a700-resume.pdf"],
    )

    storage_path: str = Field(
        min_length=1,
        max_length=500,
        examples=[
            "uploads/resumes/5b1b7e5e-645d-4aa4-a700-resume.pdf"
        ],
    )

    content_type: str = Field(
        min_length=1,
        max_length=100,
        examples=["application/pdf"],
    )

    file_size_bytes: int = Field(
        ge=0,
        examples=[245760],
    )

    is_primary: bool = False

    @field_validator(
        "original_filename",
        "stored_filename",
    )
    @classmethod
    def validate_filename(cls, value: str) -> str:
        filename = PurePath(value).name

        if filename != value:
            raise ValueError(
                "Filename must not contain directory components."
            )

        if filename in {".", ".."}:
            raise ValueError(
                "Filename is invalid."
            )

        return value


class ResumeUpdate(BaseModel):
    is_primary: bool | None = None

    @model_validator(mode="after")
    def validate_update_fields(self) -> Self:
        if not self.model_fields_set:
            raise ValueError(
                "At least one field must be provided for update."
            )

        if "is_primary" in self.model_fields_set and self.is_primary is None:
            raise ValueError(
                "Updated field cannot be null: is_primary."
            )

        return self


class ResumeResponse(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        from_attributes=True,
    )

    id: UUID
    candidate_id: UUID
    original_filename: str
    stored_filename: str
    storage_path: str
    content_type: str
    file_size_bytes: int
    is_primary: bool
    created_at: datetime
    updated_at: datetime