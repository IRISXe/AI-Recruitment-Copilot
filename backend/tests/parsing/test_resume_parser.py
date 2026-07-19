import pytest

from app.parsing.resume_parser import (
    CURRENT_ROLE_PATTERN,
    LOCATION_PATTERN,
    PARSER_VERSION,
    ResumeParsingError,
    extract_current_role,
    extract_email,
    extract_full_name,
    extract_labeled_value,
    extract_location,
    extract_phone,
    extract_professional_summary,
    extract_skills,
    normalize_lines,
    normalize_section_heading,
    parse_resume_text,
    split_resume_sections,
)


def test_parser_version_identifies_rule_based_parser() -> None:
    assert PARSER_VERSION == "rule-based-v1"


def test_extract_email_returns_normalized_email() -> None:
    text = "Contact: Harsha.Vardhan+Jobs@Example.COM"

    result = extract_email(text)

    assert result == "harsha.vardhan+jobs@example.com"


def test_extract_phone_returns_normalized_phone() -> None:
    text = "Phone: +91 98765 43210"

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
    assert profile.professional_summary == (
        "Backend developer experienced in API development."
    )
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


def test_normalize_section_heading_maps_heading_aliases() -> None:
    assert (
        normalize_section_heading(
            "Professional Summary:"
        )
        == "summary"
    )
    assert (
        normalize_section_heading(
            "WORK EXPERIENCE"
        )
        == "experience"
    )
    assert (
        normalize_section_heading(
            "Technical Skills"
        )
        == "skills"
    )
    assert normalize_section_heading(
        "Backend Developer"
    ) is None


def test_split_resume_sections_groups_content_by_heading() -> None:
    lines = [
        "Harsha Vardhan",
        "harsha@example.com",
        "Professional Summary",
        "Backend developer experienced in API development.",
        "Technical Skills",
        "Python, FastAPI and PostgreSQL",
        "Education",
        "Bachelor of Technology",
    ]

    sections = split_resume_sections(lines)

    assert sections["header"] == [
        "Harsha Vardhan",
        "harsha@example.com",
    ]
    assert sections["summary"] == [
        "Backend developer experienced in API development.",
    ]
    assert sections["skills"] == [
        "Python, FastAPI and PostgreSQL",
    ]
    assert sections["education"] == [
        "Bachelor of Technology",
    ]


def test_extract_professional_summary_joins_summary_lines() -> None:
    sections = {
        "summary": [
            "Backend developer with experience",
            "building REST APIs and cloud applications.",
        ],
    }

    result = extract_professional_summary(sections)

    assert result == (
        "Backend developer with experience "
        "building REST APIs and cloud applications."
    )


def test_extract_professional_summary_returns_none_when_missing(
) -> None:
    assert extract_professional_summary({}) is None


def test_extract_labeled_value_returns_matching_value() -> None:
    lines = [
        "Harsha Vardhan",
        "Current Role: Backend Developer",
    ]

    result = extract_labeled_value(
        lines,
        CURRENT_ROLE_PATTERN,
    )

    assert result == "Backend Developer"


@pytest.mark.parametrize(
    (
        "line",
        "expected_role",
    ),
    [
        (
            "Current Role: Backend Developer",
            "Backend Developer",
        ),
        (
            "Role - Frontend Engineer",
            "Frontend Engineer",
        ),
        (
            "Designation: Software Engineer",
            "Software Engineer",
        ),
        (
            "Title - Technical Consultant",
            "Technical Consultant",
        ),
    ],
)
def test_extract_current_role_supports_role_labels(
    line: str,
    expected_role: str,
) -> None:
    assert extract_current_role(
        [line]
    ) == expected_role


@pytest.mark.parametrize(
    (
        "line",
        "expected_location",
    ),
    [
        (
            "Location: Hyderabad, Telangana",
            "Hyderabad, Telangana",
        ),
        (
            "Current Location - Bengaluru",
            "Bengaluru",
        ),
        (
            "Based In: Chennai",
            "Chennai",
        ),
    ],
)
def test_extract_location_supports_location_labels(
    line: str,
    expected_location: str,
) -> None:
    assert extract_location(
        [line]
    ) == expected_location


def test_role_and_location_extractors_return_none_when_missing(
) -> None:
    lines = [
        "Harsha Vardhan",
        "harsha@example.com",
        "Python and FastAPI",
    ]

    assert extract_current_role(lines) is None
    assert extract_location(lines) is None


def test_parse_resume_text_extracts_role_and_location() -> None:
    text = """
    Harsha Vardhan
    Current Role: Backend Developer
    Location: Hyderabad, Telangana
    harsha@example.com

    Professional Summary
    Backend developer experienced in API development.

    Skills
    Python and FastAPI
    """

    profile = parse_resume_text(text)

    assert profile.current_role == "Backend Developer"
    assert profile.location == "Hyderabad, Telangana"