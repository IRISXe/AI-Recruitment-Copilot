import pytest

from app.parsing.resume_parser import (
    PARSER_VERSION,
    ResumeParsingError,
    extract_email,
    extract_full_name,
    extract_phone,
    extract_skills,
    normalize_lines,
    parse_resume_text,
)


def test_parser_version_identifies_rule_based_parser() -> None:
    assert PARSER_VERSION == "rule-based-v1"


def test_extract_email_returns_normalized_email() -> None:
    text = (
        "Contact: Harsha.Vardhan+Jobs@Example.COM"
    )

    result = extract_email(text)

    assert result == "harsha.vardhan+jobs@example.com"


def test_extract_phone_returns_normalized_phone() -> None:
    text = (
        "Phone: +91 98765 43210"
    )

    result = extract_phone(text)

    assert result == "+919876543210"


def test_extract_full_name_skips_headings_and_contact_lines() -> None:
    text = """
    PROFESSIONAL SUMMARY
    Harsha Vardhan
    harsha@example.com
    +91 98765 43210
    Backend Developer
    """

    lines = normalize_lines(text)

    result = extract_full_name(lines)

    assert result == "Harsha Vardhan"


def test_extract_skills_normalizes_aliases_and_removes_duplicates(
) -> None:
    text = """
    Skills:
    Python, FastAPI, PostgreSQL, postgres,
    React, React.js, reactjs,
    AWS, Amazon Web Services
    """

    result = extract_skills(text)

    assert result == [
        "AWS",
        "FastAPI",
        "PostgreSQL",
        "Python",
        "React.js",
    ]


def test_parse_resume_text_returns_structured_profile() -> None:
    text = """
    Harsha Vardhan
    harsha.vardhan@example.com
    +91 98765 43210

    Professional Summary
    Backend developer experienced in API development.

    Technical Skills
    Python, FastAPI, PostgreSQL, React.js,
    TypeScript, AWS, Docker, Git
    """

    profile = parse_resume_text(text)

    assert profile.full_name == "Harsha Vardhan"
    assert profile.email == "harsha.vardhan@example.com"
    assert profile.phone == "+919876543210"

    assert profile.skills == [
        "AWS",
        "Docker",
        "FastAPI",
        "Git",
        "PostgreSQL",
        "Python",
        "React.js",
        "TypeScript",
    ]

    assert profile.location is None
    assert profile.current_role is None
    assert profile.professional_summary is None
    assert profile.total_experience_months is None

    assert profile.education == []
    assert profile.work_experience == []
    assert profile.projects == []
    assert profile.certifications == []
    assert profile.languages == []


def test_parse_resume_text_allows_missing_contact_information(
) -> None:
    text = """
    Harsha Vardhan

    Skills
    Python and FastAPI
    """

    profile = parse_resume_text(text)

    assert profile.full_name == "Harsha Vardhan"
    assert profile.email is None
    assert profile.phone is None
    assert profile.skills == [
        "FastAPI",
        "Python",
    ]


@pytest.mark.parametrize(
    "text",
    [
        "",
        " ",
        "\n\n\t",
    ],
)
def test_parse_resume_text_rejects_empty_text(
    text: str,
) -> None:
    with pytest.raises(
        ResumeParsingError,
        match="Resume text must not be empty",
    ):
        parse_resume_text(text)