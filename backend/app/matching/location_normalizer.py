import re
from typing import Final


LOCATION_PHRASE_ALIASES: Final[dict[str, str]] = {
    "bangalore": "bengaluru",
    "bombay": "mumbai",
    "calcutta": "kolkata",
    "madras": "chennai",
    "new delhi": "delhi",
    "delhi ncr": "delhi",
    "national capital region": "delhi",
}


def _replace_location_aliases(value: str) -> str:
    normalized_value = value

    ordered_aliases = sorted(
        LOCATION_PHRASE_ALIASES.items(),
        key=lambda item: len(item[0]),
        reverse=True,
    )

    for alias, canonical_value in ordered_aliases:
        normalized_value = re.sub(
            rf"(?<!\w){re.escape(alias)}(?!\w)",
            canonical_value,
            normalized_value,
        )

    return normalized_value


def normalize_location_text(value: str) -> str:
    normalized_value = value.casefold().strip()

    if not normalized_value:
        return ""

    normalized_value = normalized_value.replace("&", " and ")
    normalized_value = re.sub(
        r"[^a-z0-9]+",
        " ",
        normalized_value,
    )
    normalized_value = re.sub(
        r"\s+",
        " ",
        normalized_value,
    ).strip()

    return _replace_location_aliases(
        normalized_value
    )


def primary_location_key(value: str) -> str:
    primary_segment = re.split(
        r"[,|/]",
        value,
        maxsplit=1,
    )[0]

    return normalize_location_text(
        primary_segment
    )


def locations_match(
    candidate_location: str,
    job_location: str,
) -> bool:
    normalized_candidate = normalize_location_text(
        candidate_location
    )
    normalized_job = normalize_location_text(
        job_location
    )

    if not normalized_candidate or not normalized_job:
        return False

    if normalized_candidate == normalized_job:
        return True

    candidate_primary = primary_location_key(
        candidate_location
    )
    job_primary = primary_location_key(
        job_location
    )

    if (
        candidate_primary
        and candidate_primary == job_primary
    ):
        return True

    candidate_terms = normalized_candidate.split()
    job_terms = normalized_job.split()

    if (
        candidate_terms
        and job_terms
        and candidate_terms[0] == job_terms[0]
    ):
        candidate_term_set = set(candidate_terms)
        job_term_set = set(job_terms)

        if (
            candidate_term_set.issubset(job_term_set)
            or job_term_set.issubset(candidate_term_set)
        ):
            return True

    return False