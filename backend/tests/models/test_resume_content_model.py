from sqlalchemy import CheckConstraint, UniqueConstraint

from app.models.resume_content import ResumeContent


def test_resume_content_uses_expected_table_and_columns() -> None:
    assert ResumeContent.__tablename__ == "resume_contents"

    assert list(
        ResumeContent.__table__.columns.keys()
    ) == [
        "id",
        "resume_id",
        "extracted_text",
        "extraction_status",
        "extraction_error",
        "extractor_version",
        "extracted_at",
        "created_at",
        "updated_at",
    ]


def test_resume_content_resume_id_foreign_key_cascades() -> None:
    foreign_key = next(
        iter(
            ResumeContent.__table__.c.resume_id.foreign_keys
        )
    )

    assert foreign_key.target_fullname == "resumes.id"
    assert foreign_key.ondelete == "CASCADE"


def test_resume_content_resume_id_is_unique() -> None:
    unique_constraints = [
        constraint
        for constraint in ResumeContent.__table__.constraints
        if isinstance(
            constraint,
            UniqueConstraint,
        )
    ]

    assert any(
        constraint.name
        == "uq_resume_contents_resume_id"
        for constraint in unique_constraints
    )


def test_resume_content_has_status_check_constraint() -> None:
    check_constraints = [
        constraint
        for constraint in ResumeContent.__table__.constraints
        if isinstance(
            constraint,
            CheckConstraint,
        )
    ]

    status_constraint = next(
        constraint
        for constraint in check_constraints
        if (
            constraint.name
            == "ck_resume_contents_extraction_status"
        )
    )

    constraint_sql = str(
        status_constraint.sqltext
    )

    assert "pending" in constraint_sql
    assert "completed" in constraint_sql
    assert "failed" in constraint_sql


def test_resume_content_column_nullability() -> None:
    columns = ResumeContent.__table__.c

    assert columns.resume_id.nullable is False
    assert columns.extraction_status.nullable is False
    assert columns.created_at.nullable is False
    assert columns.updated_at.nullable is False

    assert columns.extracted_text.nullable is True
    assert columns.extraction_error.nullable is True
    assert columns.extractor_version.nullable is True
    assert columns.extracted_at.nullable is True