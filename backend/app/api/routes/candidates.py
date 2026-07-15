from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.candidate import (
    CandidateCreate,
    CandidateResponse,
    CandidateUpdate,
)
from app.services.candidate_service import (
    create_candidate as create_candidate_service,
    delete_candidate as delete_candidate_service,
    get_candidate_by_id as get_candidate_by_id_service,
    list_candidates as list_candidates_service,
    update_candidate as update_candidate_service,
)


router = APIRouter(prefix="/candidates", tags=["Candidates"])


@router.post(
    "",
    response_model=CandidateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a candidate",
)
def create_candidate(
    payload: CandidateCreate,
    session: Session = Depends(get_db),
) -> CandidateResponse:
    candidate = create_candidate_service(session, payload)

    return CandidateResponse.model_validate(candidate)


@router.get(
    "",
    response_model=list[CandidateResponse],
    status_code=status.HTTP_200_OK,
    summary="List candidates",
)
def list_candidates(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    session: Session = Depends(get_db),
) -> list[CandidateResponse]:
    candidates = list_candidates_service(
        session,
        offset=offset,
        limit=limit,
    )

    return [
        CandidateResponse.model_validate(candidate)
        for candidate in candidates
    ]


@router.get(
    "/{candidate_id}",
    response_model=CandidateResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a candidate by ID",
)
def get_candidate_by_id(
    candidate_id: UUID,
    session: Session = Depends(get_db),
) -> CandidateResponse:
    candidate = get_candidate_by_id_service(
        session,
        candidate_id,
    )

    return CandidateResponse.model_validate(candidate)


@router.patch(
    "/{candidate_id}",
    response_model=CandidateResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a candidate",
)
def update_candidate(
    candidate_id: UUID,
    payload: CandidateUpdate,
    session: Session = Depends(get_db),
) -> CandidateResponse:
    candidate = update_candidate_service(
        session,
        candidate_id=candidate_id,
        payload=payload,
    )

    return CandidateResponse.model_validate(candidate)


@router.delete(
    "/{candidate_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a candidate",
)
def delete_candidate(
    candidate_id: UUID,
    session: Session = Depends(get_db),
) -> Response:
    delete_candidate_service(
        session,
        candidate_id=candidate_id,
    )

    return Response(
        status_code=status.HTTP_204_NO_CONTENT,
    )

    