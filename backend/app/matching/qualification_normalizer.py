import re
from collections.abc import Callable, Iterable


EDUCATION_PHRASE_ALIASES: dict[str, str] = {
    "bachelor of technology": "bachelor",
    "bachelor of engineering": "bachelor",
    "bachelor of science": "bachelor",
    "bachelors degree": "bachelor",
    "bachelor degree": "bachelor",
    "b tech": "bachelor",
    "btech": "bachelor",
    "b sc": "bachelor",
    "bsc": "bachelor",
    "master of technology": "master",
    "master of engineering": "master",
    "master of science": "master",
    "masters degree": "master",
    "master degree": "master",
    "m tech": "master",
    "mtech": "master",
    "m sc": "master",
    "msc": "master",
    "doctor of philosophy": "doctorate",
    "doctoral degree": "doctorate",
    "ph d": "doctorate",
    "phd": "doctorate",
    "computer science and engineering": "computer science",
    "computer engineering": "computer science",
    "cse": "computer science",
}


CERTIFICATION_PHRASE_ALIASES: dict[str, str] = {
    "amazon web services": "aws",
    "google cloud platform": "gcp",
    "microsoft azure": "azure",
}


EDUCATION_IGNORED_TERMS: frozenset[str] = frozenset(
    {
        "a",
        "an",
        "and",
        "degree",
        "equivalent",
        "field",
        "from",
        "in",
        "of",
        "or",
        "preferred",
        "qualification",
        "qualifications",
        "related",
        "required",
        "requirement",
        "the",
        "with",
    }
)


CERTIFICATION_IGNORED_TERMS: frozenset[str] = frozenset(
    {
        "a",
        "an",
        "and",
        "certificate",
        "certification",
        "certifications",
        "certified",
        "from",
        "in",
        "of",
        "or",
        "preferred",
        "qualification",
        "qualifications",
        "required",
        "requirement",
        "the",
        "with",
    }
)


def normalize_match_text(value: str) -> str:
    normalized_value = value.casefold()
    normalized_value = normalized_value.replace("&", " and ")
    normalized_value = normalized_value.replace("’", "'")
    normalized_value = normalized_value.replace("'s", "s")

    normalized_value = re.sub(
        r"[^a-z0-9+#.]+",
        " ",
        normalized_value,
    )

    return re.sub(
        r"\s+",
        " ",
        normalized_value,
    ).strip()


def _replace_phrase_aliases(
    value: str,
    aliases: dict[str, str],
) -> str:
    normalized_value = value

    ordered_aliases = sorted(
        aliases.items(),
        key=lambda item: len(item[0]),
        reverse=True,
    )

    for alias, canonical_value in ordered_aliases:
        normalized_alias = normalize_match_text(alias)

        normalized_value = re.sub(
            rf"(?<!\w){re.escape(normalized_alias)}(?!\w)",
            canonical_value,
            normalized_value,
        )

    return re.sub(
        r"\s+",
        " ",
        normalized_value,
    ).strip()


def _remove_ignored_terms(
    value: str,
    ignored_terms: frozenset[str],
) -> str:
    meaningful_terms = [
        term
        for term in value.split()
        if term not in ignored_terms
    ]

    return " ".join(meaningful_terms)


def normalize_education_text(value: str) -> str:
    normalized_value = normalize_match_text(value)

    if not normalized_value:
        return ""

    normalized_value = _replace_phrase_aliases(
        normalized_value,
        EDUCATION_PHRASE_ALIASES,
    )

    return _remove_ignored_terms(
        normalized_value,
        EDUCATION_IGNORED_TERMS,
    )


def normalize_certification_text(value: str) -> str:
    normalized_value = normalize_match_text(value)

    if not normalized_value:
        return ""

    normalized_value = _replace_phrase_aliases(
        normalized_value,
        CERTIFICATION_PHRASE_ALIASES,
    )

    return _remove_ignored_terms(
        normalized_value,
        CERTIFICATION_IGNORED_TERMS,
    )


def normalized_term_set(value: str) -> frozenset[str]:
    return frozenset(
        term
        for term in value.split()
        if term
    )


def normalize_text_list(
    values: Iterable[str],
    *,
    normalizer: Callable[[str], str],
) -> list[str]:
    normalized_values: list[str] = []
    seen_values: set[str] = set()

    for value in values:
        normalized_value = normalizer(value)

        if not normalized_value:
            continue

        if normalized_value in seen_values:
            continue

        seen_values.add(normalized_value)
        normalized_values.append(normalized_value)

    return normalized_values