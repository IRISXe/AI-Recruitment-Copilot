from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.candidate import Candidate


MERGEABLE_CANDIDATE_FIELDS = {
    "full_name",
    "email",
    "phone",
    "current_location",
    "current_role",
    "total_experience_months",
    "skills",
}


def get_candidate_by_email(
    session: Session,
    *,
    email: str,
    exclude_candidate_id: UUID | None = None,
) -> Candidate | None:
    statement = select(Candidate).where(
        Candidate.email == email
    )

    if exclude_candidate_id is not None:
        statement = statement.where(
            Candidate.id != exclude_candidate_id
        )

    return session.scalar(statement)


def apply_candidate_profile_updates(
    session: Session,
    *,
    candidate: Candidate,
    updates: dict[str, object],
) -> Candidate:
    unknown_fields = set(updates) - MERGEABLE_CANDIDATE_FIELDS

    if unknown_fields:
        raise ValueError(
            "Unsupported Candidate merge fields: "
            f"{', '.join(sorted(unknown_fields))}."
        )

    for field_name, value in updates.items():
        setattr(candidate, field_name, value)

    session.add(candidate)

    return candidate