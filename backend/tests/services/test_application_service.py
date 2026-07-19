from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.models.application import Application
from app.models.candidate import Candidate
from app.models.job import Job
from app.schemas.application import ApplicationCreate, ApplicationUpdate
from app.services.application_service import (
    create_application,
    delete_application,
    get_application_by_id,
    list_applications,
    update_application,
)


def build_create_payload() -> ApplicationCreate:
    return ApplicationCreate(
        job_id=uuid4(),
        candidate_id=uuid4(),
        source="LinkedIn",
        notes="Candidate applied for the backend role.",
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


def test_create_application_validates_relations_commits_and_refreshes(
) -> None:
    session = MagicMock(spec=Session)
    job = MagicMock(spec=Job)
    candidate = MagicMock(spec=Candidate)
    application = MagicMock(spec=Application)
    payload = build_create_payload()

    with patch(
        "app.services.application_service.get_job_by_id_record",
        return_value=job,
    ) as get_job:
        with patch(
            "app.services.application_service.get_candidate_by_id_record",
            return_value=candidate,
        ) as get_candidate:
            with patch(
                "app.services.application_service."
                "get_duplicate_application_record",
                return_value=None,
            ) as get_duplicate:
                with patch(
                    "app.services.application_service."
                    "create_application_record",
                    return_value=application,
                ) as create_record:
                    result = create_application(
                        session=session,
                        payload=payload,
                    )

    get_job.assert_called_once_with(
        session,
        payload.job_id,
    )

    get_candidate.assert_called_once_with(
        session,
        payload.candidate_id,
    )

    get_duplicate.assert_called_once_with(
        session,
        job_id=payload.job_id,
        candidate_id=payload.candidate_id,
    )

    create_record.assert_called_once_with(
        session,
        payload,
    )

    session.commit.assert_called_once_with()
    session.refresh.assert_called_once_with(application)
    session.rollback.assert_not_called()

    assert result is application


def test_create_application_raises_when_job_does_not_exist() -> None:
    session = MagicMock(spec=Session)
    payload = build_create_payload()

    with patch(
        "app.services.application_service.get_job_by_id_record",
        return_value=None,
    ) as get_job:
        with patch(
            "app.services.application_service.get_candidate_by_id_record",
        ) as get_candidate:
            with patch(
                "app.services.application_service."
                "get_duplicate_application_record",
            ) as get_duplicate:
                with patch(
                    "app.services.application_service."
                    "create_application_record",
                ) as create_record:
                    with pytest.raises(AppException) as exc_info:
                        create_application(
                            session=session,
                            payload=payload,
                        )

    get_job.assert_called_once_with(
        session,
        payload.job_id,
    )

    get_candidate.assert_not_called()
    get_duplicate.assert_not_called()
    create_record.assert_not_called()

    session.commit.assert_not_called()
    session.refresh.assert_not_called()
    session.rollback.assert_not_called()

    assert_app_exception(
        exc_info.value,
        expected_status=status.HTTP_404_NOT_FOUND,
        expected_code="job_not_found",
        expected_message="The requested job does not exist.",
    )


def test_create_application_raises_when_candidate_does_not_exist(
) -> None:
    session = MagicMock(spec=Session)
    job = MagicMock(spec=Job)
    payload = build_create_payload()

    with patch(
        "app.services.application_service.get_job_by_id_record",
        return_value=job,
    ):
        with patch(
            "app.services.application_service.get_candidate_by_id_record",
            return_value=None,
        ) as get_candidate:
            with patch(
                "app.services.application_service."
                "get_duplicate_application_record",
            ) as get_duplicate:
                with patch(
                    "app.services.application_service."
                    "create_application_record",
                ) as create_record:
                    with pytest.raises(AppException) as exc_info:
                        create_application(
                            session=session,
                            payload=payload,
                        )

    get_candidate.assert_called_once_with(
        session,
        payload.candidate_id,
    )

    get_duplicate.assert_not_called()
    create_record.assert_not_called()

    session.commit.assert_not_called()
    session.refresh.assert_not_called()
    session.rollback.assert_not_called()

    assert_app_exception(
        exc_info.value,
        expected_status=status.HTTP_404_NOT_FOUND,
        expected_code="candidate_not_found",
        expected_message="The requested candidate does not exist.",
    )


def test_create_application_rejects_duplicate_application() -> None:
    session = MagicMock(spec=Session)
    job = MagicMock(spec=Job)
    candidate = MagicMock(spec=Candidate)
    existing_application = MagicMock(spec=Application)
    payload = build_create_payload()

    with patch(
        "app.services.application_service.get_job_by_id_record",
        return_value=job,
    ):
        with patch(
            "app.services.application_service.get_candidate_by_id_record",
            return_value=candidate,
        ):
            with patch(
                "app.services.application_service."
                "get_duplicate_application_record",
                return_value=existing_application,
            ):
                with patch(
                    "app.services.application_service."
                    "create_application_record",
                ) as create_record:
                    with pytest.raises(AppException) as exc_info:
                        create_application(
                            session=session,
                            payload=payload,
                        )

    create_record.assert_not_called()

    session.commit.assert_not_called()
    session.refresh.assert_not_called()
    session.rollback.assert_not_called()

    assert_app_exception(
        exc_info.value,
        expected_status=status.HTTP_409_CONFLICT,
        expected_code="application_already_exists",
        expected_message=(
            "This candidate has already applied to this job."
        ),
    )


def test_create_application_rolls_back_database_error() -> None:
    session = MagicMock(spec=Session)
    payload = build_create_payload()

    with patch(
        "app.services.application_service.get_job_by_id_record",
        side_effect=SQLAlchemyError("database failure"),
    ):
        with pytest.raises(AppException) as exc_info:
            create_application(
                session=session,
                payload=payload,
            )

    session.rollback.assert_called_once_with()
    session.commit.assert_not_called()
    session.refresh.assert_not_called()

    assert_app_exception(
        exc_info.value,
        expected_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        expected_code="application_creation_failed",
        expected_message="The application could not be created.",
    )


def test_get_application_by_id_returns_existing_application() -> None:
    session = MagicMock(spec=Session)
    application = MagicMock(spec=Application)
    application_id = uuid4()

    with patch(
        "app.services.application_service.get_application_by_id_record",
        return_value=application,
    ) as get_record:
        result = get_application_by_id(
            session=session,
            application_id=application_id,
        )

    get_record.assert_called_once_with(
        session,
        application_id,
    )

    session.rollback.assert_not_called()

    assert result is application


def test_get_application_by_id_raises_not_found() -> None:
    session = MagicMock(spec=Session)
    application_id = uuid4()

    with patch(
        "app.services.application_service.get_application_by_id_record",
        return_value=None,
    ):
        with pytest.raises(AppException) as exc_info:
            get_application_by_id(
                session=session,
                application_id=application_id,
            )

    session.rollback.assert_not_called()

    assert_app_exception(
        exc_info.value,
        expected_status=status.HTTP_404_NOT_FOUND,
        expected_code="application_not_found",
        expected_message="The requested application does not exist.",
    )


def test_get_application_by_id_rolls_back_database_error() -> None:
    session = MagicMock(spec=Session)
    application_id = uuid4()

    with patch(
        "app.services.application_service.get_application_by_id_record",
        side_effect=SQLAlchemyError("database failure"),
    ):
        with pytest.raises(AppException) as exc_info:
            get_application_by_id(
                session=session,
                application_id=application_id,
            )

    session.rollback.assert_called_once_with()

    assert_app_exception(
        exc_info.value,
        expected_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        expected_code="application_retrieval_failed",
        expected_message="The application could not be retrieved.",
    )



def test_list_applications_returns_repository_results() -> None:
    session = MagicMock(spec=Session)
    job_id = uuid4()
    candidate_id = uuid4()

    applications = [
        MagicMock(spec=Application),
        MagicMock(spec=Application),
    ]

    with patch(
        "app.services.application_service.list_applications_records",
        return_value=applications,
    ) as list_records:
        result = list_applications(
            session=session,
            offset=10,
            limit=20,
            job_id=job_id,
            candidate_id=candidate_id,
            application_status="screening",
        )

    list_records.assert_called_once_with(
        session,
        offset=10,
        limit=20,
        job_id=job_id,
        candidate_id=candidate_id,
        application_status="screening",
    )

    session.rollback.assert_not_called()

    assert result is applications

def test_list_applications_rolls_back_database_error() -> None:
    session = MagicMock(spec=Session)

    with patch(
        "app.services.application_service.list_applications_records",
        side_effect=SQLAlchemyError("database failure"),
    ):
        with pytest.raises(AppException) as exc_info:
            list_applications(
                session=session,
                offset=0,
                limit=20,
            )

    session.rollback.assert_called_once_with()

    assert_app_exception(
        exc_info.value,
        expected_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        expected_code="application_listing_failed",
        expected_message="The applications could not be retrieved.",
    )


def test_update_application_commits_refreshes_and_returns_application(
) -> None:
    session = MagicMock(spec=Session)
    application = MagicMock(spec=Application)
    application.status = "applied"
    updated_application = MagicMock(spec=Application)
    application_id = uuid4()

    payload = ApplicationUpdate(
        status="screening",
        notes="Candidate moved to screening.",
    )

    with patch(
        "app.services.application_service.get_application_by_id_record",
        return_value=application,
    ) as get_record:
        with patch(
            "app.services.application_service.update_application_record",
            return_value=updated_application,
        ) as update_record:
            result = update_application(
                session=session,
                application_id=application_id,
                payload=payload,
            )

    get_record.assert_called_once_with(
        session,
        application_id,
    )

    update_record.assert_called_once_with(
        session,
        application=application,
        payload=payload,
    )

    session.commit.assert_called_once_with()
    session.refresh.assert_called_once_with(updated_application)
    session.rollback.assert_not_called()

    assert result is updated_application


def test_update_application_raises_not_found() -> None:
    session = MagicMock(spec=Session)
    application_id = uuid4()
    payload = ApplicationUpdate(status="screening")

    with patch(
        "app.services.application_service.get_application_by_id_record",
        return_value=None,
    ) as get_record:
        with patch(
            "app.services.application_service.update_application_record",
        ) as update_record:
            with pytest.raises(AppException) as exc_info:
                update_application(
                    session=session,
                    application_id=application_id,
                    payload=payload,
                )

    get_record.assert_called_once_with(
        session,
        application_id,
    )

    update_record.assert_not_called()

    session.commit.assert_not_called()
    session.refresh.assert_not_called()
    session.rollback.assert_not_called()

    assert_app_exception(
        exc_info.value,
        expected_status=status.HTTP_404_NOT_FOUND,
        expected_code="application_not_found",
        expected_message="The requested application does not exist.",
    )


def test_update_application_rolls_back_database_error() -> None:
    session = MagicMock(spec=Session)
    application = MagicMock(spec=Application)
    application.status = "applied"
    application_id = uuid4()
    payload = ApplicationUpdate(status="screening")

    with patch(
        "app.services.application_service.get_application_by_id_record",
        return_value=application,
    ):
        with patch(
            "app.services.application_service.update_application_record",
            side_effect=SQLAlchemyError("database failure"),
        ):
            with pytest.raises(AppException) as exc_info:
                update_application(
                    session=session,
                    application_id=application_id,
                    payload=payload,
                )

    session.rollback.assert_called_once_with()
    session.commit.assert_not_called()
    session.refresh.assert_not_called()

    assert_app_exception(
        exc_info.value,
        expected_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        expected_code="application_update_failed",
        expected_message="The application could not be updated.",
    )


def test_delete_application_commits_and_returns_none() -> None:
    session = MagicMock(spec=Session)
    application = MagicMock(spec=Application)
    application_id = uuid4()

    with patch(
        "app.services.application_service.get_application_by_id_record",
        return_value=application,
    ) as get_record:
        with patch(
            "app.services.application_service.delete_application_record",
        ) as delete_record:
            result = delete_application(
                session=session,
                application_id=application_id,
            )

    get_record.assert_called_once_with(
        session,
        application_id,
    )

    delete_record.assert_called_once_with(
        session,
        application=application,
    )

    session.commit.assert_called_once_with()
    session.rollback.assert_not_called()

    assert result is None


def test_delete_application_raises_not_found() -> None:
    session = MagicMock(spec=Session)
    application_id = uuid4()

    with patch(
        "app.services.application_service.get_application_by_id_record",
        return_value=None,
    ) as get_record:
        with patch(
            "app.services.application_service.delete_application_record",
        ) as delete_record:
            with pytest.raises(AppException) as exc_info:
                delete_application(
                    session=session,
                    application_id=application_id,
                )

    get_record.assert_called_once_with(
        session,
        application_id,
    )

    delete_record.assert_not_called()

    session.commit.assert_not_called()
    session.rollback.assert_not_called()

    assert_app_exception(
        exc_info.value,
        expected_status=status.HTTP_404_NOT_FOUND,
        expected_code="application_not_found",
        expected_message="The requested application does not exist.",
    )


def test_delete_application_rolls_back_database_error() -> None:
    session = MagicMock(spec=Session)
    application = MagicMock(spec=Application)
    application_id = uuid4()

    with patch(
        "app.services.application_service.get_application_by_id_record",
        return_value=application,
    ):
        with patch(
            "app.services.application_service.delete_application_record",
            side_effect=SQLAlchemyError("database failure"),
        ):
            with pytest.raises(AppException) as exc_info:
                delete_application(
                    session=session,
                    application_id=application_id,
                )

    session.rollback.assert_called_once_with()
    session.commit.assert_not_called()

    assert_app_exception(
        exc_info.value,
        expected_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        expected_code="application_deletion_failed",
        expected_message="The application could not be deleted.",
    )


def test_update_application_rejects_invalid_status_transition() -> None:
    session = MagicMock(spec=Session)
    application_id = uuid4()
    application = MagicMock(spec=Application)
    application.status = "applied"

    payload = ApplicationUpdate(status="hired")

    with patch(
        "app.services.application_service.get_application_by_id_record",
        return_value=application,
    ):
        with patch(
            "app.services.application_service.update_application_record",
        ) as update_record:
            with pytest.raises(AppException) as exc_info:
                update_application(
                    session=session,
                    application_id=application_id,
                    payload=payload,
                )

    update_record.assert_not_called()
    session.commit.assert_not_called()
    session.refresh.assert_not_called()
    session.rollback.assert_not_called()

    assert_app_exception(
        exc_info.value,
        expected_status=status.HTTP_409_CONFLICT,
        expected_code="invalid_application_status_transition",
        expected_message=(
            "Application status cannot transition "
            "from 'applied' to 'hired'."
        ),
    )


@pytest.mark.parametrize(
    "terminal_status",
    [
        "hired",
        "rejected",
        "withdrawn",
    ],
)
def test_update_application_rejects_transition_from_terminal_status(
    terminal_status: str,
) -> None:
    session = MagicMock(spec=Session)
    application_id = uuid4()
    application = MagicMock(spec=Application)
    application.status = terminal_status

    payload = ApplicationUpdate(status="screening")

    with patch(
        "app.services.application_service.get_application_by_id_record",
        return_value=application,
    ):
        with patch(
            "app.services.application_service.update_application_record",
        ) as update_record:
            with pytest.raises(AppException) as exc_info:
                update_application(
                    session=session,
                    application_id=application_id,
                    payload=payload,
                )

    update_record.assert_not_called()
    session.commit.assert_not_called()
    session.refresh.assert_not_called()
    session.rollback.assert_not_called()

    assert exc_info.value.status_code == status.HTTP_409_CONFLICT
    assert (
        exc_info.value.code
        == "invalid_application_status_transition"
    )
