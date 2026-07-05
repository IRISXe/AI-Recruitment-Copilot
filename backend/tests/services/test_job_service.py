from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.models.job import Job
from app.schemas.job import JobCreate, JobUpdate
from app.services.job_service import (
    create_job,
    delete_job,
    get_job_by_id,
    list_jobs,
    update_job,
)


def build_create_payload() -> JobCreate:
    return JobCreate(
        title="Backend Engineer",
        department="Engineering",
        location="Hyderabad",
        employment_type="full_time",
        minimum_experience=2,
        required_skills=["Python", "FastAPI"],
        preferred_skills=["PostgreSQL"],
    )


def assert_app_exception(
    exception: AppException,
    *,
    expected_status: int,
    expected_code: str,
    expected_message: str,
) -> None:
    assert exception.status_code == expected_status
    assert exception.code == expected_code
    assert exception.message == expected_message


def test_create_job_commits_refreshes_and_returns_job() -> None:
    session = MagicMock(spec=Session)
    job = MagicMock(spec=Job)
    payload = build_create_payload()

    with patch(
        "app.services.job_service.create_job_record",
        return_value=job,
    ) as create_record:
        result = create_job(
            session=session,
            payload=payload,
        )

    create_record.assert_called_once_with(session, payload)
    session.commit.assert_called_once_with()
    session.refresh.assert_called_once_with(job)
    session.rollback.assert_not_called()

    assert result is job


def test_create_job_rolls_back_database_error() -> None:
    session = MagicMock(spec=Session)
    payload = build_create_payload()

    with patch(
        "app.services.job_service.create_job_record",
        side_effect=SQLAlchemyError("database failure"),
    ):
        with pytest.raises(AppException) as exc_info:
            create_job(
                session=session,
                payload=payload,
            )

    session.rollback.assert_called_once_with()
    session.commit.assert_not_called()
    session.refresh.assert_not_called()

    assert_app_exception(
        exc_info.value,
        expected_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        expected_code="job_creation_failed",
        expected_message="The job could not be created.",
    )


def test_get_job_by_id_returns_existing_job() -> None:
    session = MagicMock(spec=Session)
    job = MagicMock(spec=Job)
    job_id = uuid4()

    with patch(
        "app.services.job_service.get_job_by_id_record",
        return_value=job,
    ) as get_record:
        result = get_job_by_id(
            session=session,
            job_id=job_id,
        )

    get_record.assert_called_once_with(session, job_id)
    session.rollback.assert_not_called()

    assert result is job


def test_get_job_by_id_raises_not_found() -> None:
    session = MagicMock(spec=Session)
    job_id = uuid4()

    with patch(
        "app.services.job_service.get_job_by_id_record",
        return_value=None,
    ):
        with pytest.raises(AppException) as exc_info:
            get_job_by_id(
                session=session,
                job_id=job_id,
            )

    session.rollback.assert_not_called()

    assert_app_exception(
        exc_info.value,
        expected_status=status.HTTP_404_NOT_FOUND,
        expected_code="job_not_found",
        expected_message="The requested job does not exist.",
    )


def test_get_job_by_id_rolls_back_database_error() -> None:
    session = MagicMock(spec=Session)
    job_id = uuid4()

    with patch(
        "app.services.job_service.get_job_by_id_record",
        side_effect=SQLAlchemyError("database failure"),
    ):
        with pytest.raises(AppException) as exc_info:
            get_job_by_id(
                session=session,
                job_id=job_id,
            )

    session.rollback.assert_called_once_with()

    assert_app_exception(
        exc_info.value,
        expected_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        expected_code="job_retrieval_failed",
        expected_message="The job could not be retrieved.",
    )


def test_list_jobs_returns_repository_results() -> None:
    session = MagicMock(spec=Session)
    jobs = [
        MagicMock(spec=Job),
        MagicMock(spec=Job),
    ]

    with patch(
        "app.services.job_service.list_jobs_records",
        return_value=jobs,
    ) as list_records:
        result = list_jobs(
            session=session,
            offset=10,
            limit=20,
        )

    list_records.assert_called_once_with(
        session,
        offset=10,
        limit=20,
    )
    session.rollback.assert_not_called()

    assert result is jobs


def test_list_jobs_rolls_back_database_error() -> None:
    session = MagicMock(spec=Session)

    with patch(
        "app.services.job_service.list_jobs_records",
        side_effect=SQLAlchemyError("database failure"),
    ):
        with pytest.raises(AppException) as exc_info:
            list_jobs(
                session=session,
                offset=0,
                limit=20,
            )

    session.rollback.assert_called_once_with()

    assert_app_exception(
        exc_info.value,
        expected_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        expected_code="job_listing_failed",
        expected_message="The jobs could not be retrieved.",
    )


def test_update_job_commits_refreshes_and_returns_updated_job() -> None:
    session = MagicMock(spec=Session)
    existing_job = MagicMock(spec=Job)
    updated_job = MagicMock(spec=Job)
    job_id = uuid4()
    payload = JobUpdate(
        title="Senior Backend Engineer",
    )

    with (
        patch(
            "app.services.job_service.get_job_by_id_record",
            return_value=existing_job,
        ) as get_record,
        patch(
            "app.services.job_service.update_job_record",
            return_value=updated_job,
        ) as update_record,
    ):
        result = update_job(
            session=session,
            job_id=job_id,
            payload=payload,
        )

    get_record.assert_called_once_with(session, job_id)
    update_record.assert_called_once_with(
        session,
        job=existing_job,
        payload=payload,
    )
    session.commit.assert_called_once_with()
    session.refresh.assert_called_once_with(updated_job)
    session.rollback.assert_not_called()

    assert result is updated_job


def test_update_job_raises_not_found() -> None:
    session = MagicMock(spec=Session)
    job_id = uuid4()
    payload = JobUpdate(
        title="Senior Backend Engineer",
    )

    with (
        patch(
            "app.services.job_service.get_job_by_id_record",
            return_value=None,
        ),
        patch(
            "app.services.job_service.update_job_record",
        ) as update_record,
    ):
        with pytest.raises(AppException) as exc_info:
            update_job(
                session=session,
                job_id=job_id,
                payload=payload,
            )

    update_record.assert_not_called()
    session.commit.assert_not_called()
    session.rollback.assert_not_called()

    assert_app_exception(
        exc_info.value,
        expected_status=status.HTTP_404_NOT_FOUND,
        expected_code="job_not_found",
        expected_message="The requested job does not exist.",
    )


def test_update_job_rolls_back_database_error() -> None:
    session = MagicMock(spec=Session)
    existing_job = MagicMock(spec=Job)
    job_id = uuid4()
    payload = JobUpdate(
        title="Senior Backend Engineer",
    )

    with (
        patch(
            "app.services.job_service.get_job_by_id_record",
            return_value=existing_job,
        ),
        patch(
            "app.services.job_service.update_job_record",
            side_effect=SQLAlchemyError("database failure"),
        ),
    ):
        with pytest.raises(AppException) as exc_info:
            update_job(
                session=session,
                job_id=job_id,
                payload=payload,
            )

    session.rollback.assert_called_once_with()
    session.commit.assert_not_called()
    session.refresh.assert_not_called()

    assert_app_exception(
        exc_info.value,
        expected_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        expected_code="job_update_failed",
        expected_message="The job could not be updated.",
    )


def test_delete_job_commits_successful_deletion() -> None:
    session = MagicMock(spec=Session)
    existing_job = MagicMock(spec=Job)
    job_id = uuid4()

    with (
        patch(
            "app.services.job_service.get_job_by_id_record",
            return_value=existing_job,
        ) as get_record,
        patch(
            "app.services.job_service.delete_job_record",
            return_value=None,
        ) as delete_record,
    ):
        result = delete_job(
            session=session,
            job_id=job_id,
        )

    get_record.assert_called_once_with(session, job_id)
    delete_record.assert_called_once_with(
        session,
        job=existing_job,
    )
    session.commit.assert_called_once_with()
    session.rollback.assert_not_called()

    assert result is None


def test_delete_job_raises_not_found() -> None:
    session = MagicMock(spec=Session)
    job_id = uuid4()

    with (
        patch(
            "app.services.job_service.get_job_by_id_record",
            return_value=None,
        ),
        patch(
            "app.services.job_service.delete_job_record",
        ) as delete_record,
    ):
        with pytest.raises(AppException) as exc_info:
            delete_job(
                session=session,
                job_id=job_id,
            )

    delete_record.assert_not_called()
    session.commit.assert_not_called()
    session.rollback.assert_not_called()

    assert_app_exception(
        exc_info.value,
        expected_status=status.HTTP_404_NOT_FOUND,
        expected_code="job_not_found",
        expected_message="The requested job does not exist.",
    )


def test_delete_job_rolls_back_database_error() -> None:
    session = MagicMock(spec=Session)
    existing_job = MagicMock(spec=Job)
    job_id = uuid4()

    with (
        patch(
            "app.services.job_service.get_job_by_id_record",
            return_value=existing_job,
        ),
        patch(
            "app.services.job_service.delete_job_record",
            side_effect=SQLAlchemyError("database failure"),
        ),
    ):
        with pytest.raises(AppException) as exc_info:
            delete_job(
                session=session,
                job_id=job_id,
            )

    session.rollback.assert_called_once_with()
    session.commit.assert_not_called()

    assert_app_exception(
        exc_info.value,
        expected_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        expected_code="job_deletion_failed",
        expected_message="The job could not be deleted.",
    )