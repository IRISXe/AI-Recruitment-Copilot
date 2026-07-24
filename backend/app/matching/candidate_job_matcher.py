from collections.abc import Iterable
from dataclasses import dataclass
from typing import Final, Literal
from datetime import datetime
from uuid import UUID

from app.schemas.candidate_job_match import (
    CandidateJobMatchAnalysisData,
    CandidateJobMatchCreate,
)

from app.matching.location_normalizer import (
    locations_match,
    normalize_location_text,
)
from app.matching.qualification_normalizer import (
    normalize_certification_text,
    normalize_education_text,
    normalized_term_set,
)
from app.matching.skill_normalizer import (
    normalize_skill_list,
    skill_comparison_key,
)
from app.schemas.job_requirement_profile import (
    JobRequirementProfileData,
    JobRequirementProfileResponse,
    JobWorkMode,
)
from app.schemas.resume_profile import (
    ResumeCertificationEntry,
    ResumeEducationEntry,
    ResumeProfileData,
    ResumeProfileResponse,
)

SCORING_VERSION: Final[str] = "candidate-job-rule-based-v1"


@dataclass(frozen=True, slots=True)
class MatchScoringPolicy:
    skill_weight: float = 0.50
    experience_weight: float = 0.20
    education_weight: float = 0.10
    certification_weight: float = 0.05
    location_weight: float = 0.05
    work_mode_weight: float = 0.10

    required_skill_weight: float = 0.80
    preferred_skill_weight: float = 0.20

    zero_required_skill_match_cap: float = 35.0

    low_required_skill_coverage_threshold: float = 0.50
    low_required_skill_match_cap: float = 49.0

    moderate_required_skill_coverage_threshold: float = 0.75
    moderate_required_skill_match_cap: float = 69.0

    strong_match_threshold: float = 85.0
    good_match_threshold: float = 70.0
    partial_match_threshold: float = 50.0

    insufficient_data_confidence_threshold: float = 40.0

    def __post_init__(self) -> None:
        overall_weight_total = (
            self.skill_weight
            + self.experience_weight
            + self.education_weight
            + self.certification_weight
            + self.location_weight
            + self.work_mode_weight
        )

        if abs(overall_weight_total - 1.0) > 0.000001:
            raise ValueError(
                "Overall scoring weights must add up to 1.0."
            )

        skill_weight_total = (
            self.required_skill_weight
            + self.preferred_skill_weight
        )

        if abs(skill_weight_total - 1.0) > 0.000001:
            raise ValueError(
                "Required and preferred skill weights must "
                "add up to 1.0."
            )

        bounded_values = (
            self.skill_weight,
            self.experience_weight,
            self.education_weight,
            self.certification_weight,
            self.location_weight,
            self.work_mode_weight,
            self.required_skill_weight,
            self.preferred_skill_weight,
            self.low_required_skill_coverage_threshold,
            self.moderate_required_skill_coverage_threshold,
        )

        if any(
            value < 0.0 or value > 1.0
            for value in bounded_values
        ):
            raise ValueError(
                "Scoring weights and coverage thresholds must "
                "be between 0.0 and 1.0."
            )

        score_values = (
            self.zero_required_skill_match_cap,
            self.low_required_skill_match_cap,
            self.moderate_required_skill_match_cap,
            self.strong_match_threshold,
            self.good_match_threshold,
            self.partial_match_threshold,
            self.insufficient_data_confidence_threshold,
        )

        if any(
            value < 0.0 or value > 100.0
            for value in score_values
        ):
            raise ValueError(
                "Score caps and recommendation thresholds must "
                "be between 0 and 100."
            )

        if not (
            self.low_required_skill_coverage_threshold
            < self.moderate_required_skill_coverage_threshold
        ):
            raise ValueError(
                "Required-skill coverage thresholds must be "
                "in ascending order."
            )

        if not (
            self.zero_required_skill_match_cap
            < self.low_required_skill_match_cap
            < self.moderate_required_skill_match_cap
        ):
            raise ValueError(
                "Required-skill score caps must be in "
                "ascending order."
            )

        if not (
            self.strong_match_threshold
            > self.good_match_threshold
            > self.partial_match_threshold
        ):
            raise ValueError(
                "Recommendation thresholds must be in "
                "descending order."
            )


DEFAULT_SCORING_POLICY = MatchScoringPolicy()


@dataclass(frozen=True, slots=True)
class SkillMatchResult:
    score: float
    required_score: float | None
    preferred_score: float | None
    required_coverage: float | None
    preferred_coverage: float | None
    matched_required_skills: tuple[str, ...]
    missing_required_skills: tuple[str, ...]
    matched_preferred_skills: tuple[str, ...]
    missing_preferred_skills: tuple[str, ...]


def _build_skill_map(
    values: Iterable[str],
) -> dict[str, str]:
    normalized_values = normalize_skill_list(values)
    skill_map: dict[str, str] = {}

    for value in normalized_values:
        comparison_key = skill_comparison_key(value)

        if comparison_key is None:
            continue

        skill_map[comparison_key] = value

    return skill_map


def _calculate_coverage(
    matched_count: int,
    total_count: int,
) -> float | None:
    if total_count == 0:
        return None

    return matched_count / total_count


def _coverage_to_score(
    coverage: float | None,
) -> float | None:
    if coverage is None:
        return None

    return round(
        coverage * 100.0,
        2,
    )


def score_skill_alignment(
    *,
    candidate_skills: Iterable[str],
    required_skills: Iterable[str],
    preferred_skills: Iterable[str],
    policy: MatchScoringPolicy = DEFAULT_SCORING_POLICY,
) -> SkillMatchResult:
    candidate_skill_map = _build_skill_map(candidate_skills)
    required_skill_map = _build_skill_map(required_skills)
    preferred_skill_map = _build_skill_map(preferred_skills)

    for required_key in required_skill_map:
        preferred_skill_map.pop(
            required_key,
            None,
        )

    candidate_skill_keys = set(candidate_skill_map)

    matched_required_keys = (
        candidate_skill_keys
        & set(required_skill_map)
    )
    matched_preferred_keys = (
        candidate_skill_keys
        & set(preferred_skill_map)
    )

    matched_required_skills = tuple(
        value
        for key, value in required_skill_map.items()
        if key in matched_required_keys
    )
    missing_required_skills = tuple(
        value
        for key, value in required_skill_map.items()
        if key not in matched_required_keys
    )

    matched_preferred_skills = tuple(
        value
        for key, value in preferred_skill_map.items()
        if key in matched_preferred_keys
    )
    missing_preferred_skills = tuple(
        value
        for key, value in preferred_skill_map.items()
        if key not in matched_preferred_keys
    )

    required_coverage = _calculate_coverage(
        len(matched_required_skills),
        len(required_skill_map),
    )
    preferred_coverage = _calculate_coverage(
        len(matched_preferred_skills),
        len(preferred_skill_map),
    )

    required_score = _coverage_to_score(
        required_coverage
    )
    preferred_score = _coverage_to_score(
        preferred_coverage
    )

    available_weight = 0.0
    weighted_score = 0.0

    if required_score is not None:
        available_weight += policy.required_skill_weight
        weighted_score += (
            required_score
            * policy.required_skill_weight
        )

    if preferred_score is not None:
        available_weight += policy.preferred_skill_weight
        weighted_score += (
            preferred_score
            * policy.preferred_skill_weight
        )

    if available_weight == 0.0:
        combined_score = 0.0
    else:
        combined_score = round(
            weighted_score / available_weight,
            2,
        )

    return SkillMatchResult(
        score=combined_score,
        required_score=required_score,
        preferred_score=preferred_score,
        required_coverage=required_coverage,
        preferred_coverage=preferred_coverage,
        matched_required_skills=matched_required_skills,
        missing_required_skills=missing_required_skills,
        matched_preferred_skills=matched_preferred_skills,
        missing_preferred_skills=missing_preferred_skills,
    )
ExperienceAlignmentStatus = Literal[
    "requirement_not_specified",
    "candidate_experience_missing",
    "below_minimum",
    "within_range",
    "meets_minimum",
    "within_maximum",
    "above_maximum",
]


@dataclass(frozen=True, slots=True)
class ExperienceMatchResult:
    score: float
    status: ExperienceAlignmentStatus
    candidate_experience_months: int | None
    minimum_experience_months: int | None
    maximum_experience_months: int | None
    gap_months: int | None
    meets_minimum: bool | None
    within_maximum: bool | None


def _years_to_months(
    value: int | None,
) -> int | None:
    if value is None:
        return None

    if value < 0:
        raise ValueError(
            "Experience requirements must not be negative."
        )

    return value * 12


def score_experience_alignment(
    *,
    candidate_experience_months: int | None,
    minimum_experience_years: int | None,
    maximum_experience_years: int | None,
) -> ExperienceMatchResult:
    minimum_experience_months = _years_to_months(
        minimum_experience_years
    )
    maximum_experience_months = _years_to_months(
        maximum_experience_years
    )

    if (
        minimum_experience_months is not None
        and maximum_experience_months is not None
        and maximum_experience_months
        < minimum_experience_months
    ):
        raise ValueError(
            "Maximum experience must not be lower than "
            "minimum experience."
        )

    if (
        candidate_experience_months is not None
        and candidate_experience_months < 0
    ):
        raise ValueError(
            "Candidate experience must not be negative."
        )

    if (
        minimum_experience_months is None
        and maximum_experience_months is None
    ):
        return ExperienceMatchResult(
            score=0.0,
            status="requirement_not_specified",
            candidate_experience_months=(
                candidate_experience_months
            ),
            minimum_experience_months=None,
            maximum_experience_months=None,
            gap_months=None,
            meets_minimum=None,
            within_maximum=None,
        )

    if candidate_experience_months is None:
        return ExperienceMatchResult(
            score=0.0,
            status="candidate_experience_missing",
            candidate_experience_months=None,
            minimum_experience_months=(
                minimum_experience_months
            ),
            maximum_experience_months=(
                maximum_experience_months
            ),
            gap_months=None,
            meets_minimum=None,
            within_maximum=None,
        )

    meets_minimum = (
        minimum_experience_months is None
        or candidate_experience_months
        >= minimum_experience_months
    )
    within_maximum = (
        maximum_experience_months is None
        or candidate_experience_months
        <= maximum_experience_months
    )

    if (
        minimum_experience_months is not None
        and candidate_experience_months
        < minimum_experience_months
    ):
        if minimum_experience_months == 0:
            score = 100.0
        else:
            score = round(
                (
                    candidate_experience_months
                    / minimum_experience_months
                )
                * 100.0,
                2,
            )

        return ExperienceMatchResult(
            score=score,
            status="below_minimum",
            candidate_experience_months=(
                candidate_experience_months
            ),
            minimum_experience_months=(
                minimum_experience_months
            ),
            maximum_experience_months=(
                maximum_experience_months
            ),
            gap_months=(
                minimum_experience_months
                - candidate_experience_months
            ),
            meets_minimum=False,
            within_maximum=within_maximum,
        )

    if (
        maximum_experience_months is not None
        and candidate_experience_months
        > maximum_experience_months
    ):
        if candidate_experience_months == 0:
            score = 100.0
        else:
            score = round(
                (
                    maximum_experience_months
                    / candidate_experience_months
                )
                * 100.0,
                2,
            )

        return ExperienceMatchResult(
            score=score,
            status="above_maximum",
            candidate_experience_months=(
                candidate_experience_months
            ),
            minimum_experience_months=(
                minimum_experience_months
            ),
            maximum_experience_months=(
                maximum_experience_months
            ),
            gap_months=(
                candidate_experience_months
                - maximum_experience_months
            ),
            meets_minimum=meets_minimum,
            within_maximum=False,
        )

    if (
        minimum_experience_months is not None
        and maximum_experience_months is not None
    ):
        status: ExperienceAlignmentStatus = "within_range"
    elif minimum_experience_months is not None:
        status = "meets_minimum"
    else:
        status = "within_maximum"

    return ExperienceMatchResult(
        score=100.0,
        status=status,
        candidate_experience_months=(
            candidate_experience_months
        ),
        minimum_experience_months=(
            minimum_experience_months
        ),
        maximum_experience_months=(
            maximum_experience_months
        ),
        gap_months=0,
        meets_minimum=meets_minimum,
        within_maximum=within_maximum,
    )
EDUCATION_LEVEL_RANK: Final[dict[str, int]] = {
    "diploma": 1,
    "bachelor": 2,
    "master": 3,
    "doctorate": 4,
}


@dataclass(frozen=True, slots=True)
class EducationMatchResult:
    score: float
    required_score: float | None
    preferred_score: float | None
    required_coverage: float | None
    preferred_coverage: float | None
    candidate_education: tuple[str, ...]
    matched_required_education: tuple[str, ...]
    missing_required_education: tuple[str, ...]
    matched_preferred_education: tuple[str, ...]
    missing_preferred_education: tuple[str, ...]


def _build_candidate_education_values(
    education_entries: Iterable[ResumeEducationEntry],
) -> tuple[str, ...]:
    candidate_values: list[str] = []
    seen_values: set[str] = set()

    for entry in education_entries:
        parts = [
            value
            for value in (
                entry.degree,
                entry.field_of_study,
            )
            if value
        ]

        if not parts:
            continue

        normalized_value = normalize_education_text(
            " ".join(parts)
        )

        if (
            not normalized_value
            or normalized_value in seen_values
        ):
            continue

        seen_values.add(normalized_value)
        candidate_values.append(normalized_value)

    return tuple(candidate_values)


def _education_level(
    terms: frozenset[str],
) -> str | None:
    for level in (
        "doctorate",
        "master",
        "bachelor",
        "diploma",
    ):
        if level in terms:
            return level

    return None


def _education_requirement_matches_candidate(
    *,
    candidate_value: str,
    requirement_value: str,
) -> bool:
    candidate_terms = normalized_term_set(
        candidate_value
    )
    requirement_terms = normalized_term_set(
        requirement_value
    )

    if not requirement_terms:
        return False

    candidate_level = _education_level(
        candidate_terms
    )
    requirement_level = _education_level(
        requirement_terms
    )

    if requirement_level is not None:
        if candidate_level is None:
            return False

        if (
            EDUCATION_LEVEL_RANK[candidate_level]
            < EDUCATION_LEVEL_RANK[requirement_level]
        ):
            return False

    non_level_requirement_terms = (
        requirement_terms
        - set(EDUCATION_LEVEL_RANK)
    )
    non_level_candidate_terms = (
        candidate_terms
        - set(EDUCATION_LEVEL_RANK)
    )

    return non_level_requirement_terms.issubset(
        non_level_candidate_terms
    )


def _normalize_education_requirements(
    values: Iterable[str],
) -> dict[str, str]:
    normalized_requirements: dict[str, str] = {}

    for value in values:
        normalized_value = normalize_education_text(
            value
        )

        if not normalized_value:
            continue

        normalized_requirements.setdefault(
            normalized_value,
            value.strip(),
        )

    return normalized_requirements


def _matched_education_requirements(
    *,
    candidate_values: tuple[str, ...],
    requirement_map: dict[str, str],
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    matched_requirements: list[str] = []
    missing_requirements: list[str] = []

    for normalized_requirement, original_requirement in (
        requirement_map.items()
    ):
        is_match = any(
            _education_requirement_matches_candidate(
                candidate_value=candidate_value,
                requirement_value=normalized_requirement,
            )
            for candidate_value in candidate_values
        )

        if is_match:
            matched_requirements.append(
                original_requirement
            )
        else:
            missing_requirements.append(
                original_requirement
            )

    return (
        tuple(matched_requirements),
        tuple(missing_requirements),
    )


def score_education_alignment(
    *,
    candidate_education: Iterable[ResumeEducationEntry],
    required_education: Iterable[str],
    preferred_education: Iterable[str],
    policy: MatchScoringPolicy = DEFAULT_SCORING_POLICY,
) -> EducationMatchResult:
    candidate_values = _build_candidate_education_values(
        candidate_education
    )

    required_requirement_map = (
        _normalize_education_requirements(
            required_education
        )
    )
    preferred_requirement_map = (
        _normalize_education_requirements(
            preferred_education
        )
    )

    for required_key in required_requirement_map:
        preferred_requirement_map.pop(
            required_key,
            None,
        )

    (
        matched_required,
        missing_required,
    ) = _matched_education_requirements(
        candidate_values=candidate_values,
        requirement_map=required_requirement_map,
    )

    (
        matched_preferred,
        missing_preferred,
    ) = _matched_education_requirements(
        candidate_values=candidate_values,
        requirement_map=preferred_requirement_map,
    )

    required_coverage = _calculate_coverage(
        len(matched_required),
        len(required_requirement_map),
    )
    preferred_coverage = _calculate_coverage(
        len(matched_preferred),
        len(preferred_requirement_map),
    )

    required_score = _coverage_to_score(
        required_coverage
    )
    preferred_score = _coverage_to_score(
        preferred_coverage
    )

    available_weight = 0.0
    weighted_score = 0.0

    if required_score is not None:
        available_weight += policy.required_skill_weight
        weighted_score += (
            required_score
            * policy.required_skill_weight
        )

    if preferred_score is not None:
        available_weight += policy.preferred_skill_weight
        weighted_score += (
            preferred_score
            * policy.preferred_skill_weight
        )

    if available_weight == 0.0:
        combined_score = 0.0
    else:
        combined_score = round(
            weighted_score / available_weight,
            2,
        )

    return EducationMatchResult(
        score=combined_score,
        required_score=required_score,
        preferred_score=preferred_score,
        required_coverage=required_coverage,
        preferred_coverage=preferred_coverage,
        candidate_education=candidate_values,
        matched_required_education=matched_required,
        missing_required_education=missing_required,
        matched_preferred_education=matched_preferred,
        missing_preferred_education=missing_preferred,
    )
@dataclass(frozen=True, slots=True)
class CertificationMatchResult:
    score: float
    required_score: float | None
    preferred_score: float | None
    required_coverage: float | None
    preferred_coverage: float | None
    candidate_certifications: tuple[str, ...]
    matched_required_certifications: tuple[str, ...]
    missing_required_certifications: tuple[str, ...]
    matched_preferred_certifications: tuple[str, ...]
    missing_preferred_certifications: tuple[str, ...]


def _build_candidate_certification_values(
    certification_entries: Iterable[ResumeCertificationEntry],
) -> tuple[str, ...]:
    candidate_values: list[str] = []
    seen_values: set[str] = set()

    for entry in certification_entries:
        parts = [
            value
            for value in (
                entry.name,
                entry.issuer,
            )
            if value
        ]

        if not parts:
            continue

        normalized_value = normalize_certification_text(
            " ".join(parts)
        )

        if (
            not normalized_value
            or normalized_value in seen_values
        ):
            continue

        seen_values.add(normalized_value)
        candidate_values.append(normalized_value)

    return tuple(candidate_values)


def _certification_requirement_matches_candidate(
    *,
    candidate_value: str,
    requirement_value: str,
) -> bool:
    candidate_terms = normalized_term_set(
        candidate_value
    )
    requirement_terms = normalized_term_set(
        requirement_value
    )

    if not requirement_terms:
        return False

    return requirement_terms.issubset(
        candidate_terms
    )


def _normalize_certification_requirements(
    values: Iterable[str],
) -> dict[str, str]:
    normalized_requirements: dict[str, str] = {}

    for value in values:
        normalized_value = normalize_certification_text(
            value
        )

        if not normalized_value:
            continue

        normalized_requirements.setdefault(
            normalized_value,
            value.strip(),
        )

    return normalized_requirements


def _matched_certification_requirements(
    *,
    candidate_values: tuple[str, ...],
    requirement_map: dict[str, str],
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    matched_requirements: list[str] = []
    missing_requirements: list[str] = []

    for normalized_requirement, original_requirement in (
        requirement_map.items()
    ):
        is_match = any(
            _certification_requirement_matches_candidate(
                candidate_value=candidate_value,
                requirement_value=normalized_requirement,
            )
            for candidate_value in candidate_values
        )

        if is_match:
            matched_requirements.append(
                original_requirement
            )
        else:
            missing_requirements.append(
                original_requirement
            )

    return (
        tuple(matched_requirements),
        tuple(missing_requirements),
    )


def score_certification_alignment(
    *,
    candidate_certifications: Iterable[
        ResumeCertificationEntry
    ],
    required_certifications: Iterable[str],
    preferred_certifications: Iterable[str],
    policy: MatchScoringPolicy = DEFAULT_SCORING_POLICY,
) -> CertificationMatchResult:
    candidate_values = (
        _build_candidate_certification_values(
            candidate_certifications
        )
    )

    required_requirement_map = (
        _normalize_certification_requirements(
            required_certifications
        )
    )
    preferred_requirement_map = (
        _normalize_certification_requirements(
            preferred_certifications
        )
    )

    for required_key in required_requirement_map:
        preferred_requirement_map.pop(
            required_key,
            None,
        )

    (
        matched_required,
        missing_required,
    ) = _matched_certification_requirements(
        candidate_values=candidate_values,
        requirement_map=required_requirement_map,
    )

    (
        matched_preferred,
        missing_preferred,
    ) = _matched_certification_requirements(
        candidate_values=candidate_values,
        requirement_map=preferred_requirement_map,
    )

    required_coverage = _calculate_coverage(
        len(matched_required),
        len(required_requirement_map),
    )
    preferred_coverage = _calculate_coverage(
        len(matched_preferred),
        len(preferred_requirement_map),
    )

    required_score = _coverage_to_score(
        required_coverage
    )
    preferred_score = _coverage_to_score(
        preferred_coverage
    )

    available_weight = 0.0
    weighted_score = 0.0

    if required_score is not None:
        available_weight += policy.required_skill_weight
        weighted_score += (
            required_score
            * policy.required_skill_weight
        )

    if preferred_score is not None:
        available_weight += policy.preferred_skill_weight
        weighted_score += (
            preferred_score
            * policy.preferred_skill_weight
        )

    if available_weight == 0.0:
        combined_score = 0.0
    else:
        combined_score = round(
            weighted_score / available_weight,
            2,
        )

    return CertificationMatchResult(
        score=combined_score,
        required_score=required_score,
        preferred_score=preferred_score,
        required_coverage=required_coverage,
        preferred_coverage=preferred_coverage,
        candidate_certifications=candidate_values,
        matched_required_certifications=matched_required,
        missing_required_certifications=missing_required,
        matched_preferred_certifications=matched_preferred,
        missing_preferred_certifications=missing_preferred,
    )

LocationAlignmentStatus = Literal[
    "job_location_not_specified",
    "candidate_location_missing",
    "matched",
    "mismatched",
]


@dataclass(frozen=True, slots=True)
class LocationMatchResult:
    score: float
    status: LocationAlignmentStatus
    candidate_location: str | None
    job_location: str | None
    normalized_candidate_location: str | None
    normalized_job_location: str | None
    is_match: bool | None


def score_location_alignment(
    *,
    candidate_location: str | None,
    job_location: str | None,
) -> LocationMatchResult:
    normalized_candidate_location = (
        normalize_location_text(candidate_location)
        if candidate_location
        else ""
    )
    normalized_job_location = (
        normalize_location_text(job_location)
        if job_location
        else ""
    )

    if not normalized_job_location:
        return LocationMatchResult(
            score=0.0,
            status="job_location_not_specified",
            candidate_location=candidate_location,
            job_location=job_location,
            normalized_candidate_location=(
                normalized_candidate_location or None
            ),
            normalized_job_location=None,
            is_match=None,
        )

    if not normalized_candidate_location:
        return LocationMatchResult(
            score=0.0,
            status="candidate_location_missing",
            candidate_location=candidate_location,
            job_location=job_location,
            normalized_candidate_location=None,
            normalized_job_location=normalized_job_location,
            is_match=None,
        )

    is_match = locations_match(
        candidate_location,
        job_location,
    )

    return LocationMatchResult(
        score=100.0 if is_match else 0.0,
        status="matched" if is_match else "mismatched",
        candidate_location=candidate_location,
        job_location=job_location,
        normalized_candidate_location=(
            normalized_candidate_location
        ),
        normalized_job_location=normalized_job_location,
        is_match=is_match,
    )


WorkModeAlignmentStatus = Literal[
    "job_work_mode_not_specified",
    "candidate_preference_missing",
    "matched",
    "mismatched",
]


@dataclass(frozen=True, slots=True)
class WorkModeMatchResult:
    score: float
    status: WorkModeAlignmentStatus
    candidate_work_mode: JobWorkMode | None
    job_work_mode: JobWorkMode | None
    is_match: bool | None


def score_work_mode_alignment(
    *,
    candidate_work_mode: JobWorkMode | None,
    job_work_mode: JobWorkMode | None,
) -> WorkModeMatchResult:
    if job_work_mode is None:
        return WorkModeMatchResult(
            score=0.0,
            status="job_work_mode_not_specified",
            candidate_work_mode=candidate_work_mode,
            job_work_mode=None,
            is_match=None,
        )

    if candidate_work_mode is None:
        return WorkModeMatchResult(
            score=0.0,
            status="candidate_preference_missing",
            candidate_work_mode=None,
            job_work_mode=job_work_mode,
            is_match=None,
        )

    is_match = candidate_work_mode == job_work_mode

    return WorkModeMatchResult(
        score=100.0 if is_match else 0.0,
        status="matched" if is_match else "mismatched",
        candidate_work_mode=candidate_work_mode,
        job_work_mode=job_work_mode,
        is_match=is_match,
    )
@dataclass(frozen=True, slots=True)
class OverallScoreResult:
    raw_score: float
    score: float
    available_weight: float
    required_skill_cap: float | None
    was_capped: bool


def required_skill_score_cap(
    *,
    required_skill_coverage: float | None,
    policy: MatchScoringPolicy = DEFAULT_SCORING_POLICY,
) -> float | None:
    if required_skill_coverage is None:
        return None

    if (
        required_skill_coverage < 0.0
        or required_skill_coverage > 1.0
    ):
        raise ValueError(
            "Required-skill coverage must be between "
            "0.0 and 1.0."
        )

    if required_skill_coverage == 0.0:
        return policy.zero_required_skill_match_cap

    if (
        required_skill_coverage
        < policy.low_required_skill_coverage_threshold
    ):
        return policy.low_required_skill_match_cap

    if (
        required_skill_coverage
        < policy.moderate_required_skill_coverage_threshold
    ):
        return policy.moderate_required_skill_match_cap

    return None


def calculate_overall_score(
    *,
    skill_score: float | None,
    experience_score: float | None,
    education_score: float | None,
    certification_score: float | None,
    location_score: float | None,
    work_mode_score: float | None,
    required_skill_coverage: float | None,
    policy: MatchScoringPolicy = DEFAULT_SCORING_POLICY,
) -> OverallScoreResult:
    weighted_components = (
        (
            skill_score,
            policy.skill_weight,
            "skill_score",
        ),
        (
            experience_score,
            policy.experience_weight,
            "experience_score",
        ),
        (
            education_score,
            policy.education_weight,
            "education_score",
        ),
        (
            certification_score,
            policy.certification_weight,
            "certification_score",
        ),
        (
            location_score,
            policy.location_weight,
            "location_score",
        ),
        (
            work_mode_score,
            policy.work_mode_weight,
            "work_mode_score",
        ),
    )

    available_weight = 0.0
    weighted_total = 0.0

    for score, weight, field_name in weighted_components:
        if score is None:
            continue

        if score < 0.0 or score > 100.0:
            raise ValueError(
                f"{field_name} must be between 0 and 100."
            )

        available_weight += weight
        weighted_total += score * weight

    if available_weight == 0.0:
        raw_score = 0.0
    else:
        raw_score = round(
            weighted_total / available_weight,
            2,
        )

    score_cap = required_skill_score_cap(
        required_skill_coverage=(
            required_skill_coverage
        ),
        policy=policy,
    )

    if score_cap is None:
        final_score = raw_score
    else:
        final_score = min(
            raw_score,
            score_cap,
        )

    final_score = round(
        final_score,
        2,
    )

    return OverallScoreResult(
        raw_score=raw_score,
        score=final_score,
        available_weight=round(
            available_weight,
            6,
        ),
        required_skill_cap=score_cap,
        was_capped=final_score < raw_score,
    )

MatchRecommendation = Literal[
    "strong_match",
    "good_match",
    "partial_match",
    "weak_match",
    "insufficient_data",
]


@dataclass(frozen=True, slots=True)
class RecommendationResult:
    recommendation: MatchRecommendation
    score: float
    confidence_score: float
    reason: str


def classify_match_recommendation(
    *,
    score: float,
    confidence_score: float,
    policy: MatchScoringPolicy = DEFAULT_SCORING_POLICY,
) -> RecommendationResult:
    if score < 0.0 or score > 100.0:
        raise ValueError(
            "Overall match score must be between 0 and 100."
        )

    if confidence_score < 0.0 or confidence_score > 100.0:
        raise ValueError(
            "Confidence score must be between 0 and 100."
        )

    if (
        confidence_score
        < policy.insufficient_data_confidence_threshold
    ):
        return RecommendationResult(
            recommendation="insufficient_data",
            score=score,
            confidence_score=confidence_score,
            reason=(
                "Available candidate and job information is "
                "insufficient for a reliable recommendation."
            ),
        )

    if score >= policy.strong_match_threshold:
        return RecommendationResult(
            recommendation="strong_match",
            score=score,
            confidence_score=confidence_score,
            reason=(
                "The candidate strongly satisfies the available "
                "job requirements."
            ),
        )

    if score >= policy.good_match_threshold:
        return RecommendationResult(
            recommendation="good_match",
            score=score,
            confidence_score=confidence_score,
            reason=(
                "The candidate satisfies most of the available "
                "job requirements."
            ),
        )

    if score >= policy.partial_match_threshold:
        return RecommendationResult(
            recommendation="partial_match",
            score=score,
            confidence_score=confidence_score,
            reason=(
                "The candidate satisfies some requirements but "
                "has meaningful gaps."
            ),
        )

    return RecommendationResult(
        recommendation="weak_match",
        score=score,
        confidence_score=confidence_score,
        reason=(
            "The candidate does not satisfy enough of the "
            "available job requirements."
        ),
    )
@dataclass(frozen=True, slots=True)
class MatchConfidenceResult:
    score: float
    parser_confidence_score: float
    data_coverage_score: float
    specified_weight: float
    assessable_weight: float
    missing_components: tuple[str, ...]
    unspecified_components: tuple[str, ...]


def calculate_match_confidence(
    *,
    resume_profile_confidence: float,
    job_requirement_profile_confidence: float,
    skill_data_available: bool | None,
    experience_data_available: bool | None,
    education_data_available: bool | None,
    certification_data_available: bool | None,
    location_data_available: bool | None,
    work_mode_data_available: bool | None,
    policy: MatchScoringPolicy = DEFAULT_SCORING_POLICY,
) -> MatchConfidenceResult:
    parser_confidences = (
        (
            "resume_profile_confidence",
            resume_profile_confidence,
        ),
        (
            "job_requirement_profile_confidence",
            job_requirement_profile_confidence,
        ),
    )

    for field_name, confidence in parser_confidences:
        if confidence < 0.0 or confidence > 1.0:
            raise ValueError(
                f"{field_name} must be between 0.0 and 1.0."
            )

    component_availability = (
        (
            "skills",
            skill_data_available,
            policy.skill_weight,
        ),
        (
            "experience",
            experience_data_available,
            policy.experience_weight,
        ),
        (
            "education",
            education_data_available,
            policy.education_weight,
        ),
        (
            "certifications",
            certification_data_available,
            policy.certification_weight,
        ),
        (
            "location",
            location_data_available,
            policy.location_weight,
        ),
        (
            "work_mode",
            work_mode_data_available,
            policy.work_mode_weight,
        ),
    )

    specified_weight = 0.0
    assessable_weight = 0.0
    missing_components: list[str] = []
    unspecified_components: list[str] = []

    for (
        component_name,
        data_available,
        component_weight,
    ) in component_availability:
        if data_available is None:
            unspecified_components.append(
                component_name
            )
            continue

        specified_weight += component_weight

        if data_available:
            assessable_weight += component_weight
        else:
            missing_components.append(
                component_name
            )

    parser_confidence_ratio = (
        resume_profile_confidence
        + job_requirement_profile_confidence
    ) / 2.0

    parser_confidence_score = round(
        parser_confidence_ratio * 100.0,
        2,
    )

    if specified_weight == 0.0:
        data_coverage_ratio = 0.0
    else:
        data_coverage_ratio = (
            assessable_weight / specified_weight
        )

    data_coverage_score = round(
        data_coverage_ratio * 100.0,
        2,
    )

    confidence_score = round(
        parser_confidence_score
        * data_coverage_ratio,
        2,
    )

    return MatchConfidenceResult(
        score=confidence_score,
        parser_confidence_score=(
            parser_confidence_score
        ),
        data_coverage_score=data_coverage_score,
        specified_weight=round(
            specified_weight,
            6,
        ),
        assessable_weight=round(
            assessable_weight,
            6,
        ),
        missing_components=tuple(
            missing_components
        ),
        unspecified_components=tuple(
            unspecified_components
        ),
    )
def _format_percentage(
    value: float | None,
) -> str:
    if value is None:
        return "not specified"

    return f"{round(value * 100.0, 2)}%"


def _build_experience_analysis(
    result: ExperienceMatchResult,
) -> str:
    if result.status == "requirement_not_specified":
        return (
            "The job does not specify an experience "
            "requirement."
        )

    if result.status == "candidate_experience_missing":
        return (
            "The job specifies an experience requirement, "
            "but candidate experience data is unavailable."
        )

    if result.status == "below_minimum":
        return (
            "Candidate experience is below the minimum "
            f"requirement by {result.gap_months} months."
        )

    if result.status == "above_maximum":
        return (
            "Candidate experience exceeds the stated maximum "
            f"by {result.gap_months} months."
        )

    if result.status == "within_range":
        return (
            "Candidate experience is within the job's "
            "specified experience range."
        )

    if result.status == "meets_minimum":
        return (
            "Candidate experience meets the job's minimum "
            "experience requirement."
        )

    return (
        "Candidate experience is within the job's maximum "
        "experience requirement."
    )


def _build_education_analysis(
    result: EducationMatchResult,
) -> str:
    if (
        result.required_coverage is None
        and result.preferred_coverage is None
    ):
        return (
            "The job does not specify education "
            "requirements."
        )

    if not result.candidate_education:
        return (
            "The job specifies education requirements, but "
            "candidate education data is unavailable."
        )

    return (
        "Required education coverage: "
        f"{_format_percentage(result.required_coverage)}. "
        "Preferred education coverage: "
        f"{_format_percentage(result.preferred_coverage)}."
    )


def _build_certification_analysis(
    result: CertificationMatchResult,
) -> str:
    if (
        result.required_coverage is None
        and result.preferred_coverage is None
    ):
        return (
            "The job does not specify certification "
            "requirements."
        )

    if not result.candidate_certifications:
        return (
            "The job specifies certification requirements, "
            "but candidate certification data is unavailable."
        )

    return (
        "Required certification coverage: "
        f"{_format_percentage(result.required_coverage)}. "
        "Preferred certification coverage: "
        f"{_format_percentage(result.preferred_coverage)}."
    )


def _build_location_analysis(
    result: LocationMatchResult,
) -> str:
    if result.status == "job_location_not_specified":
        return "The job does not specify a location."

    if result.status == "candidate_location_missing":
        return (
            "The job specifies a location, but candidate "
            "location data is unavailable."
        )

    if result.status == "matched":
        return (
            "Candidate location matches the job location."
        )

    return (
        "Candidate location does not match the job location."
    )


def _build_work_mode_analysis(
    result: WorkModeMatchResult,
) -> str:
    if result.status == "job_work_mode_not_specified":
        return "The job does not specify a work mode."

    if result.status == "candidate_preference_missing":
        return (
            "The job specifies a work mode, but candidate "
            "work-mode preference is unavailable."
        )

    if result.status == "matched":
        return (
            "Candidate work-mode preference matches the job "
            "work mode."
        )

    return (
        "Candidate work-mode preference does not match the "
        "job work mode."
    )


def _humanize_missing_component(
    component_name: str,
) -> str:
    messages = {
        "skills": "Candidate skill data is unavailable.",
        "experience": (
            "Candidate experience data is unavailable."
        ),
        "education": (
            "Candidate education data is unavailable."
        ),
        "certifications": (
            "Candidate certification data is unavailable."
        ),
        "location": (
            "Candidate location data is unavailable."
        ),
        "work_mode": (
            "Candidate work-mode preference is unavailable."
        ),
    }

    return messages.get(
        component_name,
        f"Candidate {component_name} data is unavailable.",
    )


def build_match_analysis_data(
    *,
    skill_result: SkillMatchResult,
    experience_result: ExperienceMatchResult,
    education_result: EducationMatchResult,
    certification_result: CertificationMatchResult,
    location_result: LocationMatchResult,
    work_mode_result: WorkModeMatchResult,
    overall_result: OverallScoreResult,
    confidence_result: MatchConfidenceResult,
) -> CandidateJobMatchAnalysisData:
    strengths: list[str] = []
    gaps: list[str] = []
    warnings: list[str] = []
    additional_alignment: list[str] = []

    if skill_result.required_coverage == 1.0:
        strengths.append(
            "Candidate matched all required skills."
        )

    if skill_result.preferred_coverage == 1.0:
        strengths.append(
            "Candidate matched all preferred skills."
        )

    if experience_result.status in {
        "within_range",
        "meets_minimum",
        "within_maximum",
    }:
        strengths.append(
            "Candidate experience satisfies the job "
            "requirement."
        )

    if education_result.required_coverage == 1.0:
        strengths.append(
            "Candidate matched all required education "
            "requirements."
        )

    if certification_result.required_coverage == 1.0:
        strengths.append(
            "Candidate matched all required certification "
            "requirements."
        )

    if location_result.status == "matched":
        strengths.append(
            "Candidate location matches the job location."
        )

    if work_mode_result.status == "matched":
        strengths.append(
            "Candidate work-mode preference matches the job."
        )

    if skill_result.missing_required_skills:
        gaps.append(
            "Missing required skills: "
            + ", ".join(
                skill_result.missing_required_skills
            )
            + "."
        )

    if experience_result.status == "below_minimum":
        gaps.append(
            "Candidate experience is "
            f"{experience_result.gap_months} months below "
            "the minimum requirement."
        )

    if experience_result.status == "above_maximum":
        gaps.append(
            "Candidate experience is "
            f"{experience_result.gap_months} months above "
            "the stated maximum."
        )

    if education_result.missing_required_education:
        gaps.append(
            "Missing required education: "
            + ", ".join(
                education_result.missing_required_education
            )
            + "."
        )

    if certification_result.missing_required_certifications:
        gaps.append(
            "Missing required certifications: "
            + ", ".join(
                certification_result
                .missing_required_certifications
            )
            + "."
        )

    if location_result.status == "mismatched":
        gaps.append(
            "Candidate location does not match the job "
            "location."
        )

    if work_mode_result.status == "mismatched":
        gaps.append(
            "Candidate work-mode preference does not match "
            "the job work mode."
        )

    if overall_result.was_capped:
        warnings.append(
            "Overall score was capped at "
            f"{overall_result.required_skill_cap} because "
            "required-skill coverage was insufficient."
        )

    if confidence_result.score < 40.0:
        warnings.append(
            "Match confidence is below the reliable "
            "recommendation threshold."
        )

    missing_data = [
        _humanize_missing_component(component_name)
        for component_name in (
            confidence_result.missing_components
        )
    ]

    additional_alignment.extend(
        [
            (
                "Overall score before required-skill caps: "
                f"{overall_result.raw_score}."
            ),
            (
                "Parser confidence score: "
                f"{confidence_result.parser_confidence_score}."
            ),
            (
                "Assessable data coverage: "
                f"{confidence_result.data_coverage_score}%."
            ),
        ]
    )

    return CandidateJobMatchAnalysisData(
        matched_required_skills=list(
            skill_result.matched_required_skills
        ),
        missing_required_skills=list(
            skill_result.missing_required_skills
        ),
        matched_preferred_skills=list(
            skill_result.matched_preferred_skills
        ),
        missing_preferred_skills=list(
            skill_result.missing_preferred_skills
        ),
        experience_analysis=_build_experience_analysis(
            experience_result
        ),
        matched_required_education=list(
            education_result.matched_required_education
        ),
        missing_required_education=list(
            education_result.missing_required_education
        ),
        matched_preferred_education=list(
            education_result.matched_preferred_education
        ),
        missing_preferred_education=list(
            education_result.missing_preferred_education
        ),
        education_analysis=_build_education_analysis(
            education_result
        ),
        matched_required_certifications=list(
            certification_result
            .matched_required_certifications
        ),
        missing_required_certifications=list(
            certification_result
            .missing_required_certifications
        ),
        matched_preferred_certifications=list(
            certification_result
            .matched_preferred_certifications
        ),
        missing_preferred_certifications=list(
            certification_result
            .missing_preferred_certifications
        ),
        certification_analysis=(
            _build_certification_analysis(
                certification_result
            )
        ),
        location_analysis=_build_location_analysis(
            location_result
        ),
        work_mode_analysis=_build_work_mode_analysis(
            work_mode_result
        ),
        additional_alignment=additional_alignment,
        strengths=strengths,
        gaps=gaps,
        warnings=warnings,
        missing_data=missing_data,
    )

@dataclass(frozen=True, slots=True)
class CandidateJobMatchComputation:
    skill_result: SkillMatchResult
    experience_result: ExperienceMatchResult
    education_result: EducationMatchResult
    certification_result: CertificationMatchResult
    location_result: LocationMatchResult
    work_mode_result: WorkModeMatchResult
    overall_result: OverallScoreResult
    confidence_result: MatchConfidenceResult
    recommendation_result: RecommendationResult
    analysis_data: CandidateJobMatchAnalysisData


def _component_availability(
    *,
    job_requirement_specified: bool,
    candidate_data_available: bool,
) -> bool | None:
    if not job_requirement_specified:
        return None

    return candidate_data_available


def _component_score_for_overall(
    *,
    job_requirement_specified: bool,
    component_score: float,
) -> float | None:
    if not job_requirement_specified:
        return None

    return component_score


def match_candidate_profile_to_job_requirements(
    *,
    resume_profile: ResumeProfileData,
    job_requirement_profile: JobRequirementProfileData,
    candidate_work_mode: JobWorkMode | None = None,
    policy: MatchScoringPolicy = DEFAULT_SCORING_POLICY,
) -> CandidateJobMatchComputation:
    skill_result = score_skill_alignment(
        candidate_skills=resume_profile.skills,
        required_skills=(
            job_requirement_profile.required_skills
        ),
        preferred_skills=(
            job_requirement_profile.preferred_skills
        ),
        policy=policy,
    )

    experience_result = score_experience_alignment(
        candidate_experience_months=(
            resume_profile.total_experience_months
        ),
        minimum_experience_years=(
            job_requirement_profile
            .minimum_experience_years
        ),
        maximum_experience_years=(
            job_requirement_profile
            .maximum_experience_years
        ),
    )

    education_result = score_education_alignment(
        candidate_education=resume_profile.education,
        required_education=(
            job_requirement_profile.required_education
        ),
        preferred_education=(
            job_requirement_profile.preferred_education
        ),
        policy=policy,
    )

    certification_result = (
        score_certification_alignment(
            candidate_certifications=(
                resume_profile.certifications
            ),
            required_certifications=(
                job_requirement_profile
                .required_certifications
            ),
            preferred_certifications=(
                job_requirement_profile
                .preferred_certifications
            ),
            policy=policy,
        )
    )

    location_result = score_location_alignment(
        candidate_location=resume_profile.location,
        job_location=job_requirement_profile.location,
    )

    work_mode_result = score_work_mode_alignment(
        candidate_work_mode=candidate_work_mode,
        job_work_mode=job_requirement_profile.work_mode,
    )

    skills_specified = bool(
        job_requirement_profile.required_skills
        or job_requirement_profile.preferred_skills
    )
    experience_specified = (
        job_requirement_profile.minimum_experience_years
        is not None
        or job_requirement_profile.maximum_experience_years
        is not None
    )
    education_specified = bool(
        job_requirement_profile.required_education
        or job_requirement_profile.preferred_education
    )
    certifications_specified = bool(
        job_requirement_profile.required_certifications
        or job_requirement_profile.preferred_certifications
    )
    location_specified = bool(
        normalize_location_text(
            job_requirement_profile.location or ""
        )
    )
    work_mode_specified = (
        job_requirement_profile.work_mode is not None
    )

    skill_data_available = _component_availability(
        job_requirement_specified=skills_specified,
        candidate_data_available=bool(
            normalize_skill_list(resume_profile.skills)
        ),
    )
    experience_data_available = _component_availability(
        job_requirement_specified=experience_specified,
        candidate_data_available=(
            resume_profile.total_experience_months
            is not None
        ),
    )
    education_data_available = _component_availability(
        job_requirement_specified=education_specified,
        candidate_data_available=bool(
            education_result.candidate_education
        ),
    )
    certification_data_available = _component_availability(
        job_requirement_specified=certifications_specified,
        candidate_data_available=bool(
            certification_result.candidate_certifications
        ),
    )
    location_data_available = _component_availability(
        job_requirement_specified=location_specified,
        candidate_data_available=bool(
            normalize_location_text(
                resume_profile.location or ""
            )
        ),
    )
    work_mode_data_available = _component_availability(
        job_requirement_specified=work_mode_specified,
        candidate_data_available=(
            candidate_work_mode is not None
        ),
    )

    overall_result = calculate_overall_score(
        skill_score=_component_score_for_overall(
            job_requirement_specified=skills_specified,
            component_score=skill_result.score,
        ),
        experience_score=_component_score_for_overall(
            job_requirement_specified=experience_specified,
            component_score=experience_result.score,
        ),
        education_score=_component_score_for_overall(
            job_requirement_specified=education_specified,
            component_score=education_result.score,
        ),
        certification_score=_component_score_for_overall(
            job_requirement_specified=(
                certifications_specified
            ),
            component_score=certification_result.score,
        ),
        location_score=_component_score_for_overall(
            job_requirement_specified=location_specified,
            component_score=location_result.score,
        ),
        work_mode_score=_component_score_for_overall(
            job_requirement_specified=work_mode_specified,
            component_score=work_mode_result.score,
        ),
        required_skill_coverage=(
            skill_result.required_coverage
        ),
        policy=policy,
    )

    confidence_result = calculate_match_confidence(
        resume_profile_confidence=(
            resume_profile.confidence
        ),
        job_requirement_profile_confidence=(
            job_requirement_profile.confidence
        ),
        skill_data_available=skill_data_available,
        experience_data_available=(
            experience_data_available
        ),
        education_data_available=(
            education_data_available
        ),
        certification_data_available=(
            certification_data_available
        ),
        location_data_available=(
            location_data_available
        ),
        work_mode_data_available=(
            work_mode_data_available
        ),
        policy=policy,
    )

    recommendation_result = (
        classify_match_recommendation(
            score=overall_result.score,
            confidence_score=confidence_result.score,
            policy=policy,
        )
    )

    analysis_data = build_match_analysis_data(
        skill_result=skill_result,
        experience_result=experience_result,
        education_result=education_result,
        certification_result=certification_result,
        location_result=location_result,
        work_mode_result=work_mode_result,
        overall_result=overall_result,
        confidence_result=confidence_result,
    )

    return CandidateJobMatchComputation(
        skill_result=skill_result,
        experience_result=experience_result,
        education_result=education_result,
        certification_result=certification_result,
        location_result=location_result,
        work_mode_result=work_mode_result,
        overall_result=overall_result,
        confidence_result=confidence_result,
        recommendation_result=recommendation_result,
        analysis_data=analysis_data,
    )
def build_candidate_job_match_create(
    *,
    candidate_id: UUID,
    job_id: UUID,
    resume_profile: ResumeProfileResponse,
    job_requirement_profile: JobRequirementProfileResponse,
    computation: CandidateJobMatchComputation,
    matched_at: datetime,
) -> CandidateJobMatchCreate:
    if resume_profile.parsing_status != "completed":
        raise ValueError(
            "Resume profile must have completed parsing."
        )

    if resume_profile.profile_data is None:
        raise ValueError(
            "Completed resume profile must contain profile data."
        )

    if resume_profile.parser_version is None:
        raise ValueError(
            "Completed resume profile must contain a parser version."
        )

    if resume_profile.source_text_sha256 is None:
        raise ValueError(
            "Completed resume profile must contain a source-text hash."
        )

    if job_requirement_profile.parsing_status != "completed":
        raise ValueError(
            "Job requirement profile must have completed parsing."
        )

    if job_requirement_profile.profile_data is None:
        raise ValueError(
            "Completed job requirement profile must contain "
            "profile data."
        )

    if job_requirement_profile.parser_version is None:
        raise ValueError(
            "Completed job requirement profile must contain "
            "a parser version."
        )

    if (
        job_requirement_profile.source_description_sha256
        is None
    ):
        raise ValueError(
            "Completed job requirement profile must contain "
            "a source-description hash."
        )

    if job_id != job_requirement_profile.job_id:
        raise ValueError(
            "job_id must match the job requirement profile."
        )

    if (
        matched_at.tzinfo is None
        or matched_at.utcoffset() is None
    ):
        raise ValueError(
            "matched_at must be timezone-aware."
        )

    return CandidateJobMatchCreate(
        candidate_id=candidate_id,
        job_id=job_id,
        resume_id=resume_profile.resume_id,
        resume_profile_id=resume_profile.id,
        job_requirement_profile_id=(
            job_requirement_profile.id
        ),
        overall_score=computation.overall_result.score,
        skill_score=computation.skill_result.score,
        experience_score=computation.experience_result.score,
        education_score=computation.education_result.score,
        certification_score=(
            computation.certification_result.score
        ),
        location_score=computation.location_result.score,
        work_mode_score=computation.work_mode_result.score,
        confidence_score=computation.confidence_result.score,
        recommendation=(
            computation
            .recommendation_result
            .recommendation
        ),
        analysis_data=computation.analysis_data,
        scoring_version=SCORING_VERSION,
        source_resume_text_sha256=(
            resume_profile.source_text_sha256
        ),
        source_resume_parser_version=(
            resume_profile.parser_version
        ),
        source_job_description_sha256=(
            job_requirement_profile
            .source_description_sha256
        ),
        source_job_parser_version=(
            job_requirement_profile.parser_version
        ),
        matched_at=matched_at,
    )