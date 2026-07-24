import pytest

from app.matching.qualification_normalizer import (
    normalize_certification_text,
    normalize_education_text,
    normalize_match_text,
    normalize_text_list,
    normalized_term_set,
)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (
            "Bachelor's degree in Computer Science",
            "bachelor computer science",
        ),
        (
            "Bachelor of Technology, Computer Science",
            "bachelor computer science",
        ),
        (
            "Bachelor of Engineering in Computer Engineering",
            "bachelor computer science",
        ),
        (
            "Master of Science in Computer Science",
            "master computer science",
        ),
        (
            "Master of Technology in CSE",
            "master computer science",
        ),
        (
            "PhD in Computer Science",
            "doctorate computer science",
        ),
        (
            "Diploma in Information Technology",
            "diploma information technology",
        ),
    ],
)
def test_normalize_education_text_converts_known_qualifications(
    value: str,
    expected: str,
) -> None:
    assert normalize_education_text(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (
            "AWS Certified Developer certification preferred",
            "aws developer",
        ),
        (
            "AWS Cloud Practitioner, Amazon Web Services",
            "aws cloud practitioner aws",
        ),
        (
            "Microsoft Azure Administrator Certificate",
            "azure administrator",
        ),
        (
            "Google Cloud Platform Professional Certification",
            "gcp professional",
        ),
        (
            "SQL Fundamentals certification required",
            "sql fundamentals",
        ),
    ],
)
def test_normalize_certification_text_removes_generic_terms(
    value: str,
    expected: str,
) -> None:
    assert normalize_certification_text(value) == expected


def test_normalize_match_text_normalizes_case_and_spacing() -> None:
    result = normalize_match_text(
        "  Bachelor's   Degree & Computer   Science  "
    )

    assert result == "bachelors degree and computer science"


def test_normalize_match_text_handles_curly_apostrophe() -> None:
    assert normalize_match_text(
        "Bachelor’s Degree"
    ) == "bachelors degree"


@pytest.mark.parametrize(
    "value",
    [
        "",
        " ",
        "\n\t",
    ],
)
def test_education_normalizer_returns_empty_string_for_empty_input(
    value: str,
) -> None:
    assert normalize_education_text(value) == ""


@pytest.mark.parametrize(
    "value",
    [
        "",
        " ",
        "\n\t",
    ],
)
def test_certification_normalizer_returns_empty_string_for_empty_input(
    value: str,
) -> None:
    assert normalize_certification_text(value) == ""


def test_normalized_term_set_returns_unique_terms() -> None:
    result = normalized_term_set(
        "aws cloud practitioner aws"
    )

    assert result == frozenset(
        {
            "aws",
            "cloud",
            "practitioner",
        }
    )


def test_normalize_text_list_normalizes_and_deduplicates_values() -> None:
    result = normalize_text_list(
        [
            "Bachelor of Technology in Computer Science",
            "Bachelor's degree in Computer Science",
            "Master of Science in Computer Science",
            "",
        ],
        normalizer=normalize_education_text,
    )

    assert result == [
        "bachelor computer science",
        "master computer science",
    ]


def test_normalize_text_list_preserves_first_seen_order() -> None:
    result = normalize_text_list(
        [
            "AWS Cloud Practitioner",
            "Microsoft Azure Administrator",
            "Google Cloud Platform Professional",
        ],
        normalizer=normalize_certification_text,
    )

    assert result == [
        "aws cloud practitioner",
        "azure administrator",
        "gcp professional",
    ]


def test_normalization_is_deterministic() -> None:
    value = "Bachelor's degree in Computer Science"

    first_result = normalize_education_text(value)
    second_result = normalize_education_text(value)

    assert first_result == second_result