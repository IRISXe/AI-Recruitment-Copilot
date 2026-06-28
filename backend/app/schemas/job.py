from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


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
    employment_type: Literal[
        "full_time",
        "part_time",
        "contract",
        "internship",
    ]
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


class JobValidationResponse(BaseModel):
    message: str
    job: JobValidationRequest