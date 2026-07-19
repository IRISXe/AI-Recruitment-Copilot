from datetime import date
import re

from app.schemas.resume_profile import (
    ResumeExperienceEntry,
    ResumeProfileData,
)


PARSER_VERSION = "rule-based-v1"


class ResumeParsingError(ValueError):
    """Raised when extracted Resume text cannot be parsed."""


EMAIL_PATTERN = re.compile(
    r"\b[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}\b",
    flags=re.IGNORECASE,
)

PHONE_PATTERN = re.compile(
    (
        r"(?<!\d)"
        r"(?:\+\d{1,3}[\s.\-]?)?"
        r"(?:\(?\d{2,5}\)?[\s.\-]?){2,5}"
        r"\d{2,5}"
        r"(?!\d)"
    )
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

EXPERIENCE_COMPANY_PATTERN = re.compile(
    r"^company\s*[:\-]\s*(?P<value>.+)$",
    flags=re.IGNORECASE,
)

EXPERIENCE_ROLE_PATTERN = re.compile(
    (
        r"^(?:role|title|designation)"
        r"\s*[:\-]\s*(?P<value>.+)$"
    ),
    flags=re.IGNORECASE,
)

EXPERIENCE_START_DATE_PATTERN = re.compile(
    (
        r"^start\s+date"
        r"\s*[:\-]\s*(?P<value>.+)$"
    ),
    flags=re.IGNORECASE,
)

EXPERIENCE_END_DATE_PATTERN = re.compile(
    (
        r"^end\s+date"
        r"\s*[:\-]\s*(?P<value>.+)$"
    ),
    flags=re.IGNORECASE,
)

EXPERIENCE_DATE_VALUE_PATTERN = (
    r"(?:(?:[A-Za-z]{3,9})\s+)?\d{4}"
)

EXPERIENCE_DATE_RANGE_PATTERN = re.compile(
    (
        r"^(?:(?:dates?|duration|period)"
        r"\s*[:\-]\s*)?"
        rf"(?P<start>{EXPERIENCE_DATE_VALUE_PATTERN})"
        r"\s*(?:-|–|—|\bto\b)\s*"
        rf"(?P<end>{EXPERIENCE_DATE_VALUE_PATTERN}"
        r"|present|current|ongoing|now)$"
    ),
    flags=re.IGNORECASE,
)

CURRENT_END_DATE_VALUES = {
    "present",
    "current",
    "ongoing",
    "now",
}

MONTH_NAME_TO_NUMBER = {
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}

MONTH_YEAR_PATTERN = re.compile(
    (
        r"^(?P<month>[A-Za-z]{3,9})"
        r"\s+(?P<year>\d{4})$"
    ),
    flags=re.IGNORECASE,
)

YEAR_ONLY_PATTERN = re.compile(
    r"^(?P<year>\d{4})$"
)

EXPERIENCE_HIGHLIGHT_PREFIXES = (
    "-",
    "*",
    "•",
    "▪",
)

SECTION_HEADINGS = {
    "summary",
    "professional summary",
    "profile",
    "objective",
    "experience",
    "work experience",
    "professional experience",
    "employment history",
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
    "employment history": "experience",
    "education": "education",
    "skills": "skills",
    "technical skills": "skills",
    "projects": "projects",
    "certifications": "certifications",
    "languages": "languages",
}

SKILL_ALIASES: dict[str, tuple[str, ...]] = {
    "AWS": (
        "aws",
        "amazon web services",
    ),
    "Docker": (
        "docker",
    ),
    "FastAPI": (
        "fastapi",
    ),
    "Git": (
        "git",
    ),
    "JavaScript": (
        "javascript",
        "js",
    ),
    "LangChain": (
        "langchain",
    ),
    "Next.js": (
        "next.js",
        "nextjs",
    ),
    "Node.js": (
        "node.js",
        "nodejs",
    ),
    "PostgreSQL": (
        "postgresql",
        "postgres",
    ),
    "Python": (
        "python",
    ),
    "React.js": (
        "react",
        "react.js",
        "reactjs",
    ),
    "SQL": (
        "sql",
    ),
    "SQLAlchemy": (
        "sqlalchemy",
    ),
    "Tailwind CSS": (
        "tailwind",
        "tailwind css",
    ),
    "TypeScript": (
        "typescript",
        "ts",
    ),
}


def normalize_lines(
    text: str,
) -> list[str]:
    return [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]


def extract_email(
    text: str,
) -> str | None:
    match = EMAIL_PATTERN.search(text)

    if match is None:
        return None

    return match.group(0).lower()


def normalize_phone(
    phone: str,
) -> str | None:
    normalized_phone = phone.strip()
    has_plus_prefix = normalized_phone.startswith("+")

    digits = re.sub(
        r"\D",
        "",
        normalized_phone,
    )

    if not 10 <= len(digits) <= 15:
        return None

    if has_plus_prefix:
        return f"+{digits}"

    return digits


def extract_phone(
    text: str,
) -> str | None:
    for match in PHONE_PATTERN.finditer(text):
        normalized_phone = normalize_phone(
            match.group(0)
        )

        if normalized_phone is not None:
            return normalized_phone

    return None


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


def extract_full_name(
    lines: list[str],
) -> str | None:
    for line in lines:
        normalized_line = line.strip()
        lowered_line = normalized_line.lower().rstrip(":")

        if not normalized_line:
            continue

        if lowered_line in SECTION_HEADINGS:
            continue

        if normalize_section_heading(normalized_line) is not None:
            continue

        if EMAIL_PATTERN.search(normalized_line):
            continue

        if normalize_phone(normalized_line) is not None:
            continue

        if CURRENT_ROLE_PATTERN.match(normalized_line):
            continue

        if LOCATION_PATTERN.match(normalized_line):
            continue

        if EXPERIENCE_DATE_RANGE_PATTERN.match(normalized_line):
            continue

        if normalized_line.startswith(
            EXPERIENCE_HIGHLIGHT_PREFIXES
        ):
            continue

        if any(
            character.isdigit()
            for character in normalized_line
        ):
            continue

        words = normalized_line.split()

        if not 2 <= len(words) <= 5:
            continue

        if len(normalized_line) > 100:
            continue

        return normalized_line

    return None


def extract_skills(
    text: str,
) -> list[str]:
    detected_skills: set[str] = set()

    for canonical_name, aliases in SKILL_ALIASES.items():
        for alias in aliases:
            alias_pattern = re.compile(
                (
                    rf"(?<![\w.])"
                    rf"{re.escape(alias)}"
                    rf"(?![\w.])"
                ),
                flags=re.IGNORECASE,
            )

            if alias_pattern.search(text):
                detected_skills.add(canonical_name)
                break

    return sorted(detected_skills)


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


def is_current_end_date(
    value: str,
) -> bool:
    return (
        value.strip().lower()
        in CURRENT_END_DATE_VALUES
    )


def parse_experience_date_range(
    line: str,
) -> tuple[str, str, bool] | None:
    match = EXPERIENCE_DATE_RANGE_PATTERN.match(
        line.strip()
    )

    if match is None:
        return None

    start_date = match.group("start").strip()
    end_date = match.group("end").strip()

    return (
        start_date,
        end_date,
        is_current_end_date(end_date),
    )


def extract_experience_highlight(
    line: str,
) -> str | None:
    normalized_line = line.strip()

    for prefix in EXPERIENCE_HIGHLIGHT_PREFIXES:
        if not normalized_line.startswith(prefix):
            continue

        highlight = normalized_line[
            len(prefix):
        ].strip()

        return highlight or None

    return None


def extract_work_experience(
    sections: dict[str, list[str]],
) -> list[ResumeExperienceEntry]:
    experience_lines = sections.get(
        "experience",
        [],
    )

    if not experience_lines:
        return []

    entries: list[ResumeExperienceEntry] = []

    def create_empty_entry() -> dict[str, object]:
        return {
            "company": None,
            "role": None,
            "location": None,
            "start_date": None,
            "end_date": None,
            "is_current": False,
            "highlights": [],
        }

    current_entry = create_empty_entry()

    def flush_current_entry() -> None:
        nonlocal current_entry

        has_content = any(
            [
                current_entry["company"],
                current_entry["role"],
                current_entry["location"],
                current_entry["start_date"],
                current_entry["end_date"],
                current_entry["highlights"],
            ]
        )

        if has_content:
            entries.append(
                ResumeExperienceEntry(
                    **current_entry,
                )
            )

        current_entry = create_empty_entry()

    for line in experience_lines:
        company_match = (
            EXPERIENCE_COMPANY_PATTERN.match(line)
        )

        if company_match is not None:
            flush_current_entry()

            current_entry["company"] = (
                company_match.group("value").strip()
            )
            continue

        role_match = EXPERIENCE_ROLE_PATTERN.match(line)

        if role_match is not None:
            current_entry["role"] = (
                role_match.group("value").strip()
            )
            continue

        location_match = LOCATION_PATTERN.match(line)

        if location_match is not None:
            current_entry["location"] = (
                location_match.group("value").strip()
            )
            continue

        date_range = parse_experience_date_range(line)

        if date_range is not None:
            (
                start_date,
                end_date,
                is_current,
            ) = date_range

            current_entry["start_date"] = start_date
            current_entry["end_date"] = end_date
            current_entry["is_current"] = is_current
            continue

        start_date_match = (
            EXPERIENCE_START_DATE_PATTERN.match(line)
        )

        if start_date_match is not None:
            current_entry["start_date"] = (
                start_date_match.group("value").strip()
            )
            continue

        end_date_match = (
            EXPERIENCE_END_DATE_PATTERN.match(line)
        )

        if end_date_match is not None:
            end_date = (
                end_date_match.group("value").strip()
            )

            current_entry["end_date"] = end_date
            current_entry["is_current"] = (
                is_current_end_date(end_date)
            )
            continue

        highlight = extract_experience_highlight(line)

        if highlight is not None:
            highlights = current_entry["highlights"]

            if isinstance(highlights, list):
                highlights.append(highlight)

    flush_current_entry()

    return entries


def to_month_index(
    year: int,
    month: int,
) -> int:
    return year * 12 + month - 1


def parse_experience_month(
    value: str,
    *,
    is_end: bool,
    reference_date: date | None = None,
) -> int | None:
    normalized_value = value.strip()

    if not normalized_value:
        return None

    if is_current_end_date(normalized_value):
        effective_date = reference_date or date.today()

        return to_month_index(
            effective_date.year,
            effective_date.month,
        )

    month_year_match = MONTH_YEAR_PATTERN.match(
        normalized_value
    )

    if month_year_match is not None:
        month_name = (
            month_year_match
            .group("month")
            .lower()[:3]
        )

        month_number = MONTH_NAME_TO_NUMBER.get(
            month_name
        )

        if month_number is None:
            return None

        year = int(
            month_year_match.group("year")
        )

        return to_month_index(
            year,
            month_number,
        )

    year_only_match = YEAR_ONLY_PATTERN.match(
        normalized_value
    )

    if year_only_match is not None:
        year = int(
            year_only_match.group("year")
        )

        month = 12 if is_end else 1

        return to_month_index(
            year,
            month,
        )

    return None


def calculate_total_experience_months(
    entries: list[ResumeExperienceEntry],
    *,
    reference_date: date | None = None,
) -> int | None:
    intervals: list[tuple[int, int]] = []

    for entry in entries:
        if (
            entry.start_date is None
            or entry.end_date is None
        ):
            continue

        start_month = parse_experience_month(
            entry.start_date,
            is_end=False,
            reference_date=reference_date,
        )

        end_month = parse_experience_month(
            entry.end_date,
            is_end=True,
            reference_date=reference_date,
        )

        if (
            start_month is None
            or end_month is None
            or end_month < start_month
        ):
            continue

        intervals.append(
            (
                start_month,
                end_month,
            )
        )

    if not intervals:
        return None

    intervals.sort(
        key=lambda interval: interval[0]
    )

    merged_intervals: list[list[int]] = []

    for start_month, end_month in intervals:
        if not merged_intervals:
            merged_intervals.append(
                [
                    start_month,
                    end_month,
                ]
            )
            continue

        previous_interval = merged_intervals[-1]
        previous_end = previous_interval[1]

        if start_month <= previous_end + 1:
            previous_interval[1] = max(
                previous_end,
                end_month,
            )
            continue

        merged_intervals.append(
            [
                start_month,
                end_month,
            ]
        )

    return sum(
        end_month - start_month + 1
        for start_month, end_month in merged_intervals
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

    work_experience = extract_work_experience(
        sections
    )

    return ResumeProfileData(
        full_name=extract_full_name(lines),
        email=extract_email(normalized_text),
        phone=extract_phone(normalized_text),
        location=extract_location(lines),
        current_role=extract_current_role(lines),
        professional_summary=extract_professional_summary(
            sections
        ),
        total_experience_months=(
            calculate_total_experience_months(
                work_experience
            )
        ),
        skills=extract_skills(normalized_text),
        education=[],
        work_experience=work_experience,
        projects=[],
        certifications=[],
        languages=[],
    )