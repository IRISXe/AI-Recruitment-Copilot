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
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.resume import (
    ResumeCreate,
    ResumeResponse,
    ResumeUpdate,
)
from app.schemas.resume_content import ResumeContentResponse
from app.services.resume_content_service import (
    extract_resume_content as extract_resume_content_service,
    get_resume_content as get_resume_content_service,
)
from app.services.resume_service import (
    create_resume as create_resume_service,
    delete_resume as delete_resume_service,
    get_resume_by_id as get_resume_by_id_service,
    get_resume_download as get_resume_download_service,
    list_resumes as list_resumes_service,
    update_resume as update_resume_service,
    upload_resume as upload_resume_service,
)


router = APIRouter(
    prefix="/resumes",
    tags=["Resumes"],
)


@router.post(
    "",
    response_model=ResumeResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_resume(
    payload: ResumeCreate,
    session: Session = Depends(get_db),
) -> ResumeResponse:
    return create_resume_service(
        session,
        payload,
    )


@router.post(
    "/upload",
    response_model=ResumeResponse,
    status_code=status.HTTP_201_CREATED,
)
def upload_resume(
    candidate_id: UUID = Form(...),
    is_primary: bool = Form(False),
    file: UploadFile = File(...),
    session: Session = Depends(get_db),
) -> ResumeResponse:
    return upload_resume_service(
        session,
        candidate_id=candidate_id,
        uploaded_file=file,
        is_primary=is_primary,
    )


@router.get(
    "",
    response_model=list[ResumeResponse],
    status_code=status.HTTP_200_OK,
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
    return list_resumes_service(
        session,
        offset=offset,
        limit=limit,
        candidate_id=candidate_id,
    )


@router.get(
    "/{resume_id}/download",
    response_class=FileResponse,
    status_code=status.HTTP_200_OK,
    summary="Download a Resume file",
)
def download_resume(
    resume_id: UUID,
    session: Session = Depends(get_db),
) -> FileResponse:
    download = get_resume_download_service(
        session,
        resume_id=resume_id,
    )

    return FileResponse(
        path=download.file_path,
        media_type=download.content_type,
        filename=download.filename,
    )


@router.post(
    "/{resume_id}/extract",
    response_model=ResumeContentResponse,
    status_code=status.HTTP_200_OK,
    summary="Extract text from a Resume",
)
def extract_resume_content(
    resume_id: UUID,
    session: Session = Depends(get_db),
) -> ResumeContentResponse:
    return extract_resume_content_service(
        session,
        resume_id=resume_id,
    )


@router.get(
    "/{resume_id}/content",
    response_model=ResumeContentResponse,
    status_code=status.HTTP_200_OK,
    summary="Get extracted Resume content",
)
def get_resume_content(
    resume_id: UUID,
    session: Session = Depends(get_db),
) -> ResumeContentResponse:
    return get_resume_content_service(
        session,
        resume_id=resume_id,
    )


@router.get(
    "/{resume_id}",
    response_model=ResumeResponse,
    status_code=status.HTTP_200_OK,
)
def get_resume_by_id(
    resume_id: UUID,
    session: Session = Depends(get_db),
) -> ResumeResponse:
    return get_resume_by_id_service(
        session,
        resume_id,
    )


@router.patch(
    "/{resume_id}",
    response_model=ResumeResponse,
    status_code=status.HTTP_200_OK,
)
def update_resume(
    resume_id: UUID,
    payload: ResumeUpdate,
    session: Session = Depends(get_db),
) -> ResumeResponse:
    return update_resume_service(
        session,
        resume_id=resume_id,
        payload=payload,
    )


@router.delete(
    "/{resume_id}",
    status_code=status.HTTP_204_NO_CONTENT,
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
