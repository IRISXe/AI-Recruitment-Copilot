import re
from collections.abc import Iterable, Iterator

from app.parsing.job_description_parser import (
    SKILL_ALIASES as JOB_SKILL_ALIASES,
)
from app.parsing.resume_parser import (
    SKILL_ALIASES as RESUME_SKILL_ALIASES,
)


CANONICAL_NAME_OVERRIDES: dict[str, str] = {
    "React.js": "React",
}


def normalize_skill_text(value: str) -> str:
    return re.sub(
        r"\s+",
        " ",
        value.strip(),
    )


def _comparison_key(value: str) -> str:
    return normalize_skill_text(value).casefold()


def _iter_skill_alias_groups() -> Iterator[
    tuple[str, tuple[str, ...]]
]:
    yield from JOB_SKILL_ALIASES

    for canonical_name, aliases in RESUME_SKILL_ALIASES.items():
        yield canonical_name, aliases


def _build_alias_lookup() -> dict[str, str]:
    alias_lookup: dict[str, str] = {}

    for canonical_name, aliases in _iter_skill_alias_groups():
        preferred_canonical_name = CANONICAL_NAME_OVERRIDES.get(
            canonical_name,
            canonical_name,
        )

        values = (
            canonical_name,
            *aliases,
        )

        for value in values:
            key = _comparison_key(value)

            existing_value = alias_lookup.get(key)

            if (
                existing_value is not None
                and existing_value != preferred_canonical_name
            ):
                raise RuntimeError(
                    "Conflicting canonical skill mappings for "
                    f"'{value}': '{existing_value}' and "
                    f"'{preferred_canonical_name}'."
                )

            alias_lookup[key] = preferred_canonical_name

    return alias_lookup


SKILL_ALIAS_LOOKUP = _build_alias_lookup()


def canonicalize_skill(value: str) -> str | None:
    normalized_value = normalize_skill_text(value)

    if not normalized_value:
        return None

    return SKILL_ALIAS_LOOKUP.get(
        normalized_value.casefold(),
        normalized_value,
    )


def skill_comparison_key(value: str) -> str | None:
    canonical_skill = canonicalize_skill(value)

    if canonical_skill is None:
        return None

    return canonical_skill.casefold()


def normalize_skill_list(
    values: Iterable[str],
) -> list[str]:
    normalized_skills: list[str] = []
    seen_skills: set[str] = set()

    for value in values:
        canonical_skill = canonicalize_skill(value)

        if canonical_skill is None:
            continue

        comparison_key = canonical_skill.casefold()

        if comparison_key in seen_skills:
            continue

        seen_skills.add(comparison_key)
        normalized_skills.append(canonical_skill)

    return normalized_skills