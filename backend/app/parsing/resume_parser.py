from datetime import date
import re
from typing import Any, Literal

from app.schemas.resume_profile import (
    ResumeCertificationEntry,
    ResumeEducationEntry,
    ResumeExperienceEntry,
    ResumeProfileData,
    ResumeProjectEntry,
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
    r"^start\s+date\s*[:\-]\s*(?P<value>.+)$",
    flags=re.IGNORECASE,
)

EXPERIENCE_END_DATE_PATTERN = re.compile(
    r"^end\s+date\s*[:\-]\s*(?P<value>.+)$",
    flags=re.IGNORECASE,
)

EXPERIENCE_DATE_VALUE_PATTERN = (
    r"(?:(?:[A-Za-z]{3,9})\s+)?\d{4}"
)

EXPERIENCE_DATE_RANGE_PATTERN = re.compile(
    (
        r"^(?:(?:dates?|duration|period)\s*[:\-]\s*)?"
        rf"(?P<start>{EXPERIENCE_DATE_VALUE_PATTERN})"
        r"\s*(?:-|–|—|\bto\b)\s*"
        rf"(?P<end>{EXPERIENCE_DATE_VALUE_PATTERN}"
        r"|present|current|ongoing|now)$"
    ),
    flags=re.IGNORECASE,
)

PIPE_EXPERIENCE_HEADER_PATTERN = re.compile(
    r"^(?P<role>[^|]{2,200})\|(?P<company>[^|]{2,300})$"
)

DASH_EXPERIENCE_HEADER_PATTERN = re.compile(
    r"^(?P<company>.+?)\s+[—–]\s+(?P<role>.+)$"
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
    r"^(?P<month>[A-Za-z]{3,9})\s+(?P<year>\d{4})$",
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

EDUCATION_INSTITUTION_PATTERN = re.compile(
    (
        r"^(?:institution|university|college|school)"
        r"\s*[:\-]\s*(?P<value>.+)$"
    ),
    flags=re.IGNORECASE,
)

EDUCATION_DEGREE_PATTERN = re.compile(
    r"^degree\s*[:\-]\s*(?P<value>.+)$",
    flags=re.IGNORECASE,
)

EDUCATION_FIELD_PATTERN = re.compile(
    (
        r"^(?:field\s+of\s+study|major|speciali[sz]ation)"
        r"\s*[:\-]\s*(?P<value>.+)$"
    ),
    flags=re.IGNORECASE,
)

EDUCATION_DESCRIPTION_PATTERN = re.compile(
    r"^description\s*[:\-]\s*(?P<value>.+)$",
    flags=re.IGNORECASE,
)

PROJECT_NAME_PATTERN = re.compile(
    r"^(?:project|project\s+name|name)\s*[:\-]\s*(?P<value>.+)$",
    flags=re.IGNORECASE,
)

PROJECT_DESCRIPTION_PATTERN = re.compile(
    r"^description\s*[:\-]\s*(?P<value>.+)$",
    flags=re.IGNORECASE,
)

PROJECT_TECHNOLOGIES_PATTERN = re.compile(
    (
        r"^(?:technologies|technology|tech\s+stack|tools)"
        r"\s*[:\-]\s*(?P<value>.+)$"
    ),
    flags=re.IGNORECASE,
)

PROJECT_URL_PATTERN = re.compile(
    r"^(?:url|link|project\s+url)\s*[:\-]\s*(?P<value>.+)$",
    flags=re.IGNORECASE,
)

CERTIFICATION_NAME_PATTERN = re.compile(
    (
        r"^(?:certification|certificate|certification\s+name|name)"
        r"\s*[:\-]\s*(?P<value>.+)$"
    ),
    flags=re.IGNORECASE,
)

CERTIFICATION_ISSUER_PATTERN = re.compile(
    (
        r"^(?:issuer|issuing\s+organization|issued\s+by)"
        r"\s*[:\-]\s*(?P<value>.+)$"
    ),
    flags=re.IGNORECASE,
)

CERTIFICATION_ISSUE_DATE_PATTERN = re.compile(
    r"^issue\s+date\s*[:\-]\s*(?P<value>.+)$",
    flags=re.IGNORECASE,
)

CERTIFICATION_EXPIRY_DATE_PATTERN = re.compile(
    (
        r"^(?:expiry|expiration)\s+date"
        r"\s*[:\-]\s*(?P<value>.+)$"
    ),
    flags=re.IGNORECASE,
)

CERTIFICATION_CREDENTIAL_ID_PATTERN = re.compile(
    r"^credential\s+id\s*[:\-]\s*(?P<value>.+)$",
    flags=re.IGNORECASE,
)

CERTIFICATION_CREDENTIAL_URL_PATTERN = re.compile(
    r"^credential\s+url\s*[:\-]\s*(?P<value>.+)$",
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
    "employment history",
    "education",
    "academic background",
    "academic qualifications",
    "skills",
    "technical skills",
    "projects",
    "personal projects",
    "academic projects",
    "certifications",
    "certificates",
    "licenses & certifications",
    "languages",
    "language proficiency",
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
    "academic background": "education",
    "academic qualifications": "education",
    "skills": "skills",
    "technical skills": "skills",
    "projects": "projects",
    "personal projects": "projects",
    "academic projects": "projects",
    "certifications": "certifications",
    "certificates": "certifications",
    "licenses & certifications": "certifications",
    "languages": "languages",
    "language proficiency": "languages",
}

SKILL_ALIASES: dict[str, tuple[str, ...]] = {
    "AWS": ("aws", "amazon web services"),
    "Docker": ("docker",),
    "FastAPI": ("fastapi",),
    "Git": ("git",),
    "JavaScript": ("javascript", "js"),
    "LangChain": ("langchain",),
    "Next.js": ("next.js", "nextjs"),
    "Node.js": ("node.js", "nodejs"),
    "PostgreSQL": ("postgresql", "postgres"),
    "Python": ("python",),
    "React.js": ("react", "react.js", "reactjs"),
    "SQL": ("sql",),
    "SQLAlchemy": ("sqlalchemy",),
    "Tailwind CSS": ("tailwind", "tailwind css"),
    "TypeScript": ("typescript", "ts"),
}

CANONICAL_SECTION_NAMES = (
    "summary",
    "experience",
    "education",
    "skills",
    "projects",
    "certifications",
    "languages",
)


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


def normalize_phone(phone: str) -> str | None:
    normalized_phone = phone.strip()
    has_plus_prefix = normalized_phone.startswith("+")
    digits = re.sub(r"\D", "", normalized_phone)

    if not 10 <= len(digits) <= 15:
        return None

    if has_plus_prefix:
        return f"+{digits}"

    return digits


def extract_phone(text: str) -> str | None:
    for match in PHONE_PATTERN.finditer(text):
        normalized_phone = normalize_phone(match.group(0))

        if normalized_phone is not None:
            return normalized_phone

    return None


def normalize_section_heading(line: str) -> str | None:
    normalized_line = line.strip().lower().rstrip(":")
    return SECTION_ALIASES.get(normalized_line)


def split_resume_sections(
    lines: list[str],
) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {"header": []}
    current_section = "header"

    for line in lines:
        section_name = normalize_section_heading(line)

        if section_name is not None:
            current_section = section_name
            sections.setdefault(current_section, [])
            continue

        sections.setdefault(current_section, []).append(line)

    return sections


def extract_full_name(lines: list[str]) -> str | None:
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

        if normalized_line.startswith(EXPERIENCE_HIGHLIGHT_PREFIXES):
            continue

        if any(character.isdigit() for character in normalized_line):
            continue

        words = normalized_line.split()

        if not 2 <= len(words) <= 5:
            continue

        if len(normalized_line) > 100:
            continue

        return normalized_line

    return None


def _canonical_skill_for_value(value: str) -> str | None:
    normalized_value = value.strip().lower()

    for canonical_name, aliases in SKILL_ALIASES.items():
        if normalized_value == canonical_name.lower():
            return canonical_name

        if normalized_value in {alias.lower() for alias in aliases}:
            return canonical_name

    return None


def extract_skills(text: str) -> list[str]:
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


def normalize_technology_list(value: str) -> list[str]:
    technologies: list[str] = []
    seen: set[str] = set()

    for part in re.split(r"[,;|]", value):
        normalized_part = part.strip()

        if not normalized_part:
            continue

        canonical = _canonical_skill_for_value(normalized_part)
        technology = canonical or normalized_part
        duplicate_key = technology.casefold()

        if duplicate_key in seen:
            continue

        seen.add(duplicate_key)
        technologies.append(technology)

    return technologies


def extract_professional_summary(
    sections: dict[str, list[str]],
) -> str | None:
    summary_lines = sections.get("summary", [])

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


def extract_current_role(lines: list[str]) -> str | None:
    return extract_labeled_value(lines, CURRENT_ROLE_PATTERN)


def extract_location(lines: list[str]) -> str | None:
    return extract_labeled_value(lines, LOCATION_PATTERN)


def is_current_end_date(value: str) -> bool:
    return value.strip().lower() in CURRENT_END_DATE_VALUES


def parse_experience_date_range(
    line: str,
) -> tuple[str, str, bool] | None:
    match = EXPERIENCE_DATE_RANGE_PATTERN.match(line.strip())

    if match is None:
        return None

    start_date = match.group("start").strip()
    end_date = match.group("end").strip()

    return (
        start_date,
        end_date,
        is_current_end_date(end_date),
    )


def extract_experience_highlight(line: str) -> str | None:
    normalized_line = line.strip()

    for prefix in EXPERIENCE_HIGHLIGHT_PREFIXES:
        if not normalized_line.startswith(prefix):
            continue

        highlight = normalized_line[len(prefix):].strip()
        return highlight or None

    return None


def _empty_experience_entry() -> dict[str, Any]:
    return {
        "company": None,
        "role": None,
        "location": None,
        "start_date": None,
        "end_date": None,
        "is_current": False,
        "highlights": [],
    }


def _experience_has_content(entry: dict[str, Any]) -> bool:
    return any(
        [
            entry["company"],
            entry["role"],
            entry["location"],
            entry["start_date"],
            entry["end_date"],
            entry["highlights"],
        ]
    )


def _looks_like_context_line(line: str) -> bool:
    if not line or len(line) > 300:
        return False

    if EMAIL_PATTERN.search(line):
        return False

    if normalize_phone(line) is not None:
        return False

    if parse_experience_date_range(line) is not None:
        return False

    if extract_experience_highlight(line) is not None:
        return False

    return True


def extract_work_experience(
    sections: dict[str, list[str]],
) -> list[ResumeExperienceEntry]:
    experience_lines = sections.get("experience", [])

    if not experience_lines:
        return []

    entries: list[ResumeExperienceEntry] = []
    current_entry = _empty_experience_entry()
    pending_context: list[str] = []

    def flush_current_entry() -> None:
        nonlocal current_entry, pending_context

        if _experience_has_content(current_entry):
            if current_entry["company"] or current_entry["role"]:
                entries.append(ResumeExperienceEntry(**current_entry))

        current_entry = _empty_experience_entry()
        pending_context = []

    for raw_line in experience_lines:
        line = raw_line.strip()

        company_match = EXPERIENCE_COMPANY_PATTERN.match(line)

        if company_match is not None:
            flush_current_entry()
            current_entry["company"] = company_match.group("value").strip()
            continue

        role_match = EXPERIENCE_ROLE_PATTERN.match(line)

        if role_match is not None:
            current_entry["role"] = role_match.group("value").strip()
            continue

        start_date_match = EXPERIENCE_START_DATE_PATTERN.match(line)

        if start_date_match is not None:
            current_entry["start_date"] = start_date_match.group("value").strip()
            continue

        end_date_match = EXPERIENCE_END_DATE_PATTERN.match(line)

        if end_date_match is not None:
            end_date = end_date_match.group("value").strip()
            current_entry["end_date"] = end_date
            current_entry["is_current"] = is_current_end_date(end_date)
            continue

        location_match = LOCATION_PATTERN.match(line)

        if location_match is not None and _experience_has_content(current_entry):
            current_entry["location"] = location_match.group("value").strip()
            continue

        pipe_parts = [part.strip() for part in line.split("|")]

        if len(pipe_parts) == 2:
            date_range = parse_experience_date_range(pipe_parts[0])

            if date_range is not None:
                if current_entry["start_date"] is not None:
                    flush_current_entry()

                start_date, end_date, is_current = date_range
                current_entry["start_date"] = start_date
                current_entry["end_date"] = end_date
                current_entry["is_current"] = is_current
                current_entry["location"] = pipe_parts[1] or None
                continue

            pipe_header = PIPE_EXPERIENCE_HEADER_PATTERN.match(line)

            if pipe_header is not None:
                flush_current_entry()
                current_entry["role"] = pipe_header.group("role").strip()
                current_entry["company"] = pipe_header.group("company").strip()
                continue

        dash_header = DASH_EXPERIENCE_HEADER_PATTERN.match(line)

        if (
            dash_header is not None
            and parse_experience_date_range(line) is None
        ):
            flush_current_entry()
            current_entry["company"] = dash_header.group("company").strip()
            current_entry["role"] = dash_header.group("role").strip()
            continue

        date_range = parse_experience_date_range(line)

        if date_range is not None:
            if current_entry["start_date"] is not None:
                flush_current_entry()

            if current_entry["company"] is None and current_entry["role"] is None:
                if len(pending_context) >= 2:
                    current_entry["company"] = pending_context[-2]
                    current_entry["role"] = pending_context[-1]
                elif len(pending_context) == 1:
                    current_entry["role"] = pending_context[-1]

            start_date, end_date, is_current = date_range
            current_entry["start_date"] = start_date
            current_entry["end_date"] = end_date
            current_entry["is_current"] = is_current
            pending_context = []
            continue

        highlight = extract_experience_highlight(line)

        if highlight is not None:
            highlights = current_entry["highlights"]

            if isinstance(highlights, list) and _experience_has_content(current_entry):
                highlights.append(highlight)
            continue

        if (
            current_entry["start_date"] is not None
            and current_entry["location"] is None
            and _looks_like_context_line(line)
        ):
            current_entry["location"] = line
            continue

        if _looks_like_context_line(line):
            pending_context.append(line)
            pending_context = pending_context[-2:]

    flush_current_entry()
    return entries


def _join_description_lines(lines: list[str]) -> str | None:
    normalized_lines = [line.strip() for line in lines if line.strip()]

    if not normalized_lines:
        return None

    return "\n".join(normalized_lines)


def extract_education(
    sections: dict[str, list[str]],
) -> list[ResumeEducationEntry]:
    education_lines = sections.get("education", [])

    if not education_lines:
        return []

    entries: list[ResumeEducationEntry] = []
    current_entry: dict[str, Any] = {
        "institution": None,
        "degree": None,
        "field_of_study": None,
        "start_date": None,
        "end_date": None,
        "description": None,
    }
    description_lines: list[str] = []

    def flush_current_entry() -> None:
        nonlocal current_entry, description_lines

        current_entry["description"] = _join_description_lines(
            description_lines
        )

        has_structured_content = any(
            [
                current_entry["institution"],
                current_entry["degree"],
                current_entry["field_of_study"],
                current_entry["start_date"],
                current_entry["end_date"],
            ]
        )

        if has_structured_content:
            entries.append(ResumeEducationEntry(**current_entry))

        current_entry = {
            "institution": None,
            "degree": None,
            "field_of_study": None,
            "start_date": None,
            "end_date": None,
            "description": None,
        }
        description_lines = []

    for line in education_lines:
        institution_match = EDUCATION_INSTITUTION_PATTERN.match(line)

        if institution_match is not None:
            if any(current_entry.values()) or description_lines:
                flush_current_entry()

            current_entry["institution"] = institution_match.group(
                "value"
            ).strip()
            continue

        degree_match = EDUCATION_DEGREE_PATTERN.match(line)

        if degree_match is not None:
            current_entry["degree"] = degree_match.group("value").strip()
            continue

        field_match = EDUCATION_FIELD_PATTERN.match(line)

        if field_match is not None:
            current_entry["field_of_study"] = field_match.group(
                "value"
            ).strip()
            continue

        date_range = parse_experience_date_range(line)

        if date_range is not None:
            current_entry["start_date"] = date_range[0]
            current_entry["end_date"] = date_range[1]
            continue

        description_match = EDUCATION_DESCRIPTION_PATTERN.match(line)

        if description_match is not None:
            description_lines.append(
                description_match.group("value").strip()
            )
            continue

        description_lines.append(line.strip())

    flush_current_entry()
    return entries


def extract_projects(
    sections: dict[str, list[str]],
) -> list[ResumeProjectEntry]:
    project_lines = sections.get("projects", [])

    if not project_lines:
        return []

    entries: list[ResumeProjectEntry] = []
    current_entry: dict[str, Any] = {
        "name": None,
        "description": None,
        "technologies": [],
        "url": None,
        "highlights": [],
    }

    def flush_current_entry() -> None:
        nonlocal current_entry

        if any(
            [
                current_entry["name"],
                current_entry["description"],
                current_entry["technologies"],
                current_entry["url"],
                current_entry["highlights"],
            ]
        ):
            entries.append(ResumeProjectEntry(**current_entry))

        current_entry = {
            "name": None,
            "description": None,
            "technologies": [],
            "url": None,
            "highlights": [],
        }

    for line in project_lines:
        name_match = PROJECT_NAME_PATTERN.match(line)

        if name_match is not None:
            if any(current_entry.values()):
                flush_current_entry()

            current_entry["name"] = name_match.group("value").strip()
            continue

        description_match = PROJECT_DESCRIPTION_PATTERN.match(line)

        if description_match is not None:
            current_entry["description"] = description_match.group(
                "value"
            ).strip()
            continue

        technologies_match = PROJECT_TECHNOLOGIES_PATTERN.match(line)

        if technologies_match is not None:
            current_entry["technologies"] = normalize_technology_list(
                technologies_match.group("value")
            )
            continue

        url_match = PROJECT_URL_PATTERN.match(line)

        if url_match is not None:
            current_entry["url"] = url_match.group("value").strip()
            continue

        highlight = extract_experience_highlight(line)

        if highlight is not None:
            highlights = current_entry["highlights"]

            if isinstance(highlights, list):
                highlights.append(highlight)
            continue

        if current_entry["name"] is None:
            current_entry["name"] = line.strip()
        elif current_entry["description"] is None:
            current_entry["description"] = line.strip()

    flush_current_entry()
    return entries


def extract_certifications(
    sections: dict[str, list[str]],
) -> list[ResumeCertificationEntry]:
    certification_lines = sections.get("certifications", [])

    if not certification_lines:
        return []

    entries: list[ResumeCertificationEntry] = []
    current_entry: dict[str, str | None] = {
        "name": None,
        "issuer": None,
        "issue_date": None,
        "expiry_date": None,
        "credential_id": None,
        "credential_url": None,
    }

    def flush_current_entry() -> None:
        nonlocal current_entry

        if any(current_entry.values()):
            entries.append(ResumeCertificationEntry(**current_entry))

        current_entry = {
            "name": None,
            "issuer": None,
            "issue_date": None,
            "expiry_date": None,
            "credential_id": None,
            "credential_url": None,
        }

    patterns_and_fields: tuple[tuple[re.Pattern[str], str], ...] = (
        (CERTIFICATION_ISSUER_PATTERN, "issuer"),
        (CERTIFICATION_ISSUE_DATE_PATTERN, "issue_date"),
        (CERTIFICATION_EXPIRY_DATE_PATTERN, "expiry_date"),
        (CERTIFICATION_CREDENTIAL_ID_PATTERN, "credential_id"),
        (CERTIFICATION_CREDENTIAL_URL_PATTERN, "credential_url"),
    )

    for line in certification_lines:
        name_match = CERTIFICATION_NAME_PATTERN.match(line)

        if name_match is not None:
            if any(current_entry.values()):
                flush_current_entry()

            current_entry["name"] = name_match.group("value").strip()
            continue

        matched = False

        for pattern, field_name in patterns_and_fields:
            match = pattern.match(line)

            if match is None:
                continue

            current_entry[field_name] = match.group("value").strip()
            matched = True
            break

        if matched:
            continue

        if current_entry["name"] is None:
            if any(current_entry.values()):
                flush_current_entry()
            current_entry["name"] = line.strip()
        else:
            flush_current_entry()
            current_entry["name"] = line.strip()

    flush_current_entry()
    return entries


def _language_key(value: str) -> str:
    base_name = re.split(r"\s*(?:-|–|—|:|\|)\s*", value, maxsplit=1)[0]
    return base_name.strip().casefold()


def extract_languages(
    sections: dict[str, list[str]],
) -> list[str]:
    language_lines = sections.get("languages", [])

    if not language_lines:
        return []

    languages_by_key: dict[str, str] = {}

    for line in language_lines:
        clean_line = line.strip().lstrip("-*•▪").strip()

        for value in re.split(r"[,;]", clean_line):
            normalized_value = re.sub(r"\s+", " ", value).strip()

            if not normalized_value:
                continue

            key = _language_key(normalized_value)

            if not key:
                continue

            existing = languages_by_key.get(key)

            if existing is None or len(normalized_value) > len(existing):
                languages_by_key[key] = normalized_value

    return list(languages_by_key.values())


def derive_current_experience_value(
    work_experience: list[ResumeExperienceEntry],
    attribute: Literal["role", "location"],
) -> str | None:
    for entry in work_experience:
        if not entry.is_current:
            continue

        value = getattr(entry, attribute)

        if value:
            return value

    return None


def to_month_index(year: int, month: int) -> int:
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
        return to_month_index(effective_date.year, effective_date.month)

    month_year_match = MONTH_YEAR_PATTERN.match(normalized_value)

    if month_year_match is not None:
        month_name = month_year_match.group("month")[:3].lower()
        month = MONTH_NAME_TO_NUMBER.get(month_name)

        if month is None:
            return None

        return to_month_index(
            int(month_year_match.group("year")),
            month,
        )

    year_only_match = YEAR_ONLY_PATTERN.match(normalized_value)

    if year_only_match is not None:
        month = 12 if is_end else 1
        return to_month_index(
            int(year_only_match.group("year")),
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
        if entry.start_date is None or entry.end_date is None:
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

        if start_month is None or end_month is None:
            continue

        if end_month < start_month:
            continue

        intervals.append((start_month, end_month))

    if not intervals:
        return None

    intervals.sort()
    merged_intervals: list[list[int]] = []

    for start_month, end_month in intervals:
        if not merged_intervals:
            merged_intervals.append([start_month, end_month])
            continue

        previous_interval = merged_intervals[-1]

        if start_month <= previous_interval[1] + 1:
            previous_interval[1] = max(previous_interval[1], end_month)
        else:
            merged_intervals.append([start_month, end_month])

    return sum(
        end_month - start_month + 1
        for start_month, end_month in merged_intervals
    )


def build_parsing_metadata(
    *,
    sections: dict[str, list[str]],
    email: str | None,
    phone: str | None,
    professional_summary: str | None,
    skills: list[str],
    work_experience: list[ResumeExperienceEntry],
    education: list[ResumeEducationEntry],
    projects: list[ResumeProjectEntry],
    certifications: list[ResumeCertificationEntry],
    languages: list[str],
    full_name: str | None,
) -> tuple[list[str], list[str], float]:
    warnings: list[str] = []

    if email is None:
        warnings.append("No email detected")

    if phone is None:
        warnings.append("No phone detected")

    if sections.get("experience") and not any(
        entry.start_date and entry.end_date
        for entry in work_experience
    ):
        warnings.append("No dated experience found")

    section_results = (
        ("education", education, "Education section found but no valid entries parsed"),
        ("projects", projects, "Projects section found but no valid entries parsed"),
        (
            "certifications",
            certifications,
            "Certifications section found but no valid entries parsed",
        ),
        ("languages", languages, "Languages section found but no valid entries parsed"),
    )

    for section_name, parsed_entries, warning in section_results:
        if sections.get(section_name) and not parsed_entries:
            warnings.append(warning)

    missing_sections = [
        section_name
        for section_name in CANONICAL_SECTION_NAMES
        if section_name not in sections
    ]

    confidence_checks = (
        bool(full_name),
        bool(email),
        bool(phone),
        bool(professional_summary),
        bool(skills),
        bool(work_experience),
        bool(education),
        bool(projects),
        bool(certifications),
        bool(languages),
    )
    confidence = round(
        sum(confidence_checks) / len(confidence_checks),
        2,
    )

    return warnings, missing_sections, confidence


def parse_resume_text(text: str) -> ResumeProfileData:
    normalized_text = text.strip()

    if not normalized_text:
        raise ResumeParsingError(
            "Resume text must not be empty."
        )

    lines = normalize_lines(normalized_text)
    sections = split_resume_sections(lines)

    work_experience = extract_work_experience(sections)
    education = extract_education(sections)
    projects = extract_projects(sections)
    certifications = extract_certifications(sections)
    languages = extract_languages(sections)

    header_lines = sections.get("header", [])
    explicit_current_role = extract_current_role(header_lines)
    explicit_location = extract_location(header_lines)

    current_role = explicit_current_role or derive_current_experience_value(
        work_experience,
        "role",
    )
    location = explicit_location or derive_current_experience_value(
        work_experience,
        "location",
    )

    full_name = extract_full_name(lines)
    email = extract_email(normalized_text)
    phone = extract_phone(normalized_text)
    professional_summary = extract_professional_summary(sections)
    skills = extract_skills(normalized_text)

    warnings, missing_sections, confidence = build_parsing_metadata(
        sections=sections,
        email=email,
        phone=phone,
        professional_summary=professional_summary,
        skills=skills,
        work_experience=work_experience,
        education=education,
        projects=projects,
        certifications=certifications,
        languages=languages,
        full_name=full_name,
    )

    return ResumeProfileData(
        full_name=full_name,
        email=email,
        phone=phone,
        location=location,
        current_role=current_role,
        professional_summary=professional_summary,
        total_experience_months=(
            calculate_total_experience_months(work_experience)
        ),
        skills=skills,
        education=education,
        work_experience=work_experience,
        projects=projects,
        certifications=certifications,
        languages=languages,
        warnings=warnings,
        missing_sections=missing_sections,
        confidence=confidence,
    )