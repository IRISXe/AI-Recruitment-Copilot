"""create candidate ai analyses table

Revision ID: c2f4a8d91e6b
Revises: 5cadf093cbff
Create Date: 2026-08-03 13:33:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "c2f4a8d91e6b"
down_revision: Union[
    str,
    Sequence[str],
    None,
] = "5cadf093cbff"
branch_labels: Union[
    str,
    Sequence[str],
    None,
] = None
depends_on: Union[
    str,
    Sequence[str],
    None,
] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "candidate_ai_analyses",
        sa.Column(
            "id",
            sa.UUID(),
            nullable=False,
        ),
        sa.Column(
            "candidate_id",
            sa.UUID(),
            nullable=False,
        ),
        sa.Column(
            "job_id",
            sa.UUID(),
            nullable=False,
        ),
        sa.Column(
            "resume_id",
            sa.UUID(),
            nullable=False,
        ),
        sa.Column(
            "candidate_job_match_id",
            sa.UUID(),
            nullable=False,
        ),
        sa.Column(
            "analysis_data",
            postgresql.JSONB(
                astext_type=sa.Text()
            ),
            nullable=True,
        ),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default=sa.text("'pending'"),
            nullable=False,
        ),
        sa.Column(
            "provider",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column(
            "model_name",
            sa.String(length=200),
            nullable=False,
        ),
        sa.Column(
            "prompt_version",
            sa.String(length=50),
            nullable=False,
        ),
        sa.Column(
            "input_fingerprint_sha256",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column(
            "source_match_updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "source_scoring_version",
            sa.String(length=50),
            nullable=False,
        ),
        sa.Column(
            "source_resume_profile_hash",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column(
            "source_job_profile_hash",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column(
            "input_tokens",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "output_tokens",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "total_tokens",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "estimated_cost",
            sa.Numeric(
                precision=14,
                scale=8,
            ),
            nullable=True,
        ),
        sa.Column(
            "processing_time_ms",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "error_code",
            sa.String(length=100),
            nullable=True,
        ),
        sa.Column(
            "error_message",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "generated_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            (
                "status IN "
                "('pending', 'completed', 'failed')"
            ),
            name="ck_candidate_ai_analyses_status",
        ),
        sa.CheckConstraint(
            (
                "input_tokens IS NULL "
                "OR input_tokens >= 0"
            ),
            name=(
                "ck_candidate_ai_analyses_"
                "input_tokens_nonnegative"
            ),
        ),
        sa.CheckConstraint(
            (
                "output_tokens IS NULL "
                "OR output_tokens >= 0"
            ),
            name=(
                "ck_candidate_ai_analyses_"
                "output_tokens_nonnegative"
            ),
        ),
        sa.CheckConstraint(
            (
                "total_tokens IS NULL "
                "OR total_tokens >= 0"
            ),
            name=(
                "ck_candidate_ai_analyses_"
                "total_tokens_nonnegative"
            ),
        ),
        sa.CheckConstraint(
            (
                "estimated_cost IS NULL "
                "OR estimated_cost >= 0"
            ),
            name=(
                "ck_candidate_ai_analyses_"
                "estimated_cost_nonnegative"
            ),
        ),
        sa.CheckConstraint(
            (
                "processing_time_ms IS NULL "
                "OR processing_time_ms >= 0"
            ),
            name=(
                "ck_candidate_ai_analyses_"
                "processing_time_ms_nonnegative"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["candidate_id"],
            ["candidates.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["job_id"],
            ["jobs.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["resume_id"],
            ["resumes.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["candidate_job_match_id"],
            ["candidate_job_matches.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "candidate_id",
            "job_id",
            name=(
                "uq_candidate_ai_analyses_"
                "candidate_job"
            ),
        ),
    )

    op.create_index(
        op.f(
            "ix_candidate_ai_analyses_"
            "candidate_id"
        ),
        "candidate_ai_analyses",
        ["candidate_id"],
        unique=False,
    )

    op.create_index(
        op.f(
            "ix_candidate_ai_analyses_"
            "job_id"
        ),
        "candidate_ai_analyses",
        ["job_id"],
        unique=False,
    )

    op.create_index(
        op.f(
            "ix_candidate_ai_analyses_"
            "candidate_job_match_id"
        ),
        "candidate_ai_analyses",
        ["candidate_job_match_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        op.f(
            "ix_candidate_ai_analyses_"
            "candidate_job_match_id"
        ),
        table_name="candidate_ai_analyses",
    )

    op.drop_index(
        op.f(
            "ix_candidate_ai_analyses_"
            "job_id"
        ),
        table_name="candidate_ai_analyses",
    )

    op.drop_index(
        op.f(
            "ix_candidate_ai_analyses_"
            "candidate_id"
        ),
        table_name="candidate_ai_analyses",
    )

    op.drop_table("candidate_ai_analyses")