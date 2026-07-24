from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.candidate_job_match import (
    CandidateJobMatchResponse,
)
from app.services.candidate_job_match_service import (
    generate_candidate_job_match as generate_match_service,
)


router = APIRouter(
    prefix="/candidate-job-matches",
    tags=["Candidate-Job Matches"],
)


@router.post(
    "/candidates/{candidate_id}/jobs/{job_id}",
    response_model=CandidateJobMatchResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate a Candidate-Job match",
)
def generate_candidate_job_match(
    candidate_id: UUID,
    job_id: UUID,
    force: bool = Query(
        default=False,
        description=(
            "Recalculate the match even when the stored "
            "result is already current."
        ),
    ),
    session: Session = Depends(get_db),
) -> CandidateJobMatchResponse:
    candidate_job_match = generate_match_service(
        session,
        candidate_id=candidate_id,
        job_id=job_id,
        force=force,
    )

    return CandidateJobMatchResponse.model_validate(
        candidate_job_match
    )