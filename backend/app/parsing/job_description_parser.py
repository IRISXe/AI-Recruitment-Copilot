import re
from collections.abc import Iterable

from app.schemas.job_requirement_profile import (
    JobRequirementProfileData,
)


PARSER_VERSION = "job-rule-based-v1"


class JobDescriptionParsingError(ValueError):
    pass


SECTION_ALIASES = {
    "job summary": "summary",
    "summary": "summary",
    "overview": "summary",
    "about the role": "summary",
    "role overview": "summary",
    "about this role": "summary",
    "responsibilities": "responsibilities",
    "key responsibilities": "responsibilities",
    "roles and responsibilities": "responsibilities",
    "duties": "responsibilities",
    "what you will do": "responsibilities",
    "what you ll do": "responsibilities",
    "requirements": "requirements",
    "job requirements": "requirements",
    "qualifications": "requirements",
    "minimum qualifications": "requirements",
    "basic qualifications": "requirements",
    "required qualifications": "requirements",
    "required skills": "required_skills",
    "must have": "required_skills",
    "must haves": "required_skills",
    "preferred qualifications": "preferred",
    "preferred skills": "preferred",
    "nice to have": "preferred",
    "nice to haves": "preferred",
    "good to have": "preferred",
    "education": "education",
    "education requirements": "education",
    "certifications": "certifications",
    "certification requirements": "certifications",
}


SKILL_ALIASES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("React", ("react", "react.js", "reactjs")),
    ("Next.js", ("next.js", "nextjs")),
    ("Angular", ("angular", "angular.js", "angularjs")),
    ("Vue.js", ("vue", "vue.js", "vuejs")),
    ("JavaScript", ("javascript",)),
    ("TypeScript", ("typescript",)),
    ("HTML", ("html", "html5")),
    ("CSS", ("css", "css3")),
    ("Tailwind CSS", ("tailwind", "tailwind css")),
    ("Node.js", ("node.js", "nodejs")),
    ("Express.js", ("express", "express.js", "expressjs")),
    ("Python", ("python",)),
    ("FastAPI", ("fastapi",)),
    ("Django", ("django",)),
    ("Flask", ("flask",)),
    ("Java", ("java",)),
    ("Spring Boot", ("spring boot",)),
    ("REST APIs", ("rest api", "rest apis", "restful api", "restful apis")),
    ("GraphQL", ("graphql",)),
    ("Microservices", ("microservice", "microservices")),
    ("SQL", ("sql",)),
    ("PostgreSQL", ("postgresql", "postgres")),
    ("MySQL", ("mysql",)),
    ("MongoDB", ("mongodb",)),
    ("Redis", ("redis",)),
    ("Elasticsearch", ("elasticsearch", "elastic search")),
    ("Docker", ("docker",)),
    ("Kubernetes", ("kubernetes", "k8s")),
    ("AWS", ("aws", "amazon web services")),
    ("Azure", ("azure", "microsoft azure")),
    ("GCP", ("gcp", "google cloud platform")),
    ("Terraform", ("terraform",)),
    ("Git", ("git", "github", "gitlab")),
    ("CI/CD", ("ci/cd", "continuous integration", "continuous delivery")),
    ("Kafka", ("kafka", "apache kafka")),
    ("RabbitMQ", ("rabbitmq",)),
    ("Machine Learning", ("machine learning",)),
    ("Deep Learning", ("deep learning",)),
    ("NLP", ("nlp", "natural language processing")),
    ("LLMs", ("llm", "llms", "large language model")),
    ("LangChain", ("langchain",)),
    ("RAG", ("rag", "retrieval augmented generation")),
    ("PyTorch", ("pytorch",)),
    ("TensorFlow", ("tensorflow",)),
    ("Pandas", ("pandas",)),
    ("NumPy", ("numpy",)),
    ("ETL", ("etl", "extract transform load")),
    ("Apache Airflow", ("airflow", "apache airflow")),
    ("Apache Spark", ("spark", "apache spark", "pyspark")),
    ("Power BI", ("power bi", "powerbi")),
    ("Tableau", ("tableau",)),
    ("Microsoft Excel", ("excel", "microsoft excel")),
    ("SAP", ("sap",)),
    ("Agile", ("agile",)),
    ("Scrum", ("scrum",)),
    ("Jira", ("jira",)),
)


DOMAIN_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Frontend", ("frontend", "front-end", "front end")),
    ("Backend", ("backend", "back-end", "back end")),
    ("Full Stack", ("full stack", "full-stack")),
    ("DevOps", ("devops",)),
    ("Cloud", ("cloud computing", "cloud platform", "cloud services")),
    ("SaaS", ("saas", "software as a service")),
    ("FinTech", ("fintech", "financial technology")),
    ("Telecommunications", ("telecom", "telecommunications")),
    ("Healthcare", ("healthcare", "health care")),
    ("E-commerce", ("e-commerce", "ecommerce")),
    ("Data Migration", ("data migration",)),
    ("API Integration", ("api integration", "api integrations")),
    ("Data Engineering", ("data engineering",)),
    ("Artificial Intelligence", ("artificial intelligence",)),
)


BULLET_PATTERN = re.compile(
    r"^\s*(?:[-*•▪◦‣–—]+|\d+[.)])\s*"
)

RESPONSIBILITY_VERBS = re.compile(
    r"^(?:build|develop|design|create|implement|maintain|manage|"
    r"lead|support|collaborate|work|analyze|test|deploy|monitor|"
    r"optimize|review|deliver|integrate|troubleshoot|participate)\b",
    re.IGNORECASE,
)


def normalize_lines(text: str) -> list[str]:
    return [
        line.strip()
        for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
        if line.strip()
    ]


def normalize_section_heading(line: str) -> str | None:
    normalized = line.strip().strip("#*:").casefold()
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()

    return SECTION_ALIASES.get(normalized)


def split_job_sections(text: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {
        "general": [],
    }
    current_section = "general"

    for line in normalize_lines(text):
        section_name = normalize_section_heading(line)

        if section_name is not None:
            current_section = section_name
            sections.setdefault(current_section, [])
            continue

        sections.setdefault(current_section, []).append(line)

    return sections


def clean_list_item(line: str) -> str | None:
    cleaned = BULLET_PATTERN.sub("", line).strip()

    if not cleaned:
        return None

    return cleaned


def deduplicate_strings(values: Iterable[str]) -> list[str]:
    normalized_values: list[str] = []
    seen_values: set[str] = set()

    for value in values:
        normalized_value = value.strip()

        if not normalized_value:
            continue

        comparison_value = normalized_value.casefold()

        if comparison_value in seen_values:
            continue

        seen_values.add(comparison_value)
        normalized_values.append(normalized_value)

    return normalized_values


def extract_labeled_value(
    text: str,
    labels: tuple[str, ...],
) -> str | None:
    label_pattern = "|".join(
        re.escape(label)
        for label in labels
    )

    match = re.search(
        rf"^\s*(?:{label_pattern})\s*[:\-]\s*(.+?)\s*$",
        text,
        flags=re.IGNORECASE | re.MULTILINE,
    )

    if match is None:
        return None

    value = match.group(1).strip()

    return value or None


def _contains_alias(
    text: str,
    alias: str,
) -> re.Match[str] | None:
    return re.search(
        rf"(?<!\w){re.escape(alias)}(?!\w)",
        text,
        flags=re.IGNORECASE,
    )


def extract_known_values(
    text: str,
    aliases: tuple[tuple[str, tuple[str, ...]], ...],
) -> list[str]:
    matches: list[tuple[int, str]] = []

    for canonical_value, possible_aliases in aliases:
        earliest_position: int | None = None

        for alias in possible_aliases:
            match = _contains_alias(text, alias)

            if match is None:
                continue

            if earliest_position is None or match.start() < earliest_position:
                earliest_position = match.start()

        if earliest_position is not None:
            matches.append(
                (
                    earliest_position,
                    canonical_value,
                )
            )

    matches.sort(key=lambda item: item[0])

    return deduplicate_strings(
        canonical_value
        for _, canonical_value in matches
    )


def extract_skills(text: str) -> list[str]:
    return extract_known_values(
        text,
        SKILL_ALIASES,
    )


def _section_text(
    sections: dict[str, list[str]],
    section_names: tuple[str, ...],
) -> str:
    values: list[str] = []

    for section_name in section_names:
        values.extend(sections.get(section_name, []))

    return "\n".join(values)


def extract_job_title(
    text: str,
    sections: dict[str, list[str]],
) -> str | None:
    labeled_title = extract_labeled_value(
        text,
        (
            "job title",
            "position",
            "role",
        ),
    )

    if labeled_title is not None:
        return labeled_title[:200]

    title_pattern = re.compile(
        r"\b(?:engineer|developer|analyst|manager|consultant|"
        r"architect|specialist|administrator|intern|director|"
        r"lead|designer|scientist)\b",
        re.IGNORECASE,
    )

    for line in sections.get("general", [])[:5]:
        if len(line) > 200:
            continue

        if normalize_section_heading(line) is not None:
            continue

        if title_pattern.search(line) is None:
            continue

        if line.endswith("."):
            continue

        return clean_list_item(line)

    return None


def extract_department(text: str) -> str | None:
    return extract_labeled_value(
        text,
        (
            "department",
            "team",
            "business unit",
        ),
    )


def extract_location(text: str) -> str | None:
    return extract_labeled_value(
        text,
        (
            "location",
            "job location",
            "work location",
            "based in",
        ),
    )


def extract_employment_type(text: str) -> str | None:
    patterns = (
        (
            "full_time",
            r"\b(?:full[- ]time|permanent position|permanent role)\b",
        ),
        (
            "part_time",
            r"\bpart[- ]time\b",
        ),
        (
            "contract",
            r"\b(?:contract|contractor|contractual)\b",
        ),
        (
            "internship",
            r"\b(?:internship|intern position|intern role)\b",
        ),
    )

    for employment_type, pattern in patterns:
        if re.search(pattern, text, flags=re.IGNORECASE):
            return employment_type

    return None


def extract_work_mode(text: str) -> str | None:
    if re.search(
        r"\bhybrid\b",
        text,
        flags=re.IGNORECASE,
    ):
        return "hybrid"

    if re.search(
        r"\b(?:on[- ]site|onsite|work from office|in[- ]office)\b",
        text,
        flags=re.IGNORECASE,
    ):
        return "onsite"

    if re.search(
        r"\b(?:remote|work from home|wfh)\b",
        text,
        flags=re.IGNORECASE,
    ):
        return "remote"

    return None


def extract_seniority_level(text: str) -> str | None:
    patterns = (
        ("executive", r"\b(?:executive|chief|c-level)\b"),
        ("director", r"\bdirector\b"),
        ("manager", r"\bmanager\b"),
        ("lead", r"\b(?:lead|team lead|technical lead)\b"),
        ("senior", r"\b(?:senior|sr\.?)\b"),
        ("junior", r"\b(?:junior|jr\.?)\b"),
        (
            "entry",
            r"\b(?:entry[- ]level|graduate role|fresher)\b",
        ),
        ("intern", r"\b(?:intern|internship)\b"),
        ("mid", r"\b(?:mid[- ]level|intermediate)\b"),
    )

    for seniority_level, pattern in patterns:
        if re.search(pattern, text, flags=re.IGNORECASE):
            return seniority_level

    return None


def extract_experience_range(
    text: str,
) -> tuple[int | None, int | None]:
    range_match = re.search(
        r"\b(\d{1,2})\s*(?:-|–|—|to)\s*(\d{1,2})\s*"
        r"(?:\+?\s*)?(?:years?|yrs?)\b",
        text,
        flags=re.IGNORECASE,
    )

    if range_match is not None:
        first_value = int(range_match.group(1))
        second_value = int(range_match.group(2))

        return (
            min(first_value, second_value),
            max(first_value, second_value),
        )

    minimum_match = re.search(
        r"\b(?:minimum(?: of)?|at least|more than)\s+"
        r"(\d{1,2})\+?\s*(?:years?|yrs?)\b",
        text,
        flags=re.IGNORECASE,
    )

    maximum_match = re.search(
        r"\b(?:maximum(?: of)?|up to|not more than)\s+"
        r"(\d{1,2})\s*(?:years?|yrs?)\b",
        text,
        flags=re.IGNORECASE,
    )

    minimum_experience = (
        int(minimum_match.group(1))
        if minimum_match is not None
        else None
    )
    maximum_experience = (
        int(maximum_match.group(1))
        if maximum_match is not None
        else None
    )

    if minimum_experience is None:
        plus_match = re.search(
            r"\b(\d{1,2})\+\s*(?:years?|yrs?)\b",
            text,
            flags=re.IGNORECASE,
        )

        if plus_match is not None:
            minimum_experience = int(
                plus_match.group(1)
            )

    if minimum_experience is None:
        general_match = re.search(
            r"\b(\d{1,2})\s*(?:years?|yrs?)\s+"
            r"(?:of\s+)?experience\b",
            text,
            flags=re.IGNORECASE,
        )

        if general_match is not None:
            minimum_experience = int(
                general_match.group(1)
            )

    return (
        minimum_experience,
        maximum_experience,
    )


def extract_summary(
    sections: dict[str, list[str]],
) -> str | None:
    summary_lines = sections.get("summary", [])

    if summary_lines:
        return " ".join(summary_lines)[:5000]

    general_lines = sections.get("general", [])

    usable_lines = [
        line
        for line in general_lines
        if normalize_section_heading(line) is None
    ]

    if not usable_lines:
        return None

    return " ".join(usable_lines[:3])[:5000]


def extract_responsibilities(
    text: str,
    sections: dict[str, list[str]],
) -> list[str]:
    responsibility_lines = sections.get(
        "responsibilities",
        [],
    )

    responsibilities = [
        cleaned
        for line in responsibility_lines
        if (cleaned := clean_list_item(line)) is not None
    ]

    if responsibilities:
        return deduplicate_strings(responsibilities)

    inferred_responsibilities: list[str] = []

    for line in normalize_lines(text):
        if BULLET_PATTERN.match(line) is None:
            continue

        cleaned = clean_list_item(line)

        if cleaned is None:
            continue

        if RESPONSIBILITY_VERBS.search(cleaned):
            inferred_responsibilities.append(cleaned)

    return deduplicate_strings(
        inferred_responsibilities
    )


def extract_education(
    text: str,
) -> tuple[list[str], list[str]]:
    education_pattern = re.compile(
        r"\b(?:bachelor(?:'s)?|master(?:'s)?|doctorate|phd|"
        r"degree|b\.?\s?tech|m\.?\s?tech|b\.?\s?e\.?|"
        r"m\.?\s?e\.?|bsc|msc|mba|computer science|"
        r"engineering degree)\b",
        re.IGNORECASE,
    )

    preferred_pattern = re.compile(
        r"\b(?:preferred|desirable|nice to have|good to have)\b",
        re.IGNORECASE,
    )

    required_education: list[str] = []
    preferred_education: list[str] = []

    for line in normalize_lines(text):
        cleaned = clean_list_item(line)

        if cleaned is None:
            continue

        if education_pattern.search(cleaned) is None:
            continue

        if len(cleaned) > 500:
            continue

        if preferred_pattern.search(cleaned):
            preferred_education.append(cleaned)
        else:
            required_education.append(cleaned)

    return (
        deduplicate_strings(required_education),
        deduplicate_strings(preferred_education),
    )


def extract_certifications(
    text: str,
) -> tuple[list[str], list[str]]:
    certification_pattern = re.compile(
        r"\b(?:certification|certified|certificate|aws certified|"
        r"azure certified|pmp|scrum master|cissp|cka|ckad)\b",
        re.IGNORECASE,
    )

    preferred_pattern = re.compile(
        r"\b(?:preferred|desirable|nice to have|good to have)\b",
        re.IGNORECASE,
    )

    required_certifications: list[str] = []
    preferred_certifications: list[str] = []

    for line in normalize_lines(text):
        cleaned = clean_list_item(line)

        if cleaned is None:
            continue

        if certification_pattern.search(cleaned) is None:
            continue

        if len(cleaned) > 500:
            continue

        if preferred_pattern.search(cleaned):
            preferred_certifications.append(cleaned)
        else:
            required_certifications.append(cleaned)

    return (
        deduplicate_strings(required_certifications),
        deduplicate_strings(preferred_certifications),
    )


def extract_keywords(
    text: str,
    required_skills: list[str],
    preferred_skills: list[str],
) -> list[str]:
    domain_keywords = extract_known_values(
        text,
        DOMAIN_KEYWORDS,
    )

    return deduplicate_strings(
        [
            *required_skills,
            *preferred_skills,
            *domain_keywords,
        ]
    )


def build_parsing_metadata(
    *,
    job_title: str | None,
    summary: str | None,
    responsibilities: list[str],
    required_skills: list[str],
    minimum_experience_years: int | None,
    required_education: list[str],
    employment_type: str | None,
    work_mode: str | None,
    location: str | None,
) -> tuple[list[str], list[str], float]:
    warnings: list[str] = []
    missing_sections: list[str] = []

    if job_title is None:
        missing_sections.append("job_title")

    if not responsibilities:
        missing_sections.append("responsibilities")
        warnings.append(
            "No responsibilities were identified."
        )

    if not required_skills:
        missing_sections.append("required_skills")
        warnings.append(
            "No required skills were identified."
        )

    if minimum_experience_years is None:
        missing_sections.append("experience")
        warnings.append(
            "No minimum experience requirement was identified."
        )

    if not required_education:
        warnings.append(
            "No required education was identified."
        )

    confidence = 0.0

    if job_title is not None:
        confidence += 0.10

    if summary is not None:
        confidence += 0.10

    if responsibilities:
        confidence += 0.20

    if required_skills:
        confidence += 0.25

    if minimum_experience_years is not None:
        confidence += 0.15

    if required_education:
        confidence += 0.05

    if employment_type is not None:
        confidence += 0.05

    if work_mode is not None:
        confidence += 0.05

    if location is not None:
        confidence += 0.05

    return (
        warnings,
        missing_sections,
        round(min(confidence, 1.0), 2),
    )


def parse_job_description(
    text: str,
) -> JobRequirementProfileData:
    if not text or not text.strip():
        raise JobDescriptionParsingError(
            "The job description is empty."
        )

    if len(text.strip()) < 20:
        raise JobDescriptionParsingError(
            "The job description is too short to parse."
        )

    sections = split_job_sections(text)

    required_section_text = _section_text(
        sections,
        (
            "requirements",
            "required_skills",
        ),
    )
    preferred_section_text = _section_text(
        sections,
        (
            "preferred",
        ),
    )

    required_skills = extract_skills(
        required_section_text
    )
    preferred_skills = extract_skills(
        preferred_section_text
    )

    all_detected_skills = extract_skills(text)

    if not required_skills:
        required_skills = [
            skill
            for skill in all_detected_skills
            if skill not in preferred_skills
        ]
    else:
        required_skills = deduplicate_strings(
            [
                *required_skills,
                *[
                    skill
                    for skill in all_detected_skills
                    if skill not in preferred_skills
                ],
            ]
        )

    required_skill_keys = {
        skill.casefold()
        for skill in required_skills
    }

    preferred_skills = [
        skill
        for skill in preferred_skills
        if skill.casefold() not in required_skill_keys
    ]

    job_title = extract_job_title(
        text,
        sections,
    )
    department = extract_department(text)
    location = extract_location(text)
    employment_type = extract_employment_type(text)
    work_mode = extract_work_mode(text)
    seniority_level = extract_seniority_level(text)
    summary = extract_summary(sections)
    responsibilities = extract_responsibilities(
        text,
        sections,
    )

    (
        minimum_experience_years,
        maximum_experience_years,
    ) = extract_experience_range(text)

    (
        required_education,
        preferred_education,
    ) = extract_education(text)

    (
        required_certifications,
        preferred_certifications,
    ) = extract_certifications(text)

    keywords = extract_keywords(
        text,
        required_skills,
        preferred_skills,
    )

    (
        warnings,
        missing_sections,
        confidence,
    ) = build_parsing_metadata(
        job_title=job_title,
        summary=summary,
        responsibilities=responsibilities,
        required_skills=required_skills,
        minimum_experience_years=minimum_experience_years,
        required_education=required_education,
        employment_type=employment_type,
        work_mode=work_mode,
        location=location,
    )

    return JobRequirementProfileData(
        job_title=job_title,
        department=department,
        location=location,
        employment_type=employment_type,
        work_mode=work_mode,
        seniority_level=seniority_level,
        summary=summary,
        responsibilities=responsibilities,
        required_skills=required_skills,
        preferred_skills=preferred_skills,
        minimum_experience_years=minimum_experience_years,
        maximum_experience_years=maximum_experience_years,
        required_education=required_education,
        preferred_education=preferred_education,
        required_certifications=required_certifications,
        preferred_certifications=preferred_certifications,
        keywords=keywords,
        warnings=warnings,
        missing_sections=missing_sections,
        confidence=confidence,
    )