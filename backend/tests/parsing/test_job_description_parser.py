import pytest

from app.parsing.job_description_parser import (
    JobDescriptionParsingError,
    extract_experience_range,
    extract_skills,
    parse_job_description,
)


FULL_JOB_DESCRIPTION = """
Job Title: Senior Backend Engineer
Department: Engineering
Location: Hyderabad
Work mode: Hybrid
Employment type: Full-time

About the Role
We are looking for a Senior Backend Engineer to build scalable
cloud applications.

Responsibilities
- Design and develop REST APIs using Python and FastAPI.
- Maintain PostgreSQL databases.
- Deploy applications using Docker and AWS.

Required Skills
- Python
- FastAPI
- PostgreSQL
- Docker
- Minimum 3 years of experience
- Bachelor's degree in Computer Science

Preferred Skills
- Kubernetes
- AWS Certified Developer certification preferred
"""


def test_parse_job_description_extracts_structured_profile() -> None:
    profile = parse_job_description(
        FULL_JOB_DESCRIPTION
    )

    assert profile.job_title == "Senior Backend Engineer"
    assert profile.department == "Engineering"
    assert profile.location == "Hyderabad"
    assert profile.employment_type == "full_time"
    assert profile.work_mode == "hybrid"
    assert profile.seniority_level == "senior"

    assert profile.minimum_experience_years == 3
    assert profile.maximum_experience_years is None

    assert "Python" in profile.required_skills
    assert "FastAPI" in profile.required_skills
    assert "PostgreSQL" in profile.required_skills
    assert "Docker" in profile.required_skills
    assert "REST APIs" in profile.required_skills

    assert "Kubernetes" in profile.preferred_skills
    assert "AWS" in profile.preferred_skills

    assert profile.responsibilities == [
        "Design and develop REST APIs using Python and FastAPI.",
        "Maintain PostgreSQL databases.",
        "Deploy applications using Docker and AWS.",
    ]

    assert profile.required_education == [
        "Bachelor's degree in Computer Science"
    ]

    assert profile.preferred_certifications == [
        "AWS Certified Developer certification preferred"
    ]

    assert profile.warnings == []
    assert profile.missing_sections == []
    assert profile.confidence == 1.0


def test_parse_job_description_rejects_empty_text() -> None:
    with pytest.raises(
        JobDescriptionParsingError,
        match="The job description is empty",
    ):
        parse_job_description("")


def test_parse_job_description_rejects_short_text() -> None:
    with pytest.raises(
        JobDescriptionParsingError,
        match="too short to parse",
    ):
        parse_job_description("Backend role")


def test_extract_experience_range_extracts_minimum_and_maximum() -> None:
    minimum, maximum = extract_experience_range(
        "Candidates must have 3 to 5 years of experience."
    )

    assert minimum == 3
    assert maximum == 5


def test_extract_experience_range_extracts_plus_requirement() -> None:
    minimum, maximum = extract_experience_range(
        "Requires 4+ years of experience with Python."
    )

    assert minimum == 4
    assert maximum is None


@pytest.mark.parametrize(
    ("description", "expected_work_mode"),
    [
        (
            "This is a fully remote Backend Engineer position.",
            "remote",
        ),
        (
            "This is a hybrid Backend Engineer position.",
            "hybrid",
        ),
        (
            "This is an onsite Backend Engineer position.",
            "onsite",
        ),
    ],
)
def test_parse_job_description_extracts_work_mode(
    description: str,
    expected_work_mode: str,
) -> None:
    profile = parse_job_description(description)

    assert profile.work_mode == expected_work_mode


def test_extract_skills_returns_unique_canonical_values() -> None:
    skills = extract_skills(
        "React, ReactJS, TypeScript, FastAPI and PostgreSQL"
    )

    assert skills == [
        "React",
        "TypeScript",
        "FastAPI",
        "PostgreSQL",
    ]


def test_preferred_skills_are_not_added_to_required_skills() -> None:
    description = """
Job Title: Backend Engineer

Required Skills
- Python
- FastAPI

Preferred Skills
- AWS
- Kubernetes
"""

    profile = parse_job_description(description)

    assert profile.required_skills == [
        "Python",
        "FastAPI",
    ]
    assert profile.preferred_skills == [
        "AWS",
        "Kubernetes",
    ]


def test_parse_job_description_reports_missing_requirements() -> None:
    description = (
        "We are hiring someone to join our growing product team "
        "and contribute to important company initiatives."
    )

    profile = parse_job_description(description)

    assert "job_title" in profile.missing_sections
    assert "responsibilities" in profile.missing_sections
    assert "required_skills" in profile.missing_sections
    assert "experience" in profile.missing_sections

    assert (
        "No responsibilities were identified."
        in profile.warnings
    )
    assert (
        "No required skills were identified."
        in profile.warnings
    )
    assert profile.confidence < 1.0
