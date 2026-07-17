from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    Query,
    Response,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.resume import (
    ResumeCreate,
    ResumeResponse,
    ResumeUpdate,
)
from app.services.resume_service import (
    create_resume as create_resume_service,
    delete_resume as delete_resume_service,
    get_resume_by_id as get_resume_by_id_service,
    list_resumes as list_resumes_service,
    update_resume as update_resume_service,
    upload_resume as upload_resume_service,
)


router = APIRouter(
    prefix="/resumes",
    tags=["Resumes"],
)


@router.post(
    "/upload",
    response_model=ResumeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a Resume file",
)
def upload_resume(
    candidate_id: UUID = Form(...),
    is_primary: bool = Form(default=False),
    file: UploadFile = File(...),
    session: Session = Depends(get_db),
) -> ResumeResponse:
    resume = upload_resume_service(
        session,
        candidate_id=candidate_id,
        uploaded_file=file,
        is_primary=is_primary,
    )

    return ResumeResponse.model_validate(resume)


@router.post(
    "",
    response_model=ResumeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Resume metadata",
)
def create_resume(
    payload: ResumeCreate,
    session: Session = Depends(get_db),
) -> ResumeResponse:
    resume = create_resume_service(
        session,
        payload,
    )

    return ResumeResponse.model_validate(resume)


@router.get(
    "",
    response_model=list[ResumeResponse],
    status_code=status.HTTP_200_OK,
    summary="List Resumes",
)
def list_resumes(
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
    session: Session = Depends(get_db),
) -> list[ResumeResponse]:
    resumes = list_resumes_service(
        session,
        offset=offset,
        limit=limit,
        candidate_id=candidate_id,
    )

    return [
        ResumeResponse.model_validate(resume)
        for resume in resumes
    ]


@router.get(
    "/{resume_id}",
    response_model=ResumeResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a Resume",
)
def get_resume_by_id(
    resume_id: UUID,
    session: Session = Depends(get_db),
) -> ResumeResponse:
    resume = get_resume_by_id_service(
        session,
        resume_id,
    )

    return ResumeResponse.model_validate(resume)


@router.patch(
    "/{resume_id}",
    response_model=ResumeResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a Resume",
)
def update_resume(
    resume_id: UUID,
    payload: ResumeUpdate,
    session: Session = Depends(get_db),
) -> ResumeResponse:
    resume = update_resume_service(
        session,
        resume_id=resume_id,
        payload=payload,
    )

    return ResumeResponse.model_validate(resume)


@router.delete(
    "/{resume_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a Resume",
)
def delete_resume(
    resume_id: UUID,
    session: Session = Depends(get_db),
) -> Response:
    delete_resume_service(
        session,
        resume_id=resume_id,
    )

    return Response(
        status_code=status.HTTP_204_NO_CONTENT,
    )