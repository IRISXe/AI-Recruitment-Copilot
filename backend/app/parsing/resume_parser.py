import re

from app.schemas.resume_profile import ResumeProfileData


PARSER_VERSION = "rule-based-v1"


class ResumeParsingError(Exception):
    """Raised when structured data cannot be parsed from resume text."""


EMAIL_PATTERN = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
)

PHONE_PATTERN = re.compile(
    r"(?<!\d)(?:\+?\d[\d\s().-]{7,}\d)(?!\d)"
)

CURRENT_ROLE_PATTERN = re.compile(
    (
        r"^(?:current\s+role|role|title|designation)"
        r"\s*[:\-]\s*(?P<value>.+)$"
    ),
    flags=re.IGNORECASE,
)

LOCATION_PATTERN = re.compile(
    (
        r"^(?:current\s+location|location|based\s+in)"
        r"\s*[:\-]\s*(?P<value>.+)$"
    ),
    flags=re.IGNORECASE,
)

SECTION_HEADINGS = {
    "summary",
    "professional summary",
    "profile",
    "objective",
    "experience",
    "work experience",
    "professional experience",
    "education",
    "skills",
    "technical skills",
    "projects",
    "certifications",
    "languages",
}

SECTION_ALIASES = {
    "summary": "summary",
    "professional summary": "summary",
    "profile": "summary",
    "objective": "summary",
    "experience": "experience",
    "work experience": "experience",
    "professional experience": "experience",
    "education": "education",
    "skills": "skills",
    "technical skills": "skills",
    "projects": "projects",
    "certifications": "certifications",
    "languages": "languages",
}


SKILL_ALIASES = {
    "amazon web services": "AWS",
    "aws": "AWS",
    "docker": "Docker",
    "fastapi": "FastAPI",
    "git": "Git",
    "javascript": "JavaScript",
    "langchain": "LangChain",
    "next.js": "Next.js",
    "nextjs": "Next.js",
    "node.js": "Node.js",
    "nodejs": "Node.js",
    "postgresql": "PostgreSQL",
    "postgres": "PostgreSQL",
    "python": "Python",
    "react.js": "React.js",
    "reactjs": "React.js",
    "react": "React.js",
    "sql": "SQL",
    "sqlalchemy": "SQLAlchemy",
    "tailwind css": "Tailwind CSS",
    "tailwind": "Tailwind CSS",
    "typescript": "TypeScript",
}


def normalize_lines(text: str) -> list[str]:
    return [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]


def extract_email(text: str) -> str | None:
    match = EMAIL_PATTERN.search(text)

    if match is None:
        return None

    return match.group(0).lower()


def normalize_phone(value: str) -> str:
    value = value.strip()

    has_country_prefix = value.startswith("+")

    digits = re.sub(
        r"\D",
        "",
        value,
    )

    if has_country_prefix:
        return f"+{digits}"

    return digits


def extract_phone(text: str) -> str | None:
    for match in PHONE_PATTERN.finditer(text):
        phone = normalize_phone(match.group(0))

        digit_count = len(
            phone.removeprefix("+")
        )

        if 10 <= digit_count <= 15:
            return phone

    return None


def extract_full_name(
    lines: list[str],
) -> str | None:
    for line in lines[:5]:
        normalized_line = line.lower().rstrip(":")

        if normalized_line in SECTION_HEADINGS:
            continue

        if EMAIL_PATTERN.search(line):
            continue

        if PHONE_PATTERN.search(line):
            continue

        if any(character.isdigit() for character in line):
            continue

        words = line.split()

        if 2 <= len(words) <= 5:
            return line

    return None


def extract_skills(
    text: str,
) -> list[str]:
    normalized_text = text.lower()

    detected_skills: list[str] = []

    for alias, canonical_name in SKILL_ALIASES.items():
        pattern = re.compile(
            rf"(?<![\w.]){re.escape(alias)}(?![\w.])",
            flags=re.IGNORECASE,
        )

        if pattern.search(normalized_text):
            if canonical_name not in detected_skills:
                detected_skills.append(canonical_name)

    return sorted(
        detected_skills,
        key=str.casefold,
    )


def normalize_section_heading(
    line: str,
) -> str | None:
    normalized_line = line.strip().lower().rstrip(":")

    return SECTION_ALIASES.get(normalized_line)


def split_resume_sections(
    lines: list[str],
) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {
        "header": [],
    }

    current_section = "header"

    for line in lines:
        section_name = normalize_section_heading(line)

        if section_name is not None:
            current_section = section_name
            sections.setdefault(
                current_section,
                [],
            )
            continue

        sections.setdefault(
            current_section,
            [],
        ).append(line)

    return sections


def extract_professional_summary(
    sections: dict[str, list[str]],
) -> str | None:
    summary_lines = sections.get(
        "summary",
        [],
    )

    if not summary_lines:
        return None

    summary = " ".join(summary_lines).strip()

    return summary or None

def extract_labeled_value(
    lines: list[str],
    pattern: re.Pattern[str],
) -> str | None:
    for line in lines:
        match = pattern.match(line)

        if match is None:
            continue

        value = match.group("value").strip()

        if value:
            return value

    return None


def extract_current_role(
    lines: list[str],
) -> str | None:
    return extract_labeled_value(
        lines,
        CURRENT_ROLE_PATTERN,
    )


def extract_location(
    lines: list[str],
) -> str | None:
    return extract_labeled_value(
        lines,
        LOCATION_PATTERN,
    )


def parse_resume_text(
    text: str,
) -> ResumeProfileData:
    normalized_text = text.strip()

    if not normalized_text:
        raise ResumeParsingError(
            "Resume text must not be empty."
        )

    lines = normalize_lines(normalized_text)
    sections = split_resume_sections(lines)

    return ResumeProfileData(
    full_name=extract_full_name(lines),
    email=extract_email(normalized_text),
    phone=extract_phone(normalized_text),
    location=extract_location(lines),
    current_role=extract_current_role(lines),
    professional_summary=extract_professional_summary(
        sections
    ),
    total_experience_months=None,
    skills=extract_skills(normalized_text),
    education=[],
    work_experience=[],
    projects=[],
    certifications=[],
    languages=[],
)