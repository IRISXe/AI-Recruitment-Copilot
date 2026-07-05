from datetime import datetime
from typing import Annotated, Self
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    StringConstraints,
    model_validator,
)


Skill = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=100,
    ),
]


class CandidateBase(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    full_name: str = Field(
        min_length=2,
        max_length=150,
        examples=["Harsha Vardhan"],
    )
    email: EmailStr = Field(
        examples=["harsha@example.com"],
    )
    phone: str | None = Field(
        default=None,
        min_length=7,
        max_length=30,
        examples=["+91 9876543210"],
    )
    current_location: str | None = Field(
        default=None,
        min_length=2,
        max_length=100,
        examples=["Hyderabad"],
    )
    current_role: str | None = Field(
        default=None,
        min_length=2,
        max_length=150,
        examples=["Backend Developer"],
    )
    total_experience_months: int = Field(
        default=0,
        ge=0,
        le=720,
        examples=[18],
    )
    skills: list[Skill] = Field(
        default_factory=list,
        max_length=50,
        examples=[["Python", "FastAPI", "PostgreSQL"]],
    )


class CandidateCreate(CandidateBase):
    pass


class CandidateUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    full_name: str | None = Field(
        default=None,
        min_length=2,
        max_length=150,
        examples=["Harsha Vardhan"],
    )
    email: EmailStr | None = Field(
        default=None,
        examples=["harsha@example.com"],
    )
    phone: str | None = Field(
        default=None,
        min_length=7,
        max_length=30,
        examples=["+91 9876543210"],
    )
    current_location: str | None = Field(
        default=None,
        min_length=2,
        max_length=100,
        examples=["Bengaluru"],
    )
    current_role: str | None = Field(
        default=None,
        min_length=2,
        max_length=150,
        examples=["Senior Backend Developer"],
    )
    total_experience_months: int | None = Field(
        default=None,
        ge=0,
        le=720,
        examples=[24],
    )
    skills: list[Skill] | None = Field(
        default=None,
        max_length=50,
        examples=[["Python", "FastAPI", "AWS"]],
    )

    @model_validator(mode="after")
    def validate_update_fields(self) -> Self:
        if not self.model_fields_set:
            raise ValueError(
                "At least one field must be provided for update."
            )

        non_nullable_fields = {
            "full_name",
            "email",
            "total_experience_months",
            "skills",
        }

        null_fields = sorted(
            field_name
            for field_name in self.model_fields_set
            if (
                field_name in non_nullable_fields
                and getattr(self, field_name) is None
            )
        )

        if null_fields:
            fields = ", ".join(null_fields)

            raise ValueError(
                f"Updated fields cannot be null: {fields}."
            )

        return self


class CandidateResponse(CandidateBase):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        from_attributes=True,
    )

    id: UUID
    created_at: datetime
    updated_at: datetime
