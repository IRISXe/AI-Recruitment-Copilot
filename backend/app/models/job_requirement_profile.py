from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class JobRequirementProfile(Base):
    __tablename__ = "job_requirement_profiles"

    __table_args__ = (
        CheckConstraint(
            (
                "parsing_status IN "
                "('pending', 'completed', 'failed')"
            ),
            name="ck_job_requirement_profiles_parsing_status",
        ),
        UniqueConstraint(
            "job_id",
            name="uq_job_requirement_profiles_job_id",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    job_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey(
            "jobs.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    profile_data: Mapped[dict[str, object] | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    parsing_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        server_default="pending",
    )

    parsing_error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    parser_version: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    source_description_sha256: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )

    parsed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
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
