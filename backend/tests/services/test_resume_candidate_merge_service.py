from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.schemas.resume_profile import ResumeCandidateMergeRequest
from app.services.resume_candidate_merge_service import (
    merge_resume_profile_into_candidate,
)


def _candidate() -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        full_name="Existing Name",
        email="existing@example.com",
        phone=None,
        current_location=None,
        current_role=None,
        total_experience_months=0,
        skills=["React.js"],
    )


def _profile() -> SimpleNamespace:
    return SimpleNamespace(
        parsing_status="completed",
        profile_data={
            "full_name": "Parsed Name",
            "email": "parsed@example.com",
            "phone": "+919876543210",
            "location": "Hyderabad",
            "current_role": "Backend Developer",
            "total_experience_months": 30,
            "skills": ["React.js", "FastAPI", "PostgreSQL"],
        },
    )


def test_merge_protects_existing_values_and_merges_skills() -> None:
    session = MagicMock(spec=Session)
    resume_id = uuid4()
    candidate = _candidate()
    resume = SimpleNamespace(candidate_id=candidate.id)
    payload = ResumeCandidateMergeRequest(
        fields=[
            "full_name",
            "email",
            "phone",
            "current_location",
            "current_role",
            "total_experience_months",
            "skills",
        ],
        overwrite_existing=False,
    )

    with patch(
        "app.services.resume_candidate_merge_service.get_resume_by_id_record",
        return_value=resume,
    ), patch(
        "app.services.resume_candidate_merge_service.get_resume_profile_record",
        return_value=_profile(),
    ), patch(
        "app.services.resume_candidate_merge_service.get_candidate_by_id_record",
        return_value=candidate,
    ), patch(
        "app.services.resume_candidate_merge_service.get_candidate_by_email",
        return_value=None,
    ), patch(
        "app.services.resume_candidate_merge_service.apply_candidate_profile_updates",
        return_value=candidate,
    ) as update_record:
        result = merge_resume_profile_into_candidate(
            session,
            resume_id=resume_id,
            payload=payload,
        )

    assert result is candidate
    updates = update_record.call_args.kwargs["updates"]
    assert "full_name" not in updates
    assert "email" not in updates
    assert updates["phone"] == "+919876543210"
    assert updates["current_location"] == "Hyderabad"
    assert updates["current_role"] == "Backend Developer"
    assert updates["total_experience_months"] == 30
    assert updates["skills"] == [
        "React.js",
        "FastAPI",
        "PostgreSQL",
    ]
    session.commit.assert_called_once_with()
    session.refresh.assert_called_once_with(candidate)


def test_merge_overwrites_selected_existing_fields() -> None:
    session = MagicMock(spec=Session)
    resume_id = uuid4()
    candidate = _candidate()
    payload = ResumeCandidateMergeRequest(
        fields=["full_name", "email", "skills"],
        overwrite_existing=True,
    )

    with patch(
        "app.services.resume_candidate_merge_service.get_resume_by_id_record",
        return_value=SimpleNamespace(candidate_id=candidate.id),
    ), patch(
        "app.services.resume_candidate_merge_service.get_resume_profile_record",
        return_value=_profile(),
    ), patch(
        "app.services.resume_candidate_merge_service.get_candidate_by_id_record",
        return_value=candidate,
    ), patch(
        "app.services.resume_candidate_merge_service.get_candidate_by_email",
        return_value=None,
    ), patch(
        "app.services.resume_candidate_merge_service.apply_candidate_profile_updates",
        return_value=candidate,
    ) as update_record:
        merge_resume_profile_into_candidate(
            session,
            resume_id=resume_id,
            payload=payload,
        )

    assert update_record.call_args.kwargs["updates"] == {
        "full_name": "Parsed Name",
        "email": "parsed@example.com",
        "skills": ["React.js", "FastAPI", "PostgreSQL"],
    }


def test_merge_rejects_duplicate_candidate_email() -> None:
    session = MagicMock(spec=Session)
    resume_id = uuid4()
    candidate = _candidate()
    payload = ResumeCandidateMergeRequest(
        fields=["email"],
        overwrite_existing=True,
    )

    with patch(
        "app.services.resume_candidate_merge_service.get_resume_by_id_record",
        return_value=SimpleNamespace(candidate_id=candidate.id),
    ), patch(
        "app.services.resume_candidate_merge_service.get_resume_profile_record",
        return_value=_profile(),
    ), patch(
        "app.services.resume_candidate_merge_service.get_candidate_by_id_record",
        return_value=candidate,
    ), patch(
        "app.services.resume_candidate_merge_service.get_candidate_by_email",
        return_value=SimpleNamespace(id=uuid4()),
    ):
        with pytest.raises(AppException) as exc_info:
            merge_resume_profile_into_candidate(
                session,
                resume_id=resume_id,
                payload=payload,
            )

    assert exc_info.value.status_code == 409
    assert exc_info.value.code == "candidate_email_exists"
    session.commit.assert_not_called()


def test_merge_rolls_back_database_failure() -> None:
    session = MagicMock(spec=Session)
    resume_id = uuid4()
    candidate = _candidate()
    payload = ResumeCandidateMergeRequest(
        fields=["phone"],
    )

    with patch(
        "app.services.resume_candidate_merge_service.get_resume_by_id_record",
        return_value=SimpleNamespace(candidate_id=candidate.id),
    ), patch(
        "app.services.resume_candidate_merge_service.get_resume_profile_record",
        return_value=_profile(),
    ), patch(
        "app.services.resume_candidate_merge_service.get_candidate_by_id_record",
        return_value=candidate,
    ), patch(
        "app.services.resume_candidate_merge_service.apply_candidate_profile_updates",
        side_effect=SQLAlchemyError("database failure"),
    ):
        with pytest.raises(AppException) as exc_info:
            merge_resume_profile_into_candidate(
                session,
                resume_id=resume_id,
                payload=payload,
            )

    assert exc_info.value.status_code == 500
    assert exc_info.value.code == "candidate_merge_database_error"
    session.rollback.assert_called_once_with()