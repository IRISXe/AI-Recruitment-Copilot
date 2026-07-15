from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.application import Application
from app.schemas.application import ApplicationCreate, ApplicationUpdate


def create_application(
    session: Session,
    payload: ApplicationCreate,
) -> Application:
    application = Application(**payload.model_dump())

    session.add(application)
    session.flush()

    return application


def get_application_by_id(
    session: Session,
    application_id: UUID,
) -> Application | None:
    return session.get(Application, application_id)


def get_application_by_job_and_candidate(
    session: Session,
    *,
    job_id: UUID,
    candidate_id: UUID,
) -> Application | None:
    statement = select(Application).where(
        Application.job_id == job_id,
        Application.candidate_id == candidate_id,
    )

    return session.scalar(statement)


def list_applications(
    session: Session,
    *,
    offset: int,
    limit: int,
) -> list[Application]:
    statement = (
        select(Application)
        .order_by(Application.created_at.desc())
        .offset(offset)
        .limit(limit)
    )

    return list(session.scalars(statement).all())


def update_application(
    session: Session,
    *,
    application: Application,
    payload: ApplicationUpdate,
) -> Application:
    update_data = payload.model_dump(exclude_unset=True)

    for field_name, value in update_data.items():
        setattr(application, field_name, value)

    session.flush()

    return application


def delete_application(
    session: Session,
    *,
    application: Application,
) -> None:
    session.delete(application)
    session.flush()
