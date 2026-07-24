from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CandidateJobMatch(Base):
    __tablename__ = "candidate_job_matches"

    __table_args__ = (
        CheckConstraint(
            "overall_score BETWEEN 0 AND 100",
            name="ck_candidate_job_matches_overall_score_range",
        ),
        CheckConstraint(
            "skill_score BETWEEN 0 AND 100",
            name="ck_candidate_job_matches_skill_score_range",
        ),
        CheckConstraint(
            "experience_score BETWEEN 0 AND 100",
            name="ck_candidate_job_matches_experience_score_range",
        ),
        CheckConstraint(
            "education_score BETWEEN 0 AND 100",
            name="ck_candidate_job_matches_education_score_range",
        ),
        CheckConstraint(
            "certification_score BETWEEN 0 AND 100",
            name="ck_candidate_job_matches_certification_score_range",
        ),
        CheckConstraint(
            "location_score BETWEEN 0 AND 100",
            name="ck_candidate_job_matches_location_score_range",
        ),
        CheckConstraint(
            "work_mode_score BETWEEN 0 AND 100",
            name="ck_candidate_job_matches_work_mode_score_range",
        ),
        CheckConstraint(
            "confidence_score BETWEEN 0 AND 100",
            name="ck_candidate_job_matches_confidence_score_range",
        ),
        CheckConstraint(
            "recommendation IN "
            "('strong_match', 'good_match', 'partial_match', "
            "'weak_match', 'insufficient_data')",
            name="ck_candidate_job_matches_recommendation",
        ),
        UniqueConstraint(
            "candidate_id",
            "job_id",
            name="uq_candidate_job_matches_candidate_job",
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

    resume_profile_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey(
            "resume_profiles.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    job_requirement_profile_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey(
            "job_requirement_profiles.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    overall_score: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False,
    )

    skill_score: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False,
    )

    experience_score: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False,
    )

    education_score: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False,
    )

    certification_score: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False,
    )

    location_score: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False,
    )

    work_mode_score: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False,
    )

    confidence_score: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False,
    )

    recommendation: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    analysis_data: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    scoring_version: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    source_resume_text_sha256: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    source_resume_parser_version: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    source_job_description_sha256: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    source_job_parser_version: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    matched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
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