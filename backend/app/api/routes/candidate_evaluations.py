from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.candidate_evaluation import (
    CandidateEvaluationResponse,
)
from app.services.candidate_evaluation_service import (
    evaluate_candidate_for_job as evaluate_candidate_service,
)


router = APIRouter(
    prefix="/candidates",
    tags=["Candidate Evaluations"],
)


@router.post(
    "/{candidate_id}/jobs/{job_id}/evaluate",
    response_model=CandidateEvaluationResponse,
    status_code=status.HTTP_200_OK,
    summary="Evaluate a Candidate for a Job",
    description=(
        "Run the complete deterministic Candidate evaluation "
        "pipeline: Resume extraction, Resume parsing, Job "
        "requirement parsing and Candidate-Job matching."
    ),
)
def evaluate_candidate_for_job(
    candidate_id: UUID,
    job_id: UUID,
    force: bool = Query(
        default=False,
        description=(
            "Reprocess every evaluation stage even when "
            "the stored records are current."
        ),
    ),
    session: Session = Depends(get_db),
) -> CandidateEvaluationResponse:
    return evaluate_candidate_service(
        session,
        candidate_id=candidate_id,
        job_id=job_id,
        force=force,
    )