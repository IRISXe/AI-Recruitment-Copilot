import pytest

from app.matching.skill_normalizer import (
    canonicalize_skill,
    normalize_skill_list,
    normalize_skill_text,
    skill_comparison_key,
)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("React", "React"),
        ("React.js", "React"),
        ("ReactJS", "React"),
        ("reactjs", "React"),
        ("Postgres", "PostgreSQL"),
        ("postgresql", "PostgreSQL"),
        ("Amazon Web Services", "AWS"),
        ("aws", "AWS"),
        ("RESTful APIs", "REST APIs"),
        ("rest api", "REST APIs"),
        ("K8s", "Kubernetes"),
        ("Google Cloud Platform", "GCP"),
        ("Natural Language Processing", "NLP"),
    ],
)
def test_canonicalize_skill_normalizes_known_aliases(
    value: str,
    expected: str,
) -> None:
    assert canonicalize_skill(value) == expected


def test_canonicalize_skill_preserves_unknown_skill() -> None:
    assert canonicalize_skill("Celery") == "Celery"


def test_canonicalize_skill_normalizes_whitespace() -> None:
    assert canonicalize_skill(
        "  Custom   Platform   Skill  "
    ) == "Custom Platform Skill"


@pytest.mark.parametrize(
    "value",
    [
        "",
        " ",
        "\n\t",
    ],
)
def test_canonicalize_skill_returns_none_for_empty_values(
    value: str,
) -> None:
    assert canonicalize_skill(value) is None


def test_normalize_skill_list_deduplicates_aliases() -> None:
    result = normalize_skill_list(
        [
            "React.js",
            "ReactJS",
            "react",
            "Postgres",
            "PostgreSQL",
            "AWS",
            "Amazon Web Services",
        ]
    )

    assert result == [
        "React",
        "PostgreSQL",
        "AWS",
    ]


def test_normalize_skill_list_preserves_first_seen_order() -> None:
    result = normalize_skill_list(
        [
            "Docker",
            "Python",
            "React.js",
            "Postgres",
        ]
    )

    assert result == [
        "Docker",
        "Python",
        "React",
        "PostgreSQL",
    ]


def test_normalize_skill_list_removes_empty_values() -> None:
    result = normalize_skill_list(
        [
            "",
            " ",
            "Python",
            "\n",
            "FastAPI",
        ]
    )

    assert result == [
        "Python",
        "FastAPI",
    ]


def test_normalize_skill_list_deduplicates_unknown_skills_case_insensitively(
) -> None:
    result = normalize_skill_list(
        [
            "Celery",
            " celery ",
            "CELERY",
        ]
    )

    assert result == [
        "Celery",
    ]


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("React.js", "react"),
        ("ReactJS", "react"),
        ("Postgres", "postgresql"),
        ("Amazon Web Services", "aws"),
        ("Unknown Skill", "unknown skill"),
        ("", None),
    ],
)
def test_skill_comparison_key_returns_canonical_casefolded_key(
    value: str,
    expected: str | None,
) -> None:
    assert skill_comparison_key(value) == expected


def test_normalize_skill_text_collapses_whitespace() -> None:
    assert normalize_skill_text(
        "  Amazon   Web   Services  "
    ) == "Amazon Web Services"