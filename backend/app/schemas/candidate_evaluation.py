from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.schemas.candidate_job_match import (
    CandidateJobMatchResponse,
)
from app.schemas.job_requirement_profile import (
    JobRequirementProfileResponse,
)
from app.schemas.resume_content import (
    ResumeContentResponse,
)
from app.schemas.resume_profile import (
    ResumeProfileResponse,
)


CandidateEvaluationStageAction = Literal[
    "reused",
    "processed",
]


class CandidateEvaluationStages(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
    )

    resume_content: CandidateEvaluationStageAction
    resume_profile: CandidateEvaluationStageAction
    job_requirement_profile: CandidateEvaluationStageAction
    candidate_job_match: CandidateEvaluationStageAction


class CandidateEvaluationResponse(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
    )

    status: Literal["completed"] = "completed"

    candidate_id: UUID
    job_id: UUID
    resume_id: UUID

    force: bool
    evaluated_at: datetime

    stages: CandidateEvaluationStages

    resume_content: ResumeContentResponse
    resume_profile: ResumeProfileResponse
    job_requirement_profile: JobRequirementProfileResponse
    candidate_job_match: CandidateJobMatchResponse