from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.candidate_job_match import (
    CandidateJobMatchRecommendation,
    CandidateJobMatchResponse,
)
from app.schemas.candidate_job_match_query import (
    CandidateJobMatchSortBy,
    CandidateJobMatchSortOrder,
)
from app.services.candidate_job_match_query_service import (
    get_candidate_job_match_by_id as get_match_service,
    list_candidate_job_matches as list_matches_service,
    list_candidate_matches_for_job as list_job_candidates_service,
    list_job_matches_for_candidate as list_candidate_jobs_service,
)
from app.services.candidate_job_match_service import (
    generate_candidate_job_match as generate_match_service,
)


router = APIRouter(
    tags=["Candidate-Job Matches"],
)


@router.post(
    "/candidate-job-matches/candidates/{candidate_id}/jobs/{job_id}",
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


@router.get(
    "/candidate-job-matches",
    response_model=list[CandidateJobMatchResponse],
    status_code=status.HTTP_200_OK,
    summary="List Candidate-Job matches",
)
def list_candidate_job_matches(
    offset: int = Query(
        default=0,
        ge=0,
    ),
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
    ),
    candidate_id: UUID | None = Query(
        default=None,
    ),
    job_id: UUID | None = Query(
        default=None,
    ),
    minimum_score: float | None = Query(
        default=None,
        ge=0.0,
        le=100.0,
    ),
    minimum_confidence: float | None = Query(
        default=None,
        ge=0.0,
        le=100.0,
    ),
    recommendation: CandidateJobMatchRecommendation | None = Query(
        default=None,
    ),
    sort_by: CandidateJobMatchSortBy = Query(
        default="overall_score",
    ),
    sort_order: CandidateJobMatchSortOrder = Query(
        default="desc",
    ),
    session: Session = Depends(get_db),
) -> list[CandidateJobMatchResponse]:
    matches = list_matches_service(
        session,
        offset=offset,
        limit=limit,
        candidate_id=candidate_id,
        job_id=job_id,
        minimum_score=minimum_score,
        minimum_confidence=minimum_confidence,
        recommendation=recommendation,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    return [
        CandidateJobMatchResponse.model_validate(match)
        for match in matches
    ]


@router.get(
    "/candidate-job-matches/{match_id}",
    response_model=CandidateJobMatchResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a Candidate-Job match by ID",
)
def get_candidate_job_match_by_id(
    match_id: UUID,
    session: Session = Depends(get_db),
) -> CandidateJobMatchResponse:
    candidate_job_match = get_match_service(
        session,
        match_id,
    )

    return CandidateJobMatchResponse.model_validate(
        candidate_job_match
    )


@router.get(
    "/jobs/{job_id}/candidate-matches",
    response_model=list[CandidateJobMatchResponse],
    status_code=status.HTTP_200_OK,
    summary="List ranked Candidate matches for a Job",
)
def list_candidate_matches_for_job(
    job_id: UUID,
    offset: int = Query(
        default=0,
        ge=0,
    ),
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
    ),
    minimum_score: float | None = Query(
        default=None,
        ge=0.0,
        le=100.0,
    ),
    minimum_confidence: float | None = Query(
        default=None,
        ge=0.0,
        le=100.0,
    ),
    recommendation: CandidateJobMatchRecommendation | None = Query(
        default=None,
    ),
    sort_by: CandidateJobMatchSortBy = Query(
        default="overall_score",
    ),
    sort_order: CandidateJobMatchSortOrder = Query(
        default="desc",
    ),
    session: Session = Depends(get_db),
) -> list[CandidateJobMatchResponse]:
    matches = list_job_candidates_service(
        session,
        job_id=job_id,
        offset=offset,
        limit=limit,
        minimum_score=minimum_score,
        minimum_confidence=minimum_confidence,
        recommendation=recommendation,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    return [
        CandidateJobMatchResponse.model_validate(match)
        for match in matches
    ]


@router.get(
    "/candidates/{candidate_id}/job-matches",
    response_model=list[CandidateJobMatchResponse],
    status_code=status.HTTP_200_OK,
    summary="List ranked Job matches for a Candidate",
)
def list_job_matches_for_candidate(
    candidate_id: UUID,
    offset: int = Query(
        default=0,
        ge=0,
    ),
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
    ),
    minimum_score: float | None = Query(
        default=None,
        ge=0.0,
        le=100.0,
    ),
    minimum_confidence: float | None = Query(
        default=None,
        ge=0.0,
        le=100.0,
    ),
    recommendation: CandidateJobMatchRecommendation | None = Query(
        default=None,
    ),
    sort_by: CandidateJobMatchSortBy = Query(
        default="overall_score",
    ),
    sort_order: CandidateJobMatchSortOrder = Query(
        default="desc",
    ),
    session: Session = Depends(get_db),
) -> list[CandidateJobMatchResponse]:
    matches = list_candidate_jobs_service(
        session,
        candidate_id=candidate_id,
        offset=offset,
        limit=limit,
        minimum_score=minimum_score,
        minimum_confidence=minimum_confidence,
        recommendation=recommendation,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    return [
        CandidateJobMatchResponse.model_validate(match)
        for match in matches
    ]