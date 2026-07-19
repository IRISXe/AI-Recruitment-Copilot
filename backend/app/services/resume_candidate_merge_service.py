from uuid import UUID

from fastapi import status
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.models.candidate import Candidate
from app.repositories.candidate_repository import (
    get_candidate_by_id as get_candidate_by_id_record,
)
from app.repositories.resume_candidate_merge_repository import (
    apply_candidate_profile_updates,
    get_candidate_by_email,
)
from app.repositories.resume_profile_state_repository import (
    get_resume_profile_by_resume_id as get_resume_profile_record,
)
from app.repositories.resume_repository import (
    get_resume_by_id as get_resume_by_id_record,
)
from app.schemas.resume_profile import (
    ResumeCandidateMergeRequest,
    ResumeProfileData,
)


def _has_existing_candidate_value(
    field_name: str,
    value: object,
) -> bool:
    if value is None:
        return False

    if isinstance(value, str):
        return bool(value.strip())

    if field_name == "total_experience_months":
        return isinstance(value, int) and value > 0

    if isinstance(value, list):
        return bool(value)

    return True


def _has_parsed_value(value: object) -> bool:
    if value is None:
        return False

    if isinstance(value, str):
        return bool(value.strip())

    if isinstance(value, list):
        return bool(value)

    return True


def _merge_skills(
    existing_skills: list[str],
    parsed_skills: list[str],
    *,
    overwrite_existing: bool,
) -> list[str]:
    source_skills = (
        [] if overwrite_existing else existing_skills
    ) + parsed_skills
    merged_skills: list[str] = []
    seen: set[str] = set()

    for skill in source_skills:
        normalized_skill = skill.strip()

        if not normalized_skill:
            continue

        duplicate_key = normalized_skill.casefold()

        if duplicate_key in seen:
            continue

        seen.add(duplicate_key)
        merged_skills.append(normalized_skill)

    return merged_skills


def merge_resume_profile_into_candidate(
    session: Session,
    *,
    resume_id: UUID,
    payload: ResumeCandidateMergeRequest,
) -> Candidate:
    try:
        resume = get_resume_by_id_record(session, resume_id)

        if resume is None:
            raise AppException(
                status_code=status.HTTP_404_NOT_FOUND,
                code="resume_not_found",
                message="The requested resume does not exist.",
            )

        resume_profile = get_resume_profile_record(
            session,
            resume_id=resume_id,
        )

        if resume_profile is None:
            raise AppException(
                status_code=status.HTTP_404_NOT_FOUND,
                code="resume_profile_not_found",
                message=(
                    "A structured profile is not available "
                    "for this resume."
                ),
            )

        if resume_profile.parsing_status != "completed":
            raise AppException(
                status_code=status.HTTP_409_CONFLICT,
                code="resume_profile_not_ready",
                message=(
                    "Resume parsing must be completed "
                    "before Candidate merging."
                ),
            )

        if not resume_profile.profile_data:
            raise AppException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                code="resume_profile_empty",
                message="The structured Resume profile is empty.",
            )

        candidate = get_candidate_by_id_record(
            session,
            resume.candidate_id,
        )

        if candidate is None:
            raise AppException(
                status_code=status.HTTP_404_NOT_FOUND,
                code="candidate_not_found",
                message="The Resume Candidate does not exist.",
            )

        profile_data = ResumeProfileData.model_validate(
            resume_profile.profile_data
        )
        parsed_values: dict[str, object] = {
            "full_name": profile_data.full_name,
            "email": (
                str(profile_data.email)
                if profile_data.email is not None
                else None
            ),
            "phone": profile_data.phone,
            "current_location": profile_data.location,
            "current_role": profile_data.current_role,
            "total_experience_months": (
                profile_data.total_experience_months
            ),
            "skills": profile_data.skills,
        }
        updates: dict[str, object] = {}

        for field_name in payload.fields:
            parsed_value = parsed_values[field_name]

            if not _has_parsed_value(parsed_value):
                continue

            if field_name == "skills":
                updates[field_name] = _merge_skills(
                    candidate.skills or [],
                    profile_data.skills,
                    overwrite_existing=payload.overwrite_existing,
                )
                continue

            existing_value = getattr(candidate, field_name)

            if (
                not payload.overwrite_existing
                and _has_existing_candidate_value(
                    field_name,
                    existing_value,
                )
            ):
                continue

            updates[field_name] = parsed_value

        requested_email = updates.get("email")

        if isinstance(requested_email, str):
            duplicate_candidate = get_candidate_by_email(
                session,
                email=requested_email,
                exclude_candidate_id=candidate.id,
            )

            if duplicate_candidate is not None:
                raise AppException(
                    status_code=status.HTTP_409_CONFLICT,
                    code="candidate_email_exists",
                    message=(
                        "Another Candidate already uses "
                        "the parsed email address."
                    ),
                )

        updated_candidate = apply_candidate_profile_updates(
            session,
            candidate=candidate,
            updates=updates,
        )

        session.commit()
        session.refresh(updated_candidate)

        return updated_candidate

    except AppException:
        raise
    except IntegrityError as exc:
        session.rollback()

        raise AppException(
            status_code=status.HTTP_409_CONFLICT,
            code="candidate_email_exists",
            message=(
                "Another Candidate already uses "
                "the parsed email address."
            ),
        ) from exc
    except SQLAlchemyError as exc:
        session.rollback()

        raise AppException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="candidate_merge_database_error",
            message=(
                "The Resume profile could not be merged "
                "into the Candidate."
            ),
        ) from exc