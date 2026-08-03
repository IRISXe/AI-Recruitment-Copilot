from sqlalchemy import (
    CheckConstraint,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB

from app.models import (
    CandidateAIAnalysis as ExportedCandidateAIAnalysis,
)
from app.models.candidate_ai_analysis import (
    CandidateAIAnalysis,
)


def test_candidate_ai_analysis_is_exported() -> None:
    assert (
        ExportedCandidateAIAnalysis
        is CandidateAIAnalysis
    )


def test_candidate_ai_analysis_uses_expected_table() -> None:
    assert (
        CandidateAIAnalysis.__tablename__
        == "candidate_ai_analyses"
    )


def test_candidate_ai_analysis_has_expected_columns(
) -> None:
    column_names = set(
        CandidateAIAnalysis.__table__.columns.keys()
    )

    assert column_names == {
        "id",
        "candidate_id",
        "job_id",
        "resume_id",
        "candidate_job_match_id",
        "analysis_data",
        "status",
        "provider",
        "model_name",
        "prompt_version",
        "input_fingerprint_sha256",
        "source_match_updated_at",
        "source_scoring_version",
        "source_resume_profile_hash",
        "source_job_profile_hash",
        "input_tokens",
        "output_tokens",
        "total_tokens",
        "estimated_cost",
        "processing_time_ms",
        "error_code",
        "error_message",
        "generated_at",
        "created_at",
        "updated_at",
    }


def test_candidate_ai_analysis_uses_jsonb_output(
) -> None:
    analysis_data_column = (
        CandidateAIAnalysis.__table__.c.analysis_data
    )

    assert isinstance(
        analysis_data_column.type,
        JSONB,
    )
    assert analysis_data_column.nullable is True


def test_candidate_ai_analysis_has_status_constraint(
) -> None:
    constraints = {
        constraint.name: constraint
        for constraint
        in CandidateAIAnalysis.__table__.constraints
        if isinstance(
            constraint,
            CheckConstraint,
        )
    }

    assert "ck_candidate_ai_analyses_status" in constraints
    assert (
        "completed"
        in str(
            constraints[
                "ck_candidate_ai_analyses_status"
            ].sqltext
        )
    )
    assert (
        "failed"
        in str(
            constraints[
                "ck_candidate_ai_analyses_status"
            ].sqltext
        )
    )


def test_candidate_ai_analysis_has_unique_pair(
) -> None:
    unique_constraints = {
        constraint.name: tuple(
            column.name
            for column in constraint.columns
        )
        for constraint
        in CandidateAIAnalysis.__table__.constraints
        if isinstance(
            constraint,
            UniqueConstraint,
        )
    }

    assert unique_constraints[
        "uq_candidate_ai_analyses_candidate_job"
    ] == (
        "candidate_id",
        "job_id",
    )


def test_candidate_ai_analysis_foreign_keys_cascade(
) -> None:
    foreign_keys = {
        foreign_key.parent.name: foreign_key
        for foreign_key
        in CandidateAIAnalysis.__table__.foreign_keys
    }

    expected_targets = {
        "candidate_id": "candidates",
        "job_id": "jobs",
        "resume_id": "resumes",
        "candidate_job_match_id": (
            "candidate_job_matches"
        ),
    }

    for column_name, table_name in (
        expected_targets.items()
    ):
        foreign_key = foreign_keys[column_name]

        assert foreign_key.column.table.name == table_name
        assert foreign_key.ondelete == "CASCADE"


def test_candidate_ai_analysis_tracks_generation_metadata(
) -> None:
    table = CandidateAIAnalysis.__table__

    assert table.c.provider.nullable is False
    assert table.c.model_name.nullable is False
    assert table.c.prompt_version.nullable is False

    assert (
        table.c.input_fingerprint_sha256.nullable
        is False
    )

    assert table.c.input_tokens.nullable is True
    assert table.c.output_tokens.nullable is True
    assert table.c.total_tokens.nullable is True
    assert table.c.estimated_cost.nullable is True
    assert table.c.processing_time_ms.nullable is True

    assert table.c.error_code.nullable is True
    assert table.c.error_message.nullable is True
    assert table.c.generated_at.nullable is True