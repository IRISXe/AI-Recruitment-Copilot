from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


ResumeExtractionStatus = Literal[
    "pending",
    "completed",
    "failed",
]


class ResumeContentResponse(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        from_attributes=True,
    )

    id: UUID
    resume_id: UUID
    extracted_text: str | None
    extraction_status: ResumeExtractionStatus
    extraction_error: str | None
    extractor_version: str | None
    extracted_at: datetime | None
    created_at: datetime
    updated_at: datetime