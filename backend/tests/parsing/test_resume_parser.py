from datetime import date

import pytest

from app.parsing.resume_parser import (
    CURRENT_ROLE_PATTERN,
    LOCATION_PATTERN,
    PARSER_VERSION,
    ResumeParsingError,
    calculate_total_experience_months,
    extract_certifications,
    extract_education,
    extract_current_role,
    extract_email,
    extract_experience_highlight,
    extract_full_name,
    extract_labeled_value,
    extract_languages,
    extract_location,
    extract_phone,
    extract_professional_summary,
    extract_projects,
    extract_skills,
    extract_work_experience,
    is_current_end_date,
    normalize_lines,
    normalize_section_heading,
    parse_experience_date_range,
    parse_experience_month,
    parse_resume_text,
    split_resume_sections,
    to_month_index,
)
from app.schemas.resume_profile import ResumeExperienceEntry


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


def test_parse_experience_date_range_extracts_past_dates(
) -> None:
    result = parse_experience_date_range(
        "Dates: July 2022 - December 2023"
    )

    assert result == (
        "July 2022",
        "December 2023",
        False,
    )


@pytest.mark.parametrize(
    "end_date",
    [
        "Present",
        "Current",
        "Ongoing",
        "Now",
    ],
)
def test_parse_experience_date_range_marks_current_entries(
    end_date: str,
) -> None:
    result = parse_experience_date_range(
        f"January 2024 - {end_date}"
    )

    assert result == (
        "January 2024",
        end_date,
        True,
    )


def test_parse_experience_date_range_returns_none_for_invalid_line(
) -> None:
    assert parse_experience_date_range(
        "Worked for two years"
    ) is None


def test_is_current_end_date_is_case_insensitive() -> None:
    assert is_current_end_date("PRESENT") is True
    assert is_current_end_date("December 2025") is False


def test_extract_experience_highlight_removes_bullet() -> None:
    assert extract_experience_highlight(
        "• Built REST APIs"
    ) == "Built REST APIs"

    assert extract_experience_highlight(
        "Normal sentence"
    ) is None


def test_extract_work_experience_returns_structured_entry(
) -> None:
    sections = {
        "experience": [
            "Company: Acme Technologies",
            "Role: Backend Developer",
            "Location: Hyderabad",
            "Dates: January 2024 - Present",
            "- Built REST APIs",
            "• Improved automated test coverage",
        ],
    }

    result = extract_work_experience(sections)

    assert len(result) == 1

    entry = result[0]

    assert entry.company == "Acme Technologies"
    assert entry.role == "Backend Developer"
    assert entry.location == "Hyderabad"
    assert entry.start_date == "January 2024"
    assert entry.end_date == "Present"
    assert entry.is_current is True

    assert entry.highlights == [
        "Built REST APIs",
        "Improved automated test coverage",
    ]


def test_extract_work_experience_supports_multiple_entries(
) -> None:
    sections = {
        "experience": [
            "Company: Acme Technologies",
            "Role: Backend Developer",
            "January 2024 - Present",
            "- Built recruitment APIs",
            "Company: Beta Systems",
            "Designation: Frontend Developer",
            "July 2022 - December 2023",
            "* Developed React interfaces",
        ],
    }

    result = extract_work_experience(sections)

    assert len(result) == 2

    assert result[0].company == "Acme Technologies"
    assert result[0].role == "Backend Developer"
    assert result[0].is_current is True
    assert result[0].highlights == [
        "Built recruitment APIs",
    ]

    assert result[1].company == "Beta Systems"
    assert result[1].role == "Frontend Developer"
    assert result[1].start_date == "July 2022"
    assert result[1].end_date == "December 2023"
    assert result[1].is_current is False
    assert result[1].highlights == [
        "Developed React interfaces",
    ]


def test_extract_work_experience_returns_empty_list_when_missing(
) -> None:
    assert extract_work_experience({}) == []


def test_parse_resume_text_extracts_work_experience() -> None:
    text = """
    Harsha Vardhan
    harsha@example.com

    Professional Summary
    Backend developer experienced in API development.

    Work Experience
    Company: Acme Technologies
    Role: Backend Developer
    Location: Hyderabad
    Dates: January 2024 - Present
    - Built REST APIs using FastAPI
    - Worked with PostgreSQL

    Skills
    Python, FastAPI and PostgreSQL
    """

    profile = parse_resume_text(text)

    assert len(profile.work_experience) == 1

    experience = profile.work_experience[0]

    assert experience.company == "Acme Technologies"
    assert experience.role == "Backend Developer"
    assert experience.location == "Hyderabad"
    assert experience.start_date == "January 2024"
    assert experience.end_date == "Present"
    assert experience.is_current is True

    assert experience.highlights == [
        "Built REST APIs using FastAPI",
        "Worked with PostgreSQL",
    ]


def test_to_month_index_returns_sequential_index() -> None:
    assert to_month_index(2024, 1) == 24288
    assert to_month_index(2024, 2) == 24289


def test_parse_experience_month_parses_month_and_year() -> None:
    result = parse_experience_month(
        "January 2024",
        is_end=False,
    )

    assert result == to_month_index(
        2024,
        1,
    )


@pytest.mark.parametrize(
    (
        "is_end",
        "expected_month",
    ),
    [
        (
            False,
            1,
        ),
        (
            True,
            12,
        ),
    ],
)
def test_parse_experience_month_handles_year_only_values(
    is_end: bool,
    expected_month: int,
) -> None:
    result = parse_experience_month(
        "2024",
        is_end=is_end,
    )

    assert result == to_month_index(
        2024,
        expected_month,
    )


def test_parse_experience_month_uses_reference_date_for_present(
) -> None:
    result = parse_experience_month(
        "Present",
        is_end=True,
        reference_date=date(
            2026,
            7,
            19,
        ),
    )

    assert result == to_month_index(
        2026,
        7,
    )


def test_parse_experience_month_returns_none_for_invalid_value(
) -> None:
    assert parse_experience_month(
        "Two years ago",
        is_end=False,
    ) is None


def test_calculate_total_experience_months_counts_single_entry(
) -> None:
    entries = [
        ResumeExperienceEntry(
            company="Acme Technologies",
            role="Backend Developer",
            start_date="January 2024",
            end_date="December 2024",
        ),
    ]

    result = calculate_total_experience_months(
        entries
    )

    assert result == 12


def test_calculate_total_experience_months_merges_overlaps(
) -> None:
    entries = [
        ResumeExperienceEntry(
            company="Acme Technologies",
            start_date="January 2022",
            end_date="December 2022",
        ),
        ResumeExperienceEntry(
            company="Beta Systems",
            start_date="July 2022",
            end_date="June 2023",
        ),
    ]

    result = calculate_total_experience_months(
        entries
    )

    assert result == 18


def test_calculate_total_experience_months_handles_current_role(
) -> None:
    entries = [
        ResumeExperienceEntry(
            company="Acme Technologies",
            start_date="January 2024",
            end_date="Present",
            is_current=True,
        ),
    ]

    result = calculate_total_experience_months(
        entries,
        reference_date=date(
            2024,
            12,
            15,
        ),
    )

    assert result == 12


def test_calculate_total_experience_months_ignores_invalid_entries(
) -> None:
    entries = [
        ResumeExperienceEntry(
            company="Invalid Company",
            start_date="Unknown",
            end_date="Present",
        ),
        ResumeExperienceEntry(
            company="Acme Technologies",
            start_date="January 2024",
            end_date="March 2024",
        ),
    ]

    result = calculate_total_experience_months(
        entries,
        reference_date=date(
            2026,
            7,
            19,
        ),
    )

    assert result == 3


def test_calculate_total_experience_months_returns_none_without_valid_dates(
) -> None:
    entries = [
        ResumeExperienceEntry(
            company="Acme Technologies",
            role="Backend Developer",
        ),
    ]

    assert calculate_total_experience_months(
        entries
    ) is None


def test_parse_resume_text_calculates_overlap_safe_experience(
) -> None:
    text = """
    Harsha Vardhan
    harsha@example.com

    Work Experience
    Company: Acme Technologies
    Role: Backend Developer
    January 2022 - December 2022
    - Built REST APIs

    Company: Beta Systems
    Role: Frontend Developer
    July 2022 - June 2023
    - Developed React applications

    Skills
    Python, FastAPI and React.js
    """

    profile = parse_resume_text(text)

    assert len(profile.work_experience) == 2
    assert profile.total_experience_months == 18


# Phase 7H-7N parser coverage

def test_extract_education_parses_multiple_entries_and_optional_fields() -> None:
    result = extract_education(
        {
            "education": [
                "Institution: JNTU Hyderabad",
                "Degree: Bachelor of Technology",
                "Field of Study: Computer Science",
                "Location: Hyderabad",
                "Dates: 2020 - 2024",
                "Grade: 8.2 CGPA",
                "Institution: State Board of Technical Education",
                "Degree: Diploma",
            ]
        }
    )

    assert len(result) == 2
    assert result[0].institution == "JNTU Hyderabad"
    assert result[0].degree == "Bachelor of Technology"
    assert result[0].field_of_study == "Computer Science"
    assert result[0].start_date == "2020"
    assert result[0].end_date == "2024"
    assert result[0].description == "Location: Hyderabad\nGrade: 8.2 CGPA"
    assert result[1].institution == "State Board of Technical Education"
    assert result[1].degree == "Diploma"
    assert result[1].start_date is None


def test_extract_education_returns_empty_list_when_section_missing() -> None:
    assert extract_education({}) == []


def test_extract_projects_parses_technologies_url_and_highlights() -> None:
    result = extract_projects(
        {
            "projects": [
                "Project: AI Recruitment Copilot",
                "Description: Recruitment management platform",
                "Technologies: React, FastAPI, postgres, Docker",
                "URL: https://example.com/copilot",
                "- Built resume upload and extraction",
                "- Added structured profile parsing",
            ]
        }
    )

    assert len(result) == 1
    project = result[0]
    assert project.name == "AI Recruitment Copilot"
    assert project.description == "Recruitment management platform"
    assert project.technologies == [
        "React.js",
        "FastAPI",
        "PostgreSQL",
        "Docker",
    ]
    assert project.url == "https://example.com/copilot"
    assert project.highlights == [
        "Built resume upload and extraction",
        "Added structured profile parsing",
    ]


def test_extract_projects_supports_multiple_projects() -> None:
    result = extract_projects(
        {
            "projects": [
                "Project: Recruitment Copilot",
                "Description: Backend platform",
                "Project: App Graph Builder",
                "Technologies: React, TypeScript",
            ]
        }
    )

    assert [entry.name for entry in result] == [
        "Recruitment Copilot",
        "App Graph Builder",
    ]


def test_extract_certifications_supports_multiple_entries() -> None:
    result = extract_certifications(
        {
            "certifications": [
                "Certification: AWS Cloud Practitioner",
                "Issuer: Amazon Web Services",
                "Issue Date: January 2025",
                "Expiry Date: January 2028",
                "Credential ID: AWS-123",
                "Credential URL: https://example.com/aws-123",
                "Certification: SQL Fundamentals",
                "Issuer: Data Academy",
            ]
        }
    )

    assert len(result) == 2
    assert result[0].name == "AWS Cloud Practitioner"
    assert result[0].issuer == "Amazon Web Services"
    assert result[0].issue_date == "January 2025"
    assert result[0].expiry_date == "January 2028"
    assert result[0].credential_id == "AWS-123"
    assert result[0].credential_url == "https://example.com/aws-123"
    assert result[1].name == "SQL Fundamentals"
    assert result[1].expiry_date is None


def test_extract_languages_supports_lines_commas_and_proficiency() -> None:
    result = extract_languages(
        {
            "languages": [
                "English",
                "Hindi, Telugu",
                "English - Professional",
                "Hindi - Native",
            ]
        }
    )

    assert result == [
        "English - Professional",
        "Hindi - Native",
        "Telugu",
    ]


def test_extract_work_experience_supports_positional_format() -> None:
    result = extract_work_experience(
        {
            "experience": [
                "Acme Technologies",
                "Backend Developer",
                "January 2024 – Present",
                "Hyderabad",
                "- Built REST APIs",
            ]
        }
    )

    assert len(result) == 1
    entry = result[0]
    assert entry.company == "Acme Technologies"
    assert entry.role == "Backend Developer"
    assert entry.start_date == "January 2024"
    assert entry.end_date == "Present"
    assert entry.is_current is True
    assert entry.location == "Hyderabad"
    assert entry.highlights == ["Built REST APIs"]


def test_extract_work_experience_supports_pipe_format() -> None:
    result = extract_work_experience(
        {
            "experience": [
                "Backend Developer | Acme Technologies",
                "January 2024 – Present | Hyderabad",
                "- Built REST APIs",
            ]
        }
    )

    assert len(result) == 1
    assert result[0].role == "Backend Developer"
    assert result[0].company == "Acme Technologies"
    assert result[0].location == "Hyderabad"
    assert result[0].is_current is True


def test_extract_work_experience_supports_company_dash_role() -> None:
    result = extract_work_experience(
        {
            "experience": [
                "Acme Technologies — Backend Developer",
                "Jan 2024 to Present",
            ]
        }
    )

    assert len(result) == 1
    assert result[0].company == "Acme Technologies"
    assert result[0].role == "Backend Developer"
    assert result[0].start_date == "Jan 2024"
    assert result[0].end_date == "Present"


def test_parse_resume_text_derives_current_role_and_location() -> None:
    profile = parse_resume_text(
        """
        Harsha Vardhan
        harsha@example.com
        +91 98765 43210

        Work Experience
        Acme Technologies
        Backend Developer
        January 2024 – Present
        Hyderabad

        Skills
        Python, FastAPI
        """
    )

    assert profile.current_role == "Backend Developer"
    assert profile.location == "Hyderabad"


def test_explicit_header_role_and_location_take_priority() -> None:
    profile = parse_resume_text(
        """
        Harsha Vardhan
        Current Role: Technical Consultant
        Location: Bengaluru
        harsha@example.com
        +91 98765 43210

        Work Experience
        Acme Technologies
        Backend Developer
        January 2024 – Present
        Hyderabad
        """
    )

    assert profile.current_role == "Technical Consultant"
    assert profile.location == "Bengaluru"


def test_parse_resume_text_adds_warnings_missing_sections_and_confidence() -> None:
    profile = parse_resume_text(
        """
        Harsha Vardhan

        Education
        Unrecognised education text
        """
    )

    assert "No email detected" in profile.warnings
    assert "No phone detected" in profile.warnings
    assert (
        "Education section found but no valid entries parsed"
        in profile.warnings
    )
    assert "experience" in profile.missing_sections
    assert 0.0 <= profile.confidence <= 1.0


def test_parse_resume_text_integrates_all_structured_sections() -> None:
    profile = parse_resume_text(
        """
        Harsha Vardhan
        harsha@example.com
        +91 98765 43210

        Professional Summary
        Backend developer building reliable APIs.

        Work Experience
        Company: Acme Technologies
        Role: Backend Developer
        Location: Hyderabad
        Dates: January 2024 - Present
        - Built FastAPI services

        Education
        Institution: JNTU Hyderabad
        Degree: Bachelor of Technology
        Field of Study: Computer Science
        Dates: 2020 - 2024

        Projects
        Project: AI Recruitment Copilot
        Description: Recruitment management platform
        Technologies: React, FastAPI, PostgreSQL, Docker
        - Added structured parsing

        Certifications
        Certification: AWS Cloud Practitioner
        Issuer: Amazon Web Services

        Languages
        English - Professional, Telugu - Native

        Technical Skills
        Python, FastAPI, PostgreSQL, React, Docker
        """
    )

    assert len(profile.work_experience) == 1
    assert len(profile.education) == 1
    assert len(profile.projects) == 1
    assert len(profile.certifications) == 1
    assert profile.languages == [
        "English - Professional",
        "Telugu - Native",
    ]
    assert profile.current_role == "Backend Developer"
    assert profile.location == "Hyderabad"
    assert profile.total_experience_months is not None
    assert profile.warnings == []
    assert profile.missing_sections == []
    assert profile.confidence == 1.0


def test_total_experience_remains_overlap_safe() -> None:
    entries = [
        ResumeExperienceEntry(
            company="A",
            role="Developer",
            start_date="January 2022",
            end_date="December 2022",
        ),
        ResumeExperienceEntry(
            company="B",
            role="Developer",
            start_date="July 2022",
            end_date="June 2023",
        ),
    ]

    assert calculate_total_experience_months(
        entries,
        reference_date=date(2026, 7, 19),
    ) == 18