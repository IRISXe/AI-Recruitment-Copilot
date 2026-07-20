from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Job(Base):
    __tablename__ = "jobs"

    __table_args__ = (
        CheckConstraint(
            "employment_type IN "
            "('full_time', 'part_time', 'contract', 'internship')",
            name="ck_jobs_employment_type",
        ),
        CheckConstraint(
            "minimum_experience BETWEEN 0 AND 50",
            name="ck_jobs_minimum_experience_range",
        ),
        CheckConstraint(
            "cardinality(required_skills) BETWEEN 1 AND 20",
            name="ck_jobs_required_skills_count",
        ),
        CheckConstraint(
            "cardinality(preferred_skills) <= 20",
            name="ck_jobs_preferred_skills_count",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    title: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    department: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    location: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    employment_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    minimum_experience: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    required_skills: Mapped[list[str]] = mapped_column(
        ARRAY(String(100)),
        nullable=False,
    )

    preferred_skills: Mapped[list[str]] = mapped_column(
        ARRAY(String(100)),
        nullable=False,
        default=list,
        server_default="{}",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )