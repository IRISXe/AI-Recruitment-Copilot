from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.application import (
    ApplicationCreate,
    ApplicationResponse,
    ApplicationStatus,
    ApplicationUpdate,
)
from app.services.application_service import (
    create_application as create_application_service,
    delete_application as delete_application_service,
    get_application_by_id as get_application_by_id_service,
    list_applications as list_applications_service,
    update_application as update_application_service,
)


router = APIRouter(
    prefix="/applications",
    tags=["Applications"],
)


@router.post(
    "",
    response_model=ApplicationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an application",
)
def create_application(
    payload: ApplicationCreate,
    session: Session = Depends(get_db),
) -> ApplicationResponse:
    application = create_application_service(
        session,
        payload,
    )

    return ApplicationResponse.model_validate(application)


@router.get(
    "",
    response_model=list[ApplicationResponse],
    status_code=status.HTTP_200_OK,
    summary="List applications",
)
def list_applications(
    offset: int = Query(
        default=0,
        ge=0,
    ),
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
    ),
    job_id: UUID | None = Query(
        default=None,
    ),
    candidate_id: UUID | None = Query(
        default=None,
    ),
    application_status: ApplicationStatus | None = Query(
        default=None,
        alias="status",
    ),
    session: Session = Depends(get_db),
) -> list[ApplicationResponse]:
    applications = list_applications_service(
        session,
        offset=offset,
        limit=limit,
        job_id=job_id,
        candidate_id=candidate_id,
        application_status=application_status,
    )

    return [
        ApplicationResponse.model_validate(application)
        for application in applications
    ]


@router.get(
    "/{application_id}",
    response_model=ApplicationResponse,
    status_code=status.HTTP_200_OK,
    summary="Get an application by ID",
)
def get_application_by_id(
    application_id: UUID,
    session: Session = Depends(get_db),
) -> ApplicationResponse:
    application = get_application_by_id_service(
        session,
        application_id,
    )

    return ApplicationResponse.model_validate(application)


@router.patch(
    "/{application_id}",
    response_model=ApplicationResponse,
    status_code=status.HTTP_200_OK,
    summary="Update an application",
)
def update_application(
    application_id: UUID,
    payload: ApplicationUpdate,
    session: Session = Depends(get_db),
) -> ApplicationResponse:
    application = update_application_service(
        session,
        application_id=application_id,
        payload=payload,
    )

    return ApplicationResponse.model_validate(application)


@router.delete(
    "/{application_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an application",
)
def delete_application(
    application_id: UUID,
    session: Session = Depends(get_db),
) -> Response:
    delete_application_service(
        session,
        application_id=application_id,
    )

    return Response(
        status_code=status.HTTP_204_NO_CONTENT,
    )