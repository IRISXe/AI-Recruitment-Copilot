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


def parse_resume_text(
    text: str,
) -> ResumeProfileData:
    normalized_text = text.strip()

    if not normalized_text:
        raise ResumeParsingError(
            "Resume text must not be empty."
        )

    lines = normalize_lines(normalized_text)

    return ResumeProfileData(
        full_name=extract_full_name(lines),
        email=extract_email(normalized_text),
        phone=extract_phone(normalized_text),
        location=None,
        current_role=None,
        professional_summary=None,
        total_experience_months=None,
        skills=extract_skills(normalized_text),
        education=[],
        work_experience=[],
        projects=[],
        certifications=[],
        languages=[],
    )