from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CandidateAIAnalysis(Base):
    __tablename__ = "candidate_ai_analyses"

    __table_args__ = (
        CheckConstraint(
            (
                "status IN "
                "('pending', 'completed', 'failed')"
            ),
            name="ck_candidate_ai_analyses_status",
        ),
        CheckConstraint(
            (
                "input_tokens IS NULL "
                "OR input_tokens >= 0"
            ),
            name=(
                "ck_candidate_ai_analyses_"
                "input_tokens_nonnegative"
            ),
        ),
        CheckConstraint(
            (
                "output_tokens IS NULL "
                "OR output_tokens >= 0"
            ),
            name=(
                "ck_candidate_ai_analyses_"
                "output_tokens_nonnegative"
            ),
        ),
        CheckConstraint(
            (
                "total_tokens IS NULL "
                "OR total_tokens >= 0"
            ),
            name=(
                "ck_candidate_ai_analyses_"
                "total_tokens_nonnegative"
            ),
        ),
        CheckConstraint(
            (
                "estimated_cost IS NULL "
                "OR estimated_cost >= 0"
            ),
            name=(
                "ck_candidate_ai_analyses_"
                "estimated_cost_nonnegative"
            ),
        ),
        CheckConstraint(
            (
                "processing_time_ms IS NULL "
                "OR processing_time_ms >= 0"
            ),
            name=(
                "ck_candidate_ai_analyses_"
                "processing_time_ms_nonnegative"
            ),
        ),
        UniqueConstraint(
            "candidate_id",
            "job_id",
            name=(
                "uq_candidate_ai_analyses_"
                "candidate_job"
            ),
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    candidate_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey(
            "candidates.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
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

    resume_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey(
            "resumes.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    candidate_job_match_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey(
            "candidate_job_matches.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    analysis_data: Mapped[
        dict[str, object] | None
    ] = mapped_column(
        JSONB,
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        server_default="pending",
    )

    provider: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    model_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    prompt_version: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    input_fingerprint_sha256: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    source_match_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    source_scoring_version: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    source_resume_profile_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    source_job_profile_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    input_tokens: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    output_tokens: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    total_tokens: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    estimated_cost: Mapped[Decimal | None] = mapped_column(
        Numeric(
            precision=14,
            scale=8,
        ),
        nullable=True,
    )

    processing_time_ms: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    error_code: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    generated_at: Mapped[datetime | None] = mapped_column(
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