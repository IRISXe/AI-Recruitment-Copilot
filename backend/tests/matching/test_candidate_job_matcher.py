from dataclasses import replace
from datetime import datetime, timezone
from uuid import UUID

import pytest

from app.matching.candidate_job_matcher import (
    DEFAULT_SCORING_POLICY,
    SCORING_VERSION,
    CandidateJobMatchComputation,
    CertificationMatchResult,
    EducationMatchResult,
    ExperienceMatchResult,
    LocationMatchResult,
    MatchConfidenceResult,
    MatchScoringPolicy,
    OverallScoreResult,
    SkillMatchResult,
    WorkModeMatchResult,
    build_candidate_job_match_create,
    build_match_analysis_data,
    calculate_match_confidence,
    calculate_overall_score,
    classify_match_recommendation,
    match_candidate_profile_to_job_requirements,
    required_skill_score_cap,
    score_certification_alignment,
    score_education_alignment,
    score_experience_alignment,
    score_location_alignment,
    score_skill_alignment,
    score_work_mode_alignment,
)
from app.schemas.job_requirement_profile import (
    JobRequirementProfileData,
    JobRequirementProfileResponse,
)
from app.schemas.resume_profile import (
    ResumeCertificationEntry,
    ResumeEducationEntry,
    ResumeProfileData,
    ResumeProfileResponse,
)

def test_default_scoring_policy_has_expected_version() -> None:
    assert SCORING_VERSION == "candidate-job-rule-based-v1"


def test_default_overall_weights_add_up_to_one() -> None:
    policy = DEFAULT_SCORING_POLICY

    total = (
        policy.skill_weight
        + policy.experience_weight
        + policy.education_weight
        + policy.certification_weight
        + policy.location_weight
        + policy.work_mode_weight
    )

    assert total == pytest.approx(1.0)


def test_default_skill_weights_add_up_to_one() -> None:
    policy = DEFAULT_SCORING_POLICY

    total = (
        policy.required_skill_weight
        + policy.preferred_skill_weight
    )

    assert total == pytest.approx(1.0)


def test_default_policy_prioritizes_required_skills() -> None:
    policy = DEFAULT_SCORING_POLICY

    assert (
        policy.required_skill_weight
        > policy.preferred_skill_weight
    )


def test_default_required_skill_caps_are_ascending() -> None:
    policy = DEFAULT_SCORING_POLICY

    assert (
        policy.zero_required_skill_match_cap
        < policy.low_required_skill_match_cap
        < policy.moderate_required_skill_match_cap
    )


def test_default_coverage_thresholds_are_ascending() -> None:
    policy = DEFAULT_SCORING_POLICY

    assert (
        policy.low_required_skill_coverage_threshold
        < policy.moderate_required_skill_coverage_threshold
    )


def test_default_recommendation_thresholds_are_descending() -> None:
    policy = DEFAULT_SCORING_POLICY

    assert (
        policy.strong_match_threshold
        > policy.good_match_threshold
        > policy.partial_match_threshold
    )


def test_policy_rejects_invalid_overall_weight_total() -> None:
    with pytest.raises(
        ValueError,
        match="Overall scoring weights must add up to 1.0",
    ):
        MatchScoringPolicy(
            skill_weight=0.60,
        )


def test_policy_rejects_invalid_skill_weight_total() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "Required and preferred skill weights must "
            "add up to 1.0"
        ),
    ):
        MatchScoringPolicy(
            required_skill_weight=0.90,
        )


@pytest.mark.parametrize(
    ("field_name", "invalid_value"),
    [
        ("skill_weight", -0.01),
        ("required_skill_weight", 1.01),
        (
            "low_required_skill_coverage_threshold",
            -0.01,
        ),
        (
            "moderate_required_skill_coverage_threshold",
            1.01,
        ),
    ],
)
def test_policy_rejects_out_of_range_weights(
    field_name: str,
    invalid_value: float,
) -> None:
    values: dict[str, float] = {
        field_name: invalid_value,
    }

    if field_name == "skill_weight":
        values["experience_weight"] = 0.71

    if field_name == "required_skill_weight":
        values["preferred_skill_weight"] = -0.01

    with pytest.raises(ValueError):
        MatchScoringPolicy(**values)


@pytest.mark.parametrize(
    ("field_name", "invalid_value"),
    [
        ("zero_required_skill_match_cap", -0.01),
        ("low_required_skill_match_cap", 100.01),
        ("moderate_required_skill_match_cap", 101.0),
        ("strong_match_threshold", 101.0),
        ("good_match_threshold", -1.0),
        ("partial_match_threshold", 100.01),
        (
            "insufficient_data_confidence_threshold",
            -0.01,
        ),
    ],
)
def test_policy_rejects_out_of_range_scores(
    field_name: str,
    invalid_value: float,
) -> None:
    with pytest.raises(
        ValueError,
        match=(
            "Score caps and recommendation thresholds "
            "must be between 0 and 100"
        ),
    ):
        MatchScoringPolicy(
            **{
                field_name: invalid_value,
            }
        )


def test_policy_rejects_invalid_coverage_threshold_order() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "Required-skill coverage thresholds must be "
            "in ascending order"
        ),
    ):
        MatchScoringPolicy(
            low_required_skill_coverage_threshold=0.80,
            moderate_required_skill_coverage_threshold=0.70,
        )


def test_policy_rejects_invalid_cap_order() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "Required-skill score caps must be in "
            "ascending order"
        ),
    ):
        MatchScoringPolicy(
            zero_required_skill_match_cap=50.0,
            low_required_skill_match_cap=49.0,
        )


def test_policy_rejects_invalid_recommendation_threshold_order() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "Recommendation thresholds must be in "
            "descending order"
        ),
    ):
        MatchScoringPolicy(
            strong_match_threshold=70.0,
            good_match_threshold=85.0,
        )


def test_skill_alignment_returns_perfect_match() -> None:
    result = score_skill_alignment(
        candidate_skills=[
            "Python",
            "FastAPI",
            "PostgreSQL",
            "Docker",
        ],
        required_skills=[
            "Python",
            "FastAPI",
        ],
        preferred_skills=[
            "PostgreSQL",
            "Docker",
        ],
    )

    assert result.score == 100.0
    assert result.required_score == 100.0
    assert result.preferred_score == 100.0
    assert result.required_coverage == 1.0
    assert result.preferred_coverage == 1.0

    assert result.matched_required_skills == (
        "Python",
        "FastAPI",
    )
    assert result.missing_required_skills == ()

    assert result.matched_preferred_skills == (
        "PostgreSQL",
        "Docker",
    )
    assert result.missing_preferred_skills == ()


def test_skill_alignment_matches_canonical_aliases() -> None:
    result = score_skill_alignment(
        candidate_skills=[
            "React.js",
            "Postgres",
            "Amazon Web Services",
        ],
        required_skills=[
            "React",
            "PostgreSQL",
        ],
        preferred_skills=[
            "AWS",
        ],
    )

    assert result.score == 100.0

    assert result.matched_required_skills == (
        "React",
        "PostgreSQL",
    )
    assert result.matched_preferred_skills == (
        "AWS",
    )


def test_skill_alignment_penalizes_missing_required_skills() -> None:
    result = score_skill_alignment(
        candidate_skills=[
            "Python",
        ],
        required_skills=[
            "Python",
            "FastAPI",
            "PostgreSQL",
            "Docker",
        ],
        preferred_skills=[],
    )

    assert result.score == 25.0
    assert result.required_score == 25.0
    assert result.required_coverage == 0.25
    assert result.preferred_score is None
    assert result.preferred_coverage is None

    assert result.matched_required_skills == (
        "Python",
    )
    assert result.missing_required_skills == (
        "FastAPI",
        "PostgreSQL",
        "Docker",
    )


def test_skill_alignment_weights_required_skills_more_heavily() -> None:
    result = score_skill_alignment(
        candidate_skills=[
            "Python",
            "Docker",
        ],
        required_skills=[
            "Python",
            "FastAPI",
        ],
        preferred_skills=[
            "Docker",
            "AWS",
        ],
    )

    assert result.required_score == 50.0
    assert result.preferred_score == 50.0
    assert result.score == 50.0


def test_skill_alignment_handles_preferred_skills_only() -> None:
    result = score_skill_alignment(
        candidate_skills=[
            "AWS",
        ],
        required_skills=[],
        preferred_skills=[
            "AWS",
            "Docker",
        ],
    )

    assert result.score == 50.0
    assert result.required_score is None
    assert result.required_coverage is None
    assert result.preferred_score == 50.0
    assert result.preferred_coverage == 0.5

    assert result.matched_preferred_skills == (
        "AWS",
    )
    assert result.missing_preferred_skills == (
        "Docker",
    )


def test_skill_alignment_returns_unknown_when_job_has_no_skills() -> None:
    result = score_skill_alignment(
        candidate_skills=[
            "Python",
            "FastAPI",
        ],
        required_skills=[],
        preferred_skills=[],
    )

    assert result.score == 0.0
    assert result.required_score is None
    assert result.preferred_score is None
    assert result.required_coverage is None
    assert result.preferred_coverage is None
    assert result.matched_required_skills == ()
    assert result.missing_required_skills == ()
    assert result.matched_preferred_skills == ()
    assert result.missing_preferred_skills == ()


def test_skill_alignment_removes_required_skills_from_preferred() -> None:
    result = score_skill_alignment(
        candidate_skills=[
            "Python",
        ],
        required_skills=[
            "Python",
        ],
        preferred_skills=[
            "Python",
            "Docker",
        ],
    )

    assert result.required_score == 100.0
    assert result.preferred_score == 0.0

    assert result.matched_required_skills == (
        "Python",
    )
    assert result.matched_preferred_skills == ()
    assert result.missing_preferred_skills == (
        "Docker",
    )


def test_skill_alignment_normalizes_duplicate_inputs() -> None:
    result = score_skill_alignment(
        candidate_skills=[
            "React",
            "React.js",
            "ReactJS",
        ],
        required_skills=[
            "ReactJS",
            "React",
        ],
        preferred_skills=[],
    )

    assert result.score == 100.0
    assert result.required_score == 100.0
    assert result.matched_required_skills == (
        "React",
    )
    assert result.missing_required_skills == ()


def test_skill_alignment_output_is_deterministic() -> None:
    arguments = {
        "candidate_skills": [
            "Postgres",
            "React.js",
            "AWS",
        ],
        "required_skills": [
            "React",
            "PostgreSQL",
            "Docker",
        ],
        "preferred_skills": [
            "Amazon Web Services",
            "Kubernetes",
        ],
    }

    first_result = score_skill_alignment(**arguments)
    second_result = score_skill_alignment(**arguments)

    assert first_result == second_result

def test_experience_alignment_meets_minimum() -> None:
    result = score_experience_alignment(
        candidate_experience_months=48,
        minimum_experience_years=3,
        maximum_experience_years=None,
    )

    assert result.score == 100.0
    assert result.status == "meets_minimum"
    assert result.candidate_experience_months == 48
    assert result.minimum_experience_months == 36
    assert result.maximum_experience_months is None
    assert result.gap_months == 0
    assert result.meets_minimum is True
    assert result.within_maximum is True


def test_experience_alignment_is_within_range() -> None:
    result = score_experience_alignment(
        candidate_experience_months=48,
        minimum_experience_years=3,
        maximum_experience_years=5,
    )

    assert result.score == 100.0
    assert result.status == "within_range"
    assert result.minimum_experience_months == 36
    assert result.maximum_experience_months == 60
    assert result.gap_months == 0
    assert result.meets_minimum is True
    assert result.within_maximum is True


def test_experience_alignment_scores_candidate_below_minimum() -> None:
    result = score_experience_alignment(
        candidate_experience_months=30,
        minimum_experience_years=3,
        maximum_experience_years=5,
    )

    assert result.score == 83.33
    assert result.status == "below_minimum"
    assert result.gap_months == 6
    assert result.meets_minimum is False
    assert result.within_maximum is True


def test_experience_alignment_scores_candidate_above_maximum() -> None:
    result = score_experience_alignment(
        candidate_experience_months=72,
        minimum_experience_years=2,
        maximum_experience_years=4,
    )

    assert result.score == 66.67
    assert result.status == "above_maximum"
    assert result.minimum_experience_months == 24
    assert result.maximum_experience_months == 48
    assert result.gap_months == 24
    assert result.meets_minimum is True
    assert result.within_maximum is False


def test_experience_alignment_supports_maximum_only() -> None:
    result = score_experience_alignment(
        candidate_experience_months=24,
        minimum_experience_years=None,
        maximum_experience_years=3,
    )

    assert result.score == 100.0
    assert result.status == "within_maximum"
    assert result.minimum_experience_months is None
    assert result.maximum_experience_months == 36
    assert result.gap_months == 0
    assert result.meets_minimum is True
    assert result.within_maximum is True


def test_experience_alignment_handles_missing_candidate_experience() -> None:
    result = score_experience_alignment(
        candidate_experience_months=None,
        minimum_experience_years=2,
        maximum_experience_years=5,
    )

    assert result.score == 0.0
    assert result.status == "candidate_experience_missing"
    assert result.candidate_experience_months is None
    assert result.minimum_experience_months == 24
    assert result.maximum_experience_months == 60
    assert result.gap_months is None
    assert result.meets_minimum is None
    assert result.within_maximum is None


def test_experience_alignment_handles_missing_job_requirement() -> None:
    result = score_experience_alignment(
        candidate_experience_months=36,
        minimum_experience_years=None,
        maximum_experience_years=None,
    )

    assert result.score == 0.0
    assert result.status == "requirement_not_specified"
    assert result.candidate_experience_months == 36
    assert result.minimum_experience_months is None
    assert result.maximum_experience_months is None
    assert result.gap_months is None
    assert result.meets_minimum is None
    assert result.within_maximum is None


def test_experience_alignment_accepts_zero_minimum() -> None:
    result = score_experience_alignment(
        candidate_experience_months=0,
        minimum_experience_years=0,
        maximum_experience_years=None,
    )

    assert result.score == 100.0
    assert result.status == "meets_minimum"
    assert result.gap_months == 0
    assert result.meets_minimum is True


@pytest.mark.parametrize(
    "candidate_experience_months",
    [
        -1,
        -12,
    ],
)
def test_experience_alignment_rejects_negative_candidate_experience(
    candidate_experience_months: int,
) -> None:
    with pytest.raises(
        ValueError,
        match="Candidate experience must not be negative",
    ):
        score_experience_alignment(
            candidate_experience_months=(
                candidate_experience_months
            ),
            minimum_experience_years=1,
            maximum_experience_years=None,
        )


@pytest.mark.parametrize(
    ("minimum_experience_years", "maximum_experience_years"),
    [
        (-1, None),
        (None, -1),
    ],
)
def test_experience_alignment_rejects_negative_requirements(
    minimum_experience_years: int | None,
    maximum_experience_years: int | None,
) -> None:
    with pytest.raises(
        ValueError,
        match="Experience requirements must not be negative",
    ):
        score_experience_alignment(
            candidate_experience_months=24,
            minimum_experience_years=minimum_experience_years,
            maximum_experience_years=maximum_experience_years,
        )


def test_experience_alignment_rejects_invalid_range() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "Maximum experience must not be lower than "
            "minimum experience"
        ),
    ):
        score_experience_alignment(
            candidate_experience_months=36,
            minimum_experience_years=5,
            maximum_experience_years=3,
        )


def test_experience_alignment_output_is_deterministic() -> None:
    arguments = {
        "candidate_experience_months": 30,
        "minimum_experience_years": 3,
        "maximum_experience_years": 5,
    }

    first_result = score_experience_alignment(**arguments)
    second_result = score_experience_alignment(**arguments)

    assert first_result == second_result

def test_education_alignment_matches_equivalent_bachelor_degree() -> None:
    result = score_education_alignment(
        candidate_education=[
            ResumeEducationEntry(
                institution="JNTU Hyderabad",
                degree="Bachelor of Technology",
                field_of_study="Computer Science",
            )
        ],
        required_education=[
            "Bachelor's degree in Computer Science",
        ],
        preferred_education=[],
    )

    assert result.score == 100.0
    assert result.required_score == 100.0
    assert result.preferred_score is None
    assert result.required_coverage == 1.0
    assert result.preferred_coverage is None

    assert result.candidate_education == (
        "bachelor computer science",
    )
    assert result.matched_required_education == (
        "Bachelor's degree in Computer Science",
    )
    assert result.missing_required_education == ()


def test_education_alignment_accepts_higher_degree_level() -> None:
    result = score_education_alignment(
        candidate_education=[
            ResumeEducationEntry(
                degree="Master of Science",
                field_of_study="Computer Science",
            )
        ],
        required_education=[
            "Bachelor's degree in Computer Science",
        ],
        preferred_education=[],
    )

    assert result.score == 100.0
    assert result.required_score == 100.0
    assert result.matched_required_education == (
        "Bachelor's degree in Computer Science",
    )


def test_education_alignment_rejects_lower_degree_level() -> None:
    result = score_education_alignment(
        candidate_education=[
            ResumeEducationEntry(
                degree="Diploma",
                field_of_study="Computer Science",
            )
        ],
        required_education=[
            "Bachelor's degree in Computer Science",
        ],
        preferred_education=[],
    )

    assert result.score == 0.0
    assert result.required_score == 0.0
    assert result.required_coverage == 0.0
    assert result.matched_required_education == ()
    assert result.missing_required_education == (
        "Bachelor's degree in Computer Science",
    )


def test_education_alignment_rejects_different_field_of_study() -> None:
    result = score_education_alignment(
        candidate_education=[
            ResumeEducationEntry(
                degree="Bachelor of Technology",
                field_of_study="Mechanical Engineering",
            )
        ],
        required_education=[
            "Bachelor's degree in Computer Science",
        ],
        preferred_education=[],
    )

    assert result.score == 0.0
    assert result.matched_required_education == ()
    assert result.missing_required_education == (
        "Bachelor's degree in Computer Science",
    )


def test_education_alignment_scores_required_and_preferred_separately(
) -> None:
    result = score_education_alignment(
        candidate_education=[
            ResumeEducationEntry(
                degree="Bachelor of Technology",
                field_of_study="Computer Science",
            )
        ],
        required_education=[
            "Bachelor's degree in Computer Science",
        ],
        preferred_education=[
            "Master's degree in Computer Science",
        ],
    )

    assert result.score == 80.0
    assert result.required_score == 100.0
    assert result.preferred_score == 0.0
    assert result.required_coverage == 1.0
    assert result.preferred_coverage == 0.0

    assert result.matched_required_education == (
        "Bachelor's degree in Computer Science",
    )
    assert result.missing_preferred_education == (
        "Master's degree in Computer Science",
    )


def test_education_alignment_supports_multiple_candidate_entries() -> None:
    result = score_education_alignment(
        candidate_education=[
            ResumeEducationEntry(
                degree="Diploma",
                field_of_study="Information Technology",
            ),
            ResumeEducationEntry(
                degree="Bachelor of Engineering",
                field_of_study="Computer Engineering",
            ),
        ],
        required_education=[
            "Bachelor's degree in Computer Science",
        ],
        preferred_education=[
            "Diploma in Information Technology",
        ],
    )

    assert result.score == 100.0
    assert result.required_score == 100.0
    assert result.preferred_score == 100.0

    assert result.matched_required_education == (
        "Bachelor's degree in Computer Science",
    )
    assert result.matched_preferred_education == (
        "Diploma in Information Technology",
    )


def test_education_alignment_handles_missing_candidate_education(
) -> None:
    result = score_education_alignment(
        candidate_education=[],
        required_education=[
            "Bachelor's degree in Computer Science",
        ],
        preferred_education=[],
    )

    assert result.score == 0.0
    assert result.required_score == 0.0
    assert result.required_coverage == 0.0
    assert result.candidate_education == ()
    assert result.missing_required_education == (
        "Bachelor's degree in Computer Science",
    )


def test_education_alignment_handles_missing_job_requirements() -> None:
    result = score_education_alignment(
        candidate_education=[
            ResumeEducationEntry(
                degree="Bachelor of Technology",
                field_of_study="Computer Science",
            )
        ],
        required_education=[],
        preferred_education=[],
    )

    assert result.score == 0.0
    assert result.required_score is None
    assert result.preferred_score is None
    assert result.required_coverage is None
    assert result.preferred_coverage is None
    assert result.matched_required_education == ()
    assert result.missing_required_education == ()


def test_education_alignment_removes_required_from_preferred() -> None:
    requirement = "Bachelor's degree in Computer Science"

    result = score_education_alignment(
        candidate_education=[
            ResumeEducationEntry(
                degree="Bachelor of Technology",
                field_of_study="Computer Science",
            )
        ],
        required_education=[
            requirement,
        ],
        preferred_education=[
            requirement,
        ],
    )

    assert result.score == 100.0
    assert result.required_score == 100.0
    assert result.preferred_score is None
    assert result.matched_required_education == (
        requirement,
    )
    assert result.matched_preferred_education == ()


def test_education_alignment_ignores_empty_candidate_entries() -> None:
    result = score_education_alignment(
        candidate_education=[
            ResumeEducationEntry(
                institution="Unknown University",
            ),
            ResumeEducationEntry(
                degree="Bachelor of Technology",
                field_of_study="Computer Science",
            ),
        ],
        required_education=[
            "Bachelor's degree in Computer Science",
        ],
        preferred_education=[],
    )

    assert result.candidate_education == (
        "bachelor computer science",
    )
    assert result.score == 100.0


def test_education_alignment_deduplicates_candidate_entries() -> None:
    result = score_education_alignment(
        candidate_education=[
            ResumeEducationEntry(
                degree="Bachelor of Technology",
                field_of_study="Computer Science",
            ),
            ResumeEducationEntry(
                degree="Bachelor's Degree",
                field_of_study="Computer Science",
            ),
        ],
        required_education=[
            "Bachelor's degree in Computer Science",
        ],
        preferred_education=[],
    )

    assert result.candidate_education == (
        "bachelor computer science",
    )
    assert result.score == 100.0


def test_education_alignment_output_is_deterministic() -> None:
    arguments = {
        "candidate_education": [
            ResumeEducationEntry(
                degree="Bachelor of Technology",
                field_of_study="Computer Science",
            )
        ],
        "required_education": [
            "Bachelor's degree in Computer Science",
        ],
        "preferred_education": [
            "Master's degree in Computer Science",
        ],
    }

    first_result = score_education_alignment(**arguments)
    second_result = score_education_alignment(**arguments)

    assert first_result == second_result
def test_certification_alignment_matches_general_provider_requirement(
) -> None:
    result = score_certification_alignment(
        candidate_certifications=[
            ResumeCertificationEntry(
                name="AWS Cloud Practitioner",
                issuer="Amazon Web Services",
            )
        ],
        required_certifications=[
            "AWS certification",
        ],
        preferred_certifications=[],
    )

    assert result.score == 100.0
    assert result.required_score == 100.0
    assert result.preferred_score is None
    assert result.required_coverage == 1.0
    assert result.preferred_coverage is None

    assert result.matched_required_certifications == (
        "AWS certification",
    )
    assert result.missing_required_certifications == ()


def test_certification_alignment_matches_specific_certification(
) -> None:
    result = score_certification_alignment(
        candidate_certifications=[
            ResumeCertificationEntry(
                name="AWS Certified Developer Associate",
                issuer="Amazon Web Services",
            )
        ],
        required_certifications=[
            "AWS Certified Developer certification",
        ],
        preferred_certifications=[],
    )

    assert result.score == 100.0
    assert result.required_score == 100.0
    assert result.matched_required_certifications == (
        "AWS Certified Developer certification",
    )


def test_certification_alignment_rejects_different_certification(
) -> None:
    result = score_certification_alignment(
        candidate_certifications=[
            ResumeCertificationEntry(
                name="AWS Cloud Practitioner",
                issuer="Amazon Web Services",
            )
        ],
        required_certifications=[
            "AWS Certified Developer certification",
        ],
        preferred_certifications=[],
    )

    assert result.score == 0.0
    assert result.required_score == 0.0
    assert result.required_coverage == 0.0
    assert result.matched_required_certifications == ()
    assert result.missing_required_certifications == (
        "AWS Certified Developer certification",
    )


def test_certification_alignment_scores_required_and_preferred_separately(
) -> None:
    result = score_certification_alignment(
        candidate_certifications=[
            ResumeCertificationEntry(
                name="AWS Cloud Practitioner",
                issuer="Amazon Web Services",
            ),
            ResumeCertificationEntry(
                name="SQL Fundamentals",
                issuer="Data Academy",
            ),
        ],
        required_certifications=[
            "AWS certification",
        ],
        preferred_certifications=[
            "AWS Certified Developer certification preferred",
            "SQL Fundamentals certification",
        ],
    )

    assert result.score == 90.0
    assert result.required_score == 100.0
    assert result.preferred_score == 50.0
    assert result.required_coverage == 1.0
    assert result.preferred_coverage == 0.5

    assert result.matched_required_certifications == (
        "AWS certification",
    )
    assert result.matched_preferred_certifications == (
        "SQL Fundamentals certification",
    )
    assert result.missing_preferred_certifications == (
        "AWS Certified Developer certification preferred",
    )


def test_certification_alignment_supports_multiple_candidate_entries(
) -> None:
    result = score_certification_alignment(
        candidate_certifications=[
            ResumeCertificationEntry(
                name="Microsoft Azure Administrator",
                issuer="Microsoft",
            ),
            ResumeCertificationEntry(
                name="Google Cloud Professional",
                issuer="Google Cloud Platform",
            ),
        ],
        required_certifications=[
            "Azure Administrator certification",
        ],
        preferred_certifications=[
            "GCP Professional certification",
        ],
    )

    assert result.score == 100.0
    assert result.required_score == 100.0
    assert result.preferred_score == 100.0

    assert result.matched_required_certifications == (
        "Azure Administrator certification",
    )
    assert result.matched_preferred_certifications == (
        "GCP Professional certification",
    )


def test_certification_alignment_handles_missing_candidate_certifications(
) -> None:
    result = score_certification_alignment(
        candidate_certifications=[],
        required_certifications=[
            "AWS certification",
        ],
        preferred_certifications=[],
    )

    assert result.score == 0.0
    assert result.required_score == 0.0
    assert result.required_coverage == 0.0
    assert result.candidate_certifications == ()
    assert result.missing_required_certifications == (
        "AWS certification",
    )


def test_certification_alignment_handles_missing_job_requirements(
) -> None:
    result = score_certification_alignment(
        candidate_certifications=[
            ResumeCertificationEntry(
                name="AWS Cloud Practitioner",
                issuer="Amazon Web Services",
            )
        ],
        required_certifications=[],
        preferred_certifications=[],
    )

    assert result.score == 0.0
    assert result.required_score is None
    assert result.preferred_score is None
    assert result.required_coverage is None
    assert result.preferred_coverage is None
    assert result.matched_required_certifications == ()
    assert result.missing_required_certifications == ()


def test_certification_alignment_removes_required_from_preferred(
) -> None:
    requirement = "AWS certification"

    result = score_certification_alignment(
        candidate_certifications=[
            ResumeCertificationEntry(
                name="AWS Cloud Practitioner",
                issuer="Amazon Web Services",
            )
        ],
        required_certifications=[
            requirement,
        ],
        preferred_certifications=[
            requirement,
        ],
    )

    assert result.score == 100.0
    assert result.required_score == 100.0
    assert result.preferred_score is None
    assert result.matched_required_certifications == (
        requirement,
    )
    assert result.matched_preferred_certifications == ()


def test_certification_alignment_ignores_empty_candidate_entries(
) -> None:
    result = score_certification_alignment(
        candidate_certifications=[
            ResumeCertificationEntry(
                issuer="Unknown Provider",
            ),
            ResumeCertificationEntry(
                name="AWS Cloud Practitioner",
                issuer="Amazon Web Services",
            ),
        ],
        required_certifications=[
            "AWS certification",
        ],
        preferred_certifications=[],
    )

    assert result.candidate_certifications == (
        "unknown provider",
        "aws cloud practitioner aws",
    )
    assert result.score == 100.0


def test_certification_alignment_deduplicates_candidate_entries(
) -> None:
    result = score_certification_alignment(
        candidate_certifications=[
            ResumeCertificationEntry(
                name="AWS Cloud Practitioner",
                issuer="Amazon Web Services",
            ),
            ResumeCertificationEntry(
                name="AWS Cloud Practitioner",
                issuer="Amazon Web Services",
            ),
        ],
        required_certifications=[
            "AWS certification",
        ],
        preferred_certifications=[],
    )

    assert result.candidate_certifications == (
        "aws cloud practitioner aws",
    )
    assert result.score == 100.0


def test_certification_alignment_output_is_deterministic() -> None:
    arguments = {
        "candidate_certifications": [
            ResumeCertificationEntry(
                name="AWS Cloud Practitioner",
                issuer="Amazon Web Services",
            ),
            ResumeCertificationEntry(
                name="SQL Fundamentals",
                issuer="Data Academy",
            ),
        ],
        "required_certifications": [
            "AWS certification",
        ],
        "preferred_certifications": [
            "SQL Fundamentals certification",
        ],
    }

    first_result = score_certification_alignment(**arguments)
    second_result = score_certification_alignment(**arguments)

    assert first_result == second_result

def test_location_alignment_matches_equivalent_locations() -> None:
    result = score_location_alignment(
        candidate_location="Bangalore",
        job_location="Bengaluru, Karnataka",
    )

    assert result.score == 100.0
    assert result.status == "matched"
    assert result.candidate_location == "Bangalore"
    assert result.job_location == "Bengaluru, Karnataka"
    assert result.normalized_candidate_location == "bengaluru"
    assert result.normalized_job_location == "bengaluru karnataka"
    assert result.is_match is True


def test_location_alignment_rejects_different_locations() -> None:
    result = score_location_alignment(
        candidate_location="Hyderabad",
        job_location="Chennai",
    )

    assert result.score == 0.0
    assert result.status == "mismatched"
    assert result.normalized_candidate_location == "hyderabad"
    assert result.normalized_job_location == "chennai"
    assert result.is_match is False


def test_location_alignment_handles_missing_candidate_location() -> None:
    result = score_location_alignment(
        candidate_location=None,
        job_location="Hyderabad",
    )

    assert result.score == 0.0
    assert result.status == "candidate_location_missing"
    assert result.candidate_location is None
    assert result.job_location == "Hyderabad"
    assert result.normalized_candidate_location is None
    assert result.normalized_job_location == "hyderabad"
    assert result.is_match is None


def test_location_alignment_handles_blank_candidate_location() -> None:
    result = score_location_alignment(
        candidate_location=" ",
        job_location="Hyderabad",
    )

    assert result.score == 0.0
    assert result.status == "candidate_location_missing"
    assert result.normalized_candidate_location is None
    assert result.normalized_job_location == "hyderabad"
    assert result.is_match is None


def test_location_alignment_handles_missing_job_location() -> None:
    result = score_location_alignment(
        candidate_location="Hyderabad",
        job_location=None,
    )

    assert result.score == 0.0
    assert result.status == "job_location_not_specified"
    assert result.candidate_location == "Hyderabad"
    assert result.job_location is None
    assert result.normalized_candidate_location == "hyderabad"
    assert result.normalized_job_location is None
    assert result.is_match is None


def test_location_alignment_handles_blank_job_location() -> None:
    result = score_location_alignment(
        candidate_location="Hyderabad",
        job_location=" ",
    )

    assert result.score == 0.0
    assert result.status == "job_location_not_specified"
    assert result.normalized_candidate_location == "hyderabad"
    assert result.normalized_job_location is None
    assert result.is_match is None


def test_location_alignment_output_is_deterministic() -> None:
    arguments = {
        "candidate_location": "Hyderabad, Telangana",
        "job_location": "Hyderabad",
    }

    first_result = score_location_alignment(**arguments)
    second_result = score_location_alignment(**arguments)

    assert first_result == second_result


def test_work_mode_alignment_matches_exact_preference() -> None:
    result = score_work_mode_alignment(
        candidate_work_mode="hybrid",
        job_work_mode="hybrid",
    )

    assert result.score == 100.0
    assert result.status == "matched"
    assert result.candidate_work_mode == "hybrid"
    assert result.job_work_mode == "hybrid"
    assert result.is_match is True


def test_work_mode_alignment_rejects_different_mode() -> None:
    result = score_work_mode_alignment(
        candidate_work_mode="remote",
        job_work_mode="onsite",
    )

    assert result.score == 0.0
    assert result.status == "mismatched"
    assert result.candidate_work_mode == "remote"
    assert result.job_work_mode == "onsite"
    assert result.is_match is False


def test_work_mode_alignment_handles_missing_candidate_preference(
) -> None:
    result = score_work_mode_alignment(
        candidate_work_mode=None,
        job_work_mode="hybrid",
    )

    assert result.score == 0.0
    assert result.status == "candidate_preference_missing"
    assert result.candidate_work_mode is None
    assert result.job_work_mode == "hybrid"
    assert result.is_match is None


def test_work_mode_alignment_handles_missing_job_mode() -> None:
    result = score_work_mode_alignment(
        candidate_work_mode="remote",
        job_work_mode=None,
    )

    assert result.score == 0.0
    assert result.status == "job_work_mode_not_specified"
    assert result.candidate_work_mode == "remote"
    assert result.job_work_mode is None
    assert result.is_match is None


def test_work_mode_alignment_handles_both_values_missing() -> None:
    result = score_work_mode_alignment(
        candidate_work_mode=None,
        job_work_mode=None,
    )

    assert result.score == 0.0
    assert result.status == "job_work_mode_not_specified"
    assert result.candidate_work_mode is None
    assert result.job_work_mode is None
    assert result.is_match is None


def test_work_mode_alignment_output_is_deterministic() -> None:
    arguments = {
        "candidate_work_mode": None,
        "job_work_mode": "hybrid",
    }

    first_result = score_work_mode_alignment(**arguments)
    second_result = score_work_mode_alignment(**arguments)

    assert first_result == second_result

def test_required_skill_score_cap_returns_none_without_requirement(
) -> None:
    assert required_skill_score_cap(
        required_skill_coverage=None,
    ) is None


def test_required_skill_score_cap_applies_zero_match_cap() -> None:
    assert required_skill_score_cap(
        required_skill_coverage=0.0,
    ) == 35.0


def test_required_skill_score_cap_applies_low_coverage_cap() -> None:
    assert required_skill_score_cap(
        required_skill_coverage=0.25,
    ) == 49.0


def test_required_skill_score_cap_applies_moderate_coverage_cap(
) -> None:
    assert required_skill_score_cap(
        required_skill_coverage=0.50,
    ) == 69.0


def test_required_skill_score_cap_does_not_cap_high_coverage(
) -> None:
    assert required_skill_score_cap(
        required_skill_coverage=0.75,
    ) is None

    assert required_skill_score_cap(
        required_skill_coverage=1.0,
    ) is None


def test_required_skill_score_cap_validates_coverage_range() -> None:
    with pytest.raises(
        ValueError,
        match="Required-skill coverage",
    ):
        required_skill_score_cap(
            required_skill_coverage=-0.01,
        )

    with pytest.raises(
        ValueError,
        match="Required-skill coverage",
    ):
        required_skill_score_cap(
            required_skill_coverage=1.01,
        )


def test_overall_score_combines_all_components() -> None:
    result = calculate_overall_score(
        skill_score=80.0,
        experience_score=70.0,
        education_score=60.0,
        certification_score=50.0,
        location_score=40.0,
        work_mode_score=30.0,
        required_skill_coverage=1.0,
    )

    assert result.raw_score == 67.5
    assert result.score == 67.5
    assert result.available_weight == 1.0
    assert result.required_skill_cap is None
    assert result.was_capped is False


def test_overall_score_renormalizes_available_weights() -> None:
    result = calculate_overall_score(
        skill_score=100.0,
        experience_score=100.0,
        education_score=100.0,
        certification_score=None,
        location_score=100.0,
        work_mode_score=None,
        required_skill_coverage=1.0,
    )

    assert result.raw_score == 100.0
    assert result.score == 100.0
    assert result.available_weight == 0.85
    assert result.required_skill_cap is None
    assert result.was_capped is False


def test_overall_score_returns_zero_without_available_components(
) -> None:
    result = calculate_overall_score(
        skill_score=None,
        experience_score=None,
        education_score=None,
        certification_score=None,
        location_score=None,
        work_mode_score=None,
        required_skill_coverage=None,
    )

    assert result.raw_score == 0.0
    assert result.score == 0.0
    assert result.available_weight == 0.0
    assert result.required_skill_cap is None
    assert result.was_capped is False


def test_overall_score_applies_zero_required_skill_cap() -> None:
    result = calculate_overall_score(
        skill_score=0.0,
        experience_score=100.0,
        education_score=100.0,
        certification_score=100.0,
        location_score=100.0,
        work_mode_score=100.0,
        required_skill_coverage=0.0,
    )

    assert result.raw_score == 50.0
    assert result.score == 35.0
    assert result.required_skill_cap == 35.0
    assert result.was_capped is True


def test_overall_score_applies_low_required_skill_cap() -> None:
    result = calculate_overall_score(
        skill_score=25.0,
        experience_score=100.0,
        education_score=100.0,
        certification_score=100.0,
        location_score=100.0,
        work_mode_score=None,
        required_skill_coverage=0.25,
    )

    assert result.raw_score == 58.33
    assert result.score == 49.0
    assert result.available_weight == 0.9
    assert result.required_skill_cap == 49.0
    assert result.was_capped is True


def test_overall_score_applies_moderate_required_skill_cap(
) -> None:
    result = calculate_overall_score(
        skill_score=60.0,
        experience_score=100.0,
        education_score=100.0,
        certification_score=100.0,
        location_score=100.0,
        work_mode_score=100.0,
        required_skill_coverage=0.50,
    )

    assert result.raw_score == 80.0
    assert result.score == 69.0
    assert result.required_skill_cap == 69.0
    assert result.was_capped is True


def test_overall_score_does_not_raise_score_to_cap() -> None:
    result = calculate_overall_score(
        skill_score=20.0,
        experience_score=20.0,
        education_score=20.0,
        certification_score=20.0,
        location_score=20.0,
        work_mode_score=20.0,
        required_skill_coverage=0.25,
    )

    assert result.raw_score == 20.0
    assert result.score == 20.0
    assert result.required_skill_cap == 49.0
    assert result.was_capped is False


@pytest.mark.parametrize(
    "field_name",
    [
        "skill_score",
        "experience_score",
        "education_score",
        "certification_score",
        "location_score",
        "work_mode_score",
    ],
)
@pytest.mark.parametrize(
    "invalid_score",
    [
        -0.01,
        100.01,
    ],
)
def test_overall_score_validates_component_score_ranges(
    field_name: str,
    invalid_score: float,
) -> None:
    arguments = {
        "skill_score": 100.0,
        "experience_score": 100.0,
        "education_score": 100.0,
        "certification_score": 100.0,
        "location_score": 100.0,
        "work_mode_score": 100.0,
        "required_skill_coverage": 1.0,
    }
    arguments[field_name] = invalid_score

    with pytest.raises(
        ValueError,
        match=field_name,
    ):
        calculate_overall_score(**arguments)


def test_overall_score_output_is_deterministic() -> None:
    arguments = {
        "skill_score": 75.0,
        "experience_score": 80.0,
        "education_score": None,
        "certification_score": 50.0,
        "location_score": 100.0,
        "work_mode_score": None,
        "required_skill_coverage": 0.75,
    }

    first_result = calculate_overall_score(**arguments)
    second_result = calculate_overall_score(**arguments)

    assert first_result == second_result

def test_recommendation_classifies_strong_match() -> None:
    result = classify_match_recommendation(
        score=85.0,
        confidence_score=80.0,
    )

    assert result.recommendation == "strong_match"
    assert result.score == 85.0
    assert result.confidence_score == 80.0
    assert result.reason == (
        "The candidate strongly satisfies the available "
        "job requirements."
    )


def test_recommendation_classifies_good_match() -> None:
    result = classify_match_recommendation(
        score=70.0,
        confidence_score=80.0,
    )

    assert result.recommendation == "good_match"
    assert result.score == 70.0


def test_recommendation_classifies_partial_match() -> None:
    result = classify_match_recommendation(
        score=50.0,
        confidence_score=80.0,
    )

    assert result.recommendation == "partial_match"
    assert result.score == 50.0


def test_recommendation_classifies_weak_match() -> None:
    result = classify_match_recommendation(
        score=49.99,
        confidence_score=80.0,
    )

    assert result.recommendation == "weak_match"
    assert result.score == 49.99


@pytest.mark.parametrize(
    "score",
    [
        0.0,
        49.99,
        50.0,
        69.99,
        70.0,
        84.99,
        85.0,
        100.0,
    ],
)
def test_recommendation_respects_threshold_boundaries(
    score: float,
) -> None:
    result = classify_match_recommendation(
        score=score,
        confidence_score=100.0,
    )

    if score >= 85.0:
        expected = "strong_match"
    elif score >= 70.0:
        expected = "good_match"
    elif score >= 50.0:
        expected = "partial_match"
    else:
        expected = "weak_match"

    assert result.recommendation == expected


def test_recommendation_uses_insufficient_data_below_threshold(
) -> None:
    result = classify_match_recommendation(
        score=100.0,
        confidence_score=39.99,
    )

    assert result.recommendation == "insufficient_data"
    assert result.score == 100.0
    assert result.confidence_score == 39.99
    assert result.reason == (
        "Available candidate and job information is "
        "insufficient for a reliable recommendation."
    )


def test_recommendation_does_not_use_insufficient_data_at_threshold(
) -> None:
    result = classify_match_recommendation(
        score=90.0,
        confidence_score=40.0,
    )

    assert result.recommendation == "strong_match"


@pytest.mark.parametrize(
    "invalid_score",
    [
        -0.01,
        100.01,
    ],
)
def test_recommendation_validates_score_range(
    invalid_score: float,
) -> None:
    with pytest.raises(
        ValueError,
        match="Overall match score",
    ):
        classify_match_recommendation(
            score=invalid_score,
            confidence_score=80.0,
        )


@pytest.mark.parametrize(
    "invalid_confidence",
    [
        -0.01,
        100.01,
    ],
)
def test_recommendation_validates_confidence_range(
    invalid_confidence: float,
) -> None:
    with pytest.raises(
        ValueError,
        match="Confidence score",
    ):
        classify_match_recommendation(
            score=80.0,
            confidence_score=invalid_confidence,
        )


def test_recommendation_output_is_deterministic() -> None:
    arguments = {
        "score": 76.0,
        "confidence_score": 85.0,
    }

    first_result = classify_match_recommendation(**arguments)
    second_result = classify_match_recommendation(**arguments)

    assert first_result == second_result

def test_match_confidence_with_all_component_data_available() -> None:
    result = calculate_match_confidence(
        resume_profile_confidence=0.90,
        job_requirement_profile_confidence=0.80,
        skill_data_available=True,
        experience_data_available=True,
        education_data_available=True,
        certification_data_available=True,
        location_data_available=True,
        work_mode_data_available=True,
    )

    assert result.score == 85.0
    assert result.parser_confidence_score == 85.0
    assert result.data_coverage_score == 100.0
    assert result.specified_weight == 1.0
    assert result.assessable_weight == 1.0
    assert result.missing_components == ()
    assert result.unspecified_components == ()


def test_match_confidence_reduces_score_for_missing_work_mode(
) -> None:
    result = calculate_match_confidence(
        resume_profile_confidence=0.90,
        job_requirement_profile_confidence=0.80,
        skill_data_available=True,
        experience_data_available=True,
        education_data_available=True,
        certification_data_available=True,
        location_data_available=True,
        work_mode_data_available=False,
    )

    assert result.score == 76.5
    assert result.parser_confidence_score == 85.0
    assert result.data_coverage_score == 90.0
    assert result.specified_weight == 1.0
    assert result.assessable_weight == 0.9
    assert result.missing_components == (
        "work_mode",
    )
    assert result.unspecified_components == ()


def test_match_confidence_excludes_unspecified_components() -> None:
    result = calculate_match_confidence(
        resume_profile_confidence=0.90,
        job_requirement_profile_confidence=0.80,
        skill_data_available=True,
        experience_data_available=True,
        education_data_available=None,
        certification_data_available=None,
        location_data_available=None,
        work_mode_data_available=None,
    )

    assert result.score == 85.0
    assert result.parser_confidence_score == 85.0
    assert result.data_coverage_score == 100.0
    assert result.specified_weight == 0.7
    assert result.assessable_weight == 0.7
    assert result.missing_components == ()
    assert result.unspecified_components == (
        "education",
        "certifications",
        "location",
        "work_mode",
    )


def test_match_confidence_applies_component_weights_to_coverage(
) -> None:
    result = calculate_match_confidence(
        resume_profile_confidence=0.90,
        job_requirement_profile_confidence=0.80,
        skill_data_available=False,
        experience_data_available=True,
        education_data_available=True,
        certification_data_available=True,
        location_data_available=True,
        work_mode_data_available=True,
    )

    assert result.parser_confidence_score == 85.0
    assert result.data_coverage_score == 50.0
    assert result.score == 42.5
    assert result.specified_weight == 1.0
    assert result.assessable_weight == 0.5
    assert result.missing_components == (
        "skills",
    )


def test_match_confidence_tracks_multiple_missing_components(
) -> None:
    result = calculate_match_confidence(
        resume_profile_confidence=1.0,
        job_requirement_profile_confidence=1.0,
        skill_data_available=True,
        experience_data_available=False,
        education_data_available=False,
        certification_data_available=True,
        location_data_available=True,
        work_mode_data_available=False,
    )

    assert result.parser_confidence_score == 100.0
    assert result.data_coverage_score == 60.0
    assert result.score == 60.0
    assert result.specified_weight == 1.0
    assert result.assessable_weight == 0.6
    assert result.missing_components == (
        "experience",
        "education",
        "work_mode",
    )


def test_match_confidence_returns_zero_without_specified_components(
) -> None:
    result = calculate_match_confidence(
        resume_profile_confidence=0.90,
        job_requirement_profile_confidence=0.80,
        skill_data_available=None,
        experience_data_available=None,
        education_data_available=None,
        certification_data_available=None,
        location_data_available=None,
        work_mode_data_available=None,
    )

    assert result.score == 0.0
    assert result.parser_confidence_score == 85.0
    assert result.data_coverage_score == 0.0
    assert result.specified_weight == 0.0
    assert result.assessable_weight == 0.0
    assert result.missing_components == ()
    assert result.unspecified_components == (
        "skills",
        "experience",
        "education",
        "certifications",
        "location",
        "work_mode",
    )


def test_match_confidence_supports_parser_confidence_extremes(
) -> None:
    result = calculate_match_confidence(
        resume_profile_confidence=0.0,
        job_requirement_profile_confidence=1.0,
        skill_data_available=True,
        experience_data_available=True,
        education_data_available=True,
        certification_data_available=True,
        location_data_available=True,
        work_mode_data_available=True,
    )

    assert result.parser_confidence_score == 50.0
    assert result.data_coverage_score == 100.0
    assert result.score == 50.0


@pytest.mark.parametrize(
    (
        "field_name",
        "resume_confidence",
        "job_confidence",
    ),
    [
        (
            "resume_profile_confidence",
            -0.01,
            0.80,
        ),
        (
            "resume_profile_confidence",
            1.01,
            0.80,
        ),
        (
            "job_requirement_profile_confidence",
            0.90,
            -0.01,
        ),
        (
            "job_requirement_profile_confidence",
            0.90,
            1.01,
        ),
    ],
)
def test_match_confidence_validates_parser_confidence_ranges(
    field_name: str,
    resume_confidence: float,
    job_confidence: float,
) -> None:
    with pytest.raises(
        ValueError,
        match=field_name,
    ):
        calculate_match_confidence(
            resume_profile_confidence=(
                resume_confidence
            ),
            job_requirement_profile_confidence=(
                job_confidence
            ),
            skill_data_available=True,
            experience_data_available=True,
            education_data_available=True,
            certification_data_available=True,
            location_data_available=True,
            work_mode_data_available=True,
        )


def test_match_confidence_output_is_deterministic() -> None:
    arguments = {
        "resume_profile_confidence": 0.90,
        "job_requirement_profile_confidence": 0.80,
        "skill_data_available": True,
        "experience_data_available": True,
        "education_data_available": None,
        "certification_data_available": False,
        "location_data_available": True,
        "work_mode_data_available": False,
    }

    first_result = calculate_match_confidence(**arguments)
    second_result = calculate_match_confidence(**arguments)

    assert first_result == second_result

def _default_analysis_results() -> tuple[
    SkillMatchResult,
    ExperienceMatchResult,
    EducationMatchResult,
    CertificationMatchResult,
    LocationMatchResult,
    WorkModeMatchResult,
    OverallScoreResult,
    MatchConfidenceResult,
]:
    skill_result = SkillMatchResult(
        score=90.0,
        required_score=100.0,
        preferred_score=50.0,
        required_coverage=1.0,
        preferred_coverage=0.5,
        matched_required_skills=(
            "React",
            "PostgreSQL",
        ),
        missing_required_skills=(),
        matched_preferred_skills=(
            "AWS",
        ),
        missing_preferred_skills=(
            "Docker",
        ),
    )

    experience_result = ExperienceMatchResult(
        score=83.33,
        status="below_minimum",
        candidate_experience_months=30,
        minimum_experience_months=36,
        maximum_experience_months=60,
        gap_months=6,
        meets_minimum=False,
        within_maximum=True,
    )

    education_result = EducationMatchResult(
        score=100.0,
        required_score=100.0,
        preferred_score=None,
        required_coverage=1.0,
        preferred_coverage=None,
        candidate_education=(
            "bachelor computer science",
        ),
        matched_required_education=(
            "Bachelor's degree in Computer Science",
        ),
        missing_required_education=(),
        matched_preferred_education=(),
        missing_preferred_education=(),
    )

    certification_result = CertificationMatchResult(
        score=100.0,
        required_score=None,
        preferred_score=100.0,
        required_coverage=None,
        preferred_coverage=1.0,
        candidate_certifications=(
            "aws cloud practitioner aws",
        ),
        matched_required_certifications=(),
        missing_required_certifications=(),
        matched_preferred_certifications=(
            "AWS certification",
        ),
        missing_preferred_certifications=(),
    )

    location_result = LocationMatchResult(
        score=100.0,
        status="matched",
        candidate_location="Bangalore",
        job_location="Bengaluru, Karnataka",
        normalized_candidate_location="bengaluru",
        normalized_job_location="bengaluru karnataka",
        is_match=True,
    )

    work_mode_result = WorkModeMatchResult(
        score=0.0,
        status="candidate_preference_missing",
        candidate_work_mode=None,
        job_work_mode="hybrid",
        is_match=None,
    )

    overall_result = OverallScoreResult(
        raw_score=81.67,
        score=81.67,
        available_weight=1.0,
        required_skill_cap=None,
        was_capped=False,
    )

    confidence_result = MatchConfidenceResult(
        score=76.5,
        parser_confidence_score=85.0,
        data_coverage_score=90.0,
        specified_weight=1.0,
        assessable_weight=0.9,
        missing_components=(
            "work_mode",
        ),
        unspecified_components=(),
    )

    return (
        skill_result,
        experience_result,
        education_result,
        certification_result,
        location_result,
        work_mode_result,
        overall_result,
        confidence_result,
    )


def test_build_match_analysis_data_maps_component_results() -> None:
    (
        skill_result,
        experience_result,
        education_result,
        certification_result,
        location_result,
        work_mode_result,
        overall_result,
        confidence_result,
    ) = _default_analysis_results()

    result = build_match_analysis_data(
        skill_result=skill_result,
        experience_result=experience_result,
        education_result=education_result,
        certification_result=certification_result,
        location_result=location_result,
        work_mode_result=work_mode_result,
        overall_result=overall_result,
        confidence_result=confidence_result,
    )

    assert result.matched_required_skills == [
        "React",
        "PostgreSQL",
    ]
    assert result.missing_required_skills == []
    assert result.matched_preferred_skills == [
        "AWS",
    ]
    assert result.missing_preferred_skills == [
        "Docker",
    ]

    assert result.experience_analysis == (
        "Candidate experience is below the minimum "
        "requirement by 6 months."
    )

    assert result.matched_required_education == [
        "Bachelor's degree in Computer Science",
    ]
    assert result.matched_preferred_certifications == [
        "AWS certification",
    ]

    assert result.location_analysis == (
        "Candidate location matches the job location."
    )
    assert result.work_mode_analysis == (
        "The job specifies a work mode, but candidate "
        "work-mode preference is unavailable."
    )

    assert result.strengths == [
        "Candidate matched all required skills.",
        (
            "Candidate matched all required education "
            "requirements."
        ),
        "Candidate location matches the job location.",
    ]

    assert result.gaps == [
        (
            "Candidate experience is 6 months below the "
            "minimum requirement."
        ),
    ]

    assert result.missing_data == [
        "Candidate work-mode preference is unavailable.",
    ]


def test_build_match_analysis_data_adds_score_cap_warning() -> None:
    (
        skill_result,
        experience_result,
        education_result,
        certification_result,
        location_result,
        work_mode_result,
        overall_result,
        confidence_result,
    ) = _default_analysis_results()

    overall_result = replace(
        overall_result,
        raw_score=80.0,
        score=49.0,
        required_skill_cap=49.0,
        was_capped=True,
    )

    result = build_match_analysis_data(
        skill_result=skill_result,
        experience_result=experience_result,
        education_result=education_result,
        certification_result=certification_result,
        location_result=location_result,
        work_mode_result=work_mode_result,
        overall_result=overall_result,
        confidence_result=confidence_result,
    )

    assert result.warnings == [
        (
            "Overall score was capped at 49.0 because "
            "required-skill coverage was insufficient."
        ),
    ]


def test_build_match_analysis_data_adds_low_confidence_warning(
) -> None:
    (
        skill_result,
        experience_result,
        education_result,
        certification_result,
        location_result,
        work_mode_result,
        overall_result,
        confidence_result,
    ) = _default_analysis_results()

    confidence_result = replace(
        confidence_result,
        score=35.0,
        parser_confidence_score=50.0,
        data_coverage_score=70.0,
    )

    result = build_match_analysis_data(
        skill_result=skill_result,
        experience_result=experience_result,
        education_result=education_result,
        certification_result=certification_result,
        location_result=location_result,
        work_mode_result=work_mode_result,
        overall_result=overall_result,
        confidence_result=confidence_result,
    )

    assert result.warnings == [
        (
            "Match confidence is below the reliable "
            "recommendation threshold."
        ),
    ]


def test_build_match_analysis_data_collects_matching_gaps() -> None:
    (
        skill_result,
        experience_result,
        education_result,
        certification_result,
        location_result,
        work_mode_result,
        overall_result,
        confidence_result,
    ) = _default_analysis_results()

    skill_result = replace(
        skill_result,
        score=0.0,
        required_score=0.0,
        required_coverage=0.0,
        matched_required_skills=(),
        missing_required_skills=(
            "Docker",
        ),
    )

    education_result = replace(
        education_result,
        score=0.0,
        required_score=0.0,
        required_coverage=0.0,
        matched_required_education=(),
        missing_required_education=(
            "Master's degree in Computer Science",
        ),
    )

    certification_result = replace(
        certification_result,
        score=0.0,
        required_score=0.0,
        required_coverage=0.0,
        matched_required_certifications=(),
        missing_required_certifications=(
            "AWS Certified Developer",
        ),
    )

    location_result = replace(
        location_result,
        score=0.0,
        status="mismatched",
        candidate_location="Hyderabad",
        job_location="Chennai",
        normalized_candidate_location="hyderabad",
        normalized_job_location="chennai",
        is_match=False,
    )

    work_mode_result = replace(
        work_mode_result,
        score=0.0,
        status="mismatched",
        candidate_work_mode="remote",
        job_work_mode="onsite",
        is_match=False,
    )

    result = build_match_analysis_data(
        skill_result=skill_result,
        experience_result=experience_result,
        education_result=education_result,
        certification_result=certification_result,
        location_result=location_result,
        work_mode_result=work_mode_result,
        overall_result=overall_result,
        confidence_result=confidence_result,
    )

    assert result.gaps == [
        "Missing required skills: Docker.",
        (
            "Candidate experience is 6 months below the "
            "minimum requirement."
        ),
        (
            "Missing required education: Master's degree "
            "in Computer Science."
        ),
        (
            "Missing required certifications: "
            "AWS Certified Developer."
        ),
        (
            "Candidate location does not match the job "
            "location."
        ),
        (
            "Candidate work-mode preference does not match "
            "the job work mode."
        ),
    ]


def test_build_match_analysis_data_collects_all_strengths() -> None:
    (
        skill_result,
        experience_result,
        education_result,
        certification_result,
        location_result,
        work_mode_result,
        overall_result,
        confidence_result,
    ) = _default_analysis_results()

    skill_result = replace(
        skill_result,
        score=100.0,
        preferred_score=100.0,
        preferred_coverage=1.0,
        missing_preferred_skills=(),
    )

    experience_result = replace(
        experience_result,
        score=100.0,
        status="within_range",
        gap_months=0,
        meets_minimum=True,
        within_maximum=True,
    )

    certification_result = replace(
        certification_result,
        required_score=100.0,
        required_coverage=1.0,
        matched_required_certifications=(
            "AWS certification",
        ),
    )

    work_mode_result = replace(
        work_mode_result,
        score=100.0,
        status="matched",
        candidate_work_mode="hybrid",
        is_match=True,
    )

    result = build_match_analysis_data(
        skill_result=skill_result,
        experience_result=experience_result,
        education_result=education_result,
        certification_result=certification_result,
        location_result=location_result,
        work_mode_result=work_mode_result,
        overall_result=overall_result,
        confidence_result=confidence_result,
    )

    assert result.strengths == [
        "Candidate matched all required skills.",
        "Candidate matched all preferred skills.",
        (
            "Candidate experience satisfies the job "
            "requirement."
        ),
        (
            "Candidate matched all required education "
            "requirements."
        ),
        (
            "Candidate matched all required certification "
            "requirements."
        ),
        "Candidate location matches the job location.",
        (
            "Candidate work-mode preference matches the "
            "job."
        ),
    ]


def test_build_match_analysis_data_humanizes_missing_components(
) -> None:
    (
        skill_result,
        experience_result,
        education_result,
        certification_result,
        location_result,
        work_mode_result,
        overall_result,
        confidence_result,
    ) = _default_analysis_results()

    confidence_result = replace(
        confidence_result,
        missing_components=(
            "skills",
            "experience",
            "education",
            "certifications",
            "location",
            "work_mode",
            "custom",
        ),
    )

    result = build_match_analysis_data(
        skill_result=skill_result,
        experience_result=experience_result,
        education_result=education_result,
        certification_result=certification_result,
        location_result=location_result,
        work_mode_result=work_mode_result,
        overall_result=overall_result,
        confidence_result=confidence_result,
    )

    assert result.missing_data == [
        "Candidate skill data is unavailable.",
        "Candidate experience data is unavailable.",
        "Candidate education data is unavailable.",
        "Candidate certification data is unavailable.",
        "Candidate location data is unavailable.",
        "Candidate work-mode preference is unavailable.",
        "Candidate custom data is unavailable.",
    ]


def test_build_match_analysis_data_describes_unspecified_requirements(
) -> None:
    (
        skill_result,
        experience_result,
        education_result,
        certification_result,
        location_result,
        work_mode_result,
        overall_result,
        confidence_result,
    ) = _default_analysis_results()

    experience_result = replace(
        experience_result,
        score=0.0,
        status="requirement_not_specified",
        minimum_experience_months=None,
        maximum_experience_months=None,
        gap_months=None,
        meets_minimum=None,
        within_maximum=None,
    )

    education_result = replace(
        education_result,
        score=0.0,
        required_score=None,
        preferred_score=None,
        required_coverage=None,
        preferred_coverage=None,
        candidate_education=(),
        matched_required_education=(),
        missing_required_education=(),
    )

    certification_result = replace(
        certification_result,
        score=0.0,
        required_score=None,
        preferred_score=None,
        required_coverage=None,
        preferred_coverage=None,
        candidate_certifications=(),
        matched_preferred_certifications=(),
    )

    location_result = replace(
        location_result,
        score=0.0,
        status="job_location_not_specified",
        job_location=None,
        normalized_job_location=None,
        is_match=None,
    )

    work_mode_result = replace(
        work_mode_result,
        score=0.0,
        status="job_work_mode_not_specified",
        job_work_mode=None,
        is_match=None,
    )

    result = build_match_analysis_data(
        skill_result=skill_result,
        experience_result=experience_result,
        education_result=education_result,
        certification_result=certification_result,
        location_result=location_result,
        work_mode_result=work_mode_result,
        overall_result=overall_result,
        confidence_result=confidence_result,
    )

    assert result.experience_analysis == (
        "The job does not specify an experience requirement."
    )
    assert result.education_analysis == (
        "The job does not specify education requirements."
    )
    assert result.certification_analysis == (
        "The job does not specify certification requirements."
    )
    assert result.location_analysis == (
        "The job does not specify a location."
    )
    assert result.work_mode_analysis == (
        "The job does not specify a work mode."
    )


def test_build_match_analysis_data_describes_missing_candidate_data(
) -> None:
    (
        skill_result,
        experience_result,
        education_result,
        certification_result,
        location_result,
        work_mode_result,
        overall_result,
        confidence_result,
    ) = _default_analysis_results()

    experience_result = replace(
        experience_result,
        score=0.0,
        status="candidate_experience_missing",
        candidate_experience_months=None,
        gap_months=None,
        meets_minimum=None,
        within_maximum=None,
    )

    education_result = replace(
        education_result,
        score=0.0,
        required_score=0.0,
        required_coverage=0.0,
        candidate_education=(),
    )

    certification_result = replace(
        certification_result,
        score=0.0,
        preferred_score=0.0,
        preferred_coverage=0.0,
        candidate_certifications=(),
    )

    location_result = replace(
        location_result,
        score=0.0,
        status="candidate_location_missing",
        candidate_location=None,
        normalized_candidate_location=None,
        is_match=None,
    )

    result = build_match_analysis_data(
        skill_result=skill_result,
        experience_result=experience_result,
        education_result=education_result,
        certification_result=certification_result,
        location_result=location_result,
        work_mode_result=work_mode_result,
        overall_result=overall_result,
        confidence_result=confidence_result,
    )

    assert result.experience_analysis == (
        "The job specifies an experience requirement, but "
        "candidate experience data is unavailable."
    )
    assert result.education_analysis == (
        "The job specifies education requirements, but "
        "candidate education data is unavailable."
    )
    assert result.certification_analysis == (
        "The job specifies certification requirements, but "
        "candidate certification data is unavailable."
    )
    assert result.location_analysis == (
        "The job specifies a location, but candidate "
        "location data is unavailable."
    )
    assert result.work_mode_analysis == (
        "The job specifies a work mode, but candidate "
        "work-mode preference is unavailable."
    )


def test_build_match_analysis_data_includes_scoring_metadata(
) -> None:
    (
        skill_result,
        experience_result,
        education_result,
        certification_result,
        location_result,
        work_mode_result,
        overall_result,
        confidence_result,
    ) = _default_analysis_results()

    result = build_match_analysis_data(
        skill_result=skill_result,
        experience_result=experience_result,
        education_result=education_result,
        certification_result=certification_result,
        location_result=location_result,
        work_mode_result=work_mode_result,
        overall_result=overall_result,
        confidence_result=confidence_result,
    )

    assert result.additional_alignment == [
        (
            "Overall score before required-skill caps: "
            "81.67."
        ),
        "Parser confidence score: 85.0.",
        "Assessable data coverage: 90.0%.",
    ]


def test_build_match_analysis_data_is_deterministic() -> None:
    (
        skill_result,
        experience_result,
        education_result,
        certification_result,
        location_result,
        work_mode_result,
        overall_result,
        confidence_result,
    ) = _default_analysis_results()

    arguments = {
        "skill_result": skill_result,
        "experience_result": experience_result,
        "education_result": education_result,
        "certification_result": certification_result,
        "location_result": location_result,
        "work_mode_result": work_mode_result,
        "overall_result": overall_result,
        "confidence_result": confidence_result,
    }

    first_result = build_match_analysis_data(**arguments)
    second_result = build_match_analysis_data(**arguments)

    assert first_result == second_result

def _build_matcher_resume_profile() -> ResumeProfileData:
    return ResumeProfileData(
        full_name="Harsha Vardhan",
        location="Bangalore",
        total_experience_months=30,
        skills=[
            "React.js",
            "PostgreSQL",
            "AWS",
        ],
        education=[
            ResumeEducationEntry(
                degree="Bachelor of Technology",
                field_of_study="Computer Science",
            )
        ],
        certifications=[
            ResumeCertificationEntry(
                name="AWS Cloud Practitioner",
                issuer="Amazon Web Services",
            )
        ],
        confidence=0.90,
    )


def _build_matcher_job_profile() -> JobRequirementProfileData:
    return JobRequirementProfileData(
        job_title="Frontend Engineer",
        location="Bengaluru, Karnataka",
        work_mode="hybrid",
        required_skills=[
            "React",
            "PostgreSQL",
        ],
        preferred_skills=[
            "AWS",
            "Docker",
        ],
        minimum_experience_years=3,
        maximum_experience_years=5,
        required_education=[
            "Bachelor's degree in Computer Science",
        ],
        preferred_certifications=[
            "AWS certification",
        ],
        confidence=0.80,
    )


def test_end_to_end_matcher_calculates_complete_result() -> None:
    result = match_candidate_profile_to_job_requirements(
        resume_profile=_build_matcher_resume_profile(),
        job_requirement_profile=_build_matcher_job_profile(),
    )

    assert result.skill_result.score == 90.0
    assert result.experience_result.score == 83.33
    assert result.education_result.score == 100.0
    assert result.certification_result.score == 100.0
    assert result.location_result.score == 100.0
    assert result.work_mode_result.score == 0.0

    assert result.overall_result.raw_score == 81.67
    assert result.overall_result.score == 81.67
    assert result.overall_result.was_capped is False

    assert result.confidence_result.score == 76.5
    assert result.confidence_result.missing_components == (
        "work_mode",
    )

    assert (
        result.recommendation_result.recommendation
        == "good_match"
    )

    assert result.analysis_data.missing_data == [
        "Candidate work-mode preference is unavailable.",
    ]


def test_end_to_end_matcher_uses_candidate_work_mode() -> None:
    result = match_candidate_profile_to_job_requirements(
        resume_profile=_build_matcher_resume_profile(),
        job_requirement_profile=_build_matcher_job_profile(),
        candidate_work_mode="hybrid",
    )

    assert result.work_mode_result.score == 100.0
    assert result.work_mode_result.status == "matched"

    assert result.overall_result.raw_score == 91.67
    assert result.overall_result.score == 91.67

    assert result.confidence_result.score == 85.0
    assert result.confidence_result.data_coverage_score == 100.0
    assert result.confidence_result.missing_components == ()

    assert (
        result.recommendation_result.recommendation
        == "strong_match"
    )


def test_end_to_end_matcher_excludes_unspecified_components(
) -> None:
    resume_profile = ResumeProfileData(
        full_name="Candidate",
        skills=[
            "React.js",
        ],
        confidence=1.0,
    )

    job_profile = JobRequirementProfileData(
        job_title="React Developer",
        required_skills=[
            "React",
        ],
        confidence=1.0,
    )

    result = match_candidate_profile_to_job_requirements(
        resume_profile=resume_profile,
        job_requirement_profile=job_profile,
    )

    assert result.skill_result.score == 100.0

    assert result.overall_result.raw_score == 100.0
    assert result.overall_result.score == 100.0
    assert result.overall_result.available_weight == 0.5

    assert result.confidence_result.score == 100.0
    assert result.confidence_result.specified_weight == 0.5
    assert result.confidence_result.assessable_weight == 0.5

    assert result.confidence_result.unspecified_components == (
        "experience",
        "education",
        "certifications",
        "location",
        "work_mode",
    )

    assert (
        result.recommendation_result.recommendation
        == "strong_match"
    )


def test_end_to_end_matcher_marks_missing_candidate_skills(
) -> None:
    resume_profile = ResumeProfileData(
        full_name="Candidate",
        skills=[],
        confidence=1.0,
    )

    job_profile = JobRequirementProfileData(
        job_title="React Developer",
        required_skills=[
            "React",
        ],
        confidence=1.0,
    )

    result = match_candidate_profile_to_job_requirements(
        resume_profile=resume_profile,
        job_requirement_profile=job_profile,
    )

    assert result.skill_result.score == 0.0
    assert result.skill_result.missing_required_skills == (
        "React",
    )

    assert result.overall_result.score == 0.0
    assert result.confidence_result.score == 0.0
    assert result.confidence_result.missing_components == (
        "skills",
    )

    assert (
        result.recommendation_result.recommendation
        == "insufficient_data"
    )

    assert result.analysis_data.missing_data == [
        "Candidate skill data is unavailable.",
    ]


def test_end_to_end_matcher_applies_required_skill_cap() -> None:
    resume_profile = ResumeProfileData(
        full_name="Candidate",
        location="Hyderabad",
        total_experience_months=48,
        skills=[
            "React",
        ],
        education=[
            ResumeEducationEntry(
                degree="Bachelor of Technology",
                field_of_study="Computer Science",
            )
        ],
        certifications=[
            ResumeCertificationEntry(
                name="AWS Cloud Practitioner",
                issuer="Amazon Web Services",
            )
        ],
        confidence=1.0,
    )

    job_profile = JobRequirementProfileData(
        job_title="Software Engineer",
        location="Hyderabad",
        work_mode="hybrid",
        required_skills=[
            "React",
            "Python",
            "Docker",
            "Kubernetes",
        ],
        minimum_experience_years=3,
        required_education=[
            "Bachelor's degree in Computer Science",
        ],
        required_certifications=[
            "AWS certification",
        ],
        confidence=1.0,
    )

    result = match_candidate_profile_to_job_requirements(
        resume_profile=resume_profile,
        job_requirement_profile=job_profile,
        candidate_work_mode="hybrid",
    )

    assert result.skill_result.required_coverage == 0.25
    assert result.skill_result.score == 25.0

    assert result.overall_result.raw_score == 62.5
    assert result.overall_result.score == 49.0
    assert result.overall_result.required_skill_cap == 49.0
    assert result.overall_result.was_capped is True

    assert (
        result.recommendation_result.recommendation
        == "weak_match"
    )

    assert result.analysis_data.warnings == [
        (
            "Overall score was capped at 49.0 because "
            "required-skill coverage was insufficient."
        ),
    ]


def test_end_to_end_matcher_returns_insufficient_data_without_requirements(
) -> None:
    resume_profile = ResumeProfileData(
        full_name="Candidate",
        confidence=0.90,
    )

    job_profile = JobRequirementProfileData(
        job_title="General Opportunity",
        confidence=0.80,
    )

    result = match_candidate_profile_to_job_requirements(
        resume_profile=resume_profile,
        job_requirement_profile=job_profile,
    )

    assert result.overall_result.score == 0.0
    assert result.overall_result.available_weight == 0.0

    assert result.confidence_result.score == 0.0
    assert result.confidence_result.specified_weight == 0.0
    assert result.confidence_result.assessable_weight == 0.0

    assert result.confidence_result.unspecified_components == (
        "skills",
        "experience",
        "education",
        "certifications",
        "location",
        "work_mode",
    )

    assert (
        result.recommendation_result.recommendation
        == "insufficient_data"
    )


def test_end_to_end_matcher_is_deterministic() -> None:
    resume_profile = _build_matcher_resume_profile()
    job_profile = _build_matcher_job_profile()

    first_result = match_candidate_profile_to_job_requirements(
        resume_profile=resume_profile,
        job_requirement_profile=job_profile,
    )

    second_result = match_candidate_profile_to_job_requirements(
        resume_profile=resume_profile,
        job_requirement_profile=job_profile,
    )

    assert first_result == second_result

def _build_persistence_profiles() -> tuple[
    ResumeProfileResponse,
    JobRequirementProfileResponse,
]:
    now = datetime(
        2026,
        7,
        20,
        12,
        0,
        tzinfo=timezone.utc,
    )

    resume_data = ResumeProfileData(
        full_name="Harsha Vardhan",
        location="Bangalore",
        total_experience_months=30,
        skills=[
            "React.js",
            "PostgreSQL",
            "AWS",
        ],
        confidence=0.90,
    )

    job_data = JobRequirementProfileData(
        job_title="Frontend Engineer",
        location="Bengaluru, Karnataka",
        required_skills=[
            "React",
            "PostgreSQL",
        ],
        preferred_skills=[
            "AWS",
            "Docker",
        ],
        confidence=0.80,
    )

    resume_profile = ResumeProfileResponse(
        id=UUID(
            "11111111-1111-1111-1111-111111111111"
        ),
        resume_id=UUID(
            "22222222-2222-2222-2222-222222222222"
        ),
        profile_data=resume_data,
        parsing_status="completed",
        parsing_error=None,
        parser_version="resume-parser-v1",
        source_text_sha256="a" * 64,
        parsed_at=now,
        created_at=now,
        updated_at=now,
    )

    job_profile = JobRequirementProfileResponse(
        id=UUID(
            "33333333-3333-3333-3333-333333333333"
        ),
        job_id=UUID(
            "44444444-4444-4444-4444-444444444444"
        ),
        profile_data=job_data,
        parsing_status="completed",
        parsing_error=None,
        parser_version="job-parser-v1",
        source_description_sha256="b" * 64,
        parsed_at=now,
        created_at=now,
        updated_at=now,
    )

    return resume_profile, job_profile


def _build_persistence_computation(
    resume_profile: ResumeProfileResponse,
    job_profile: JobRequirementProfileResponse,
) -> CandidateJobMatchComputation:
    assert resume_profile.profile_data is not None
    assert job_profile.profile_data is not None

    return match_candidate_profile_to_job_requirements(
        resume_profile=resume_profile.profile_data,
        job_requirement_profile=job_profile.profile_data,
    )


def test_build_candidate_job_match_create_maps_complete_payload(
) -> None:
    resume_profile, job_profile = (
        _build_persistence_profiles()
    )
    computation = _build_persistence_computation(
        resume_profile,
        job_profile,
    )
    matched_at = datetime(
        2026,
        7,
        20,
        12,
        30,
        tzinfo=timezone.utc,
    )
    candidate_id = UUID(
        "55555555-5555-5555-5555-555555555555"
    )

    result = build_candidate_job_match_create(
        candidate_id=candidate_id,
        job_id=job_profile.job_id,
        resume_profile=resume_profile,
        job_requirement_profile=job_profile,
        computation=computation,
        matched_at=matched_at,
    )

    assert result.candidate_id == candidate_id
    assert result.job_id == job_profile.job_id
    assert result.resume_id == resume_profile.resume_id
    assert result.resume_profile_id == resume_profile.id
    assert (
        result.job_requirement_profile_id
        == job_profile.id
    )

    assert result.overall_score == 90.91
    assert result.skill_score == 90.0
    assert result.location_score == 100.0
    assert result.confidence_score == 85.0
    assert result.recommendation == "strong_match"

    assert result.scoring_version == SCORING_VERSION
    assert result.source_resume_text_sha256 == "a" * 64
    assert (
        result.source_resume_parser_version
        == "resume-parser-v1"
    )
    assert result.source_job_description_sha256 == "b" * 64
    assert (
        result.source_job_parser_version
        == "job-parser-v1"
    )
    assert result.matched_at == matched_at

    assert result.analysis_data.matched_required_skills == [
        "React",
        "PostgreSQL",
    ]
    assert result.analysis_data.missing_preferred_skills == [
        "Docker",
    ]


@pytest.mark.parametrize(
    "parsing_status",
    [
        "pending",
        "failed",
    ],
)
def test_build_candidate_job_match_create_requires_completed_resume(
    parsing_status: str,
) -> None:
    resume_profile, job_profile = (
        _build_persistence_profiles()
    )
    computation = _build_persistence_computation(
        resume_profile,
        job_profile,
    )

    invalid_resume_profile = resume_profile.model_copy(
        update={
            "parsing_status": parsing_status,
        }
    )

    with pytest.raises(
        ValueError,
        match="Resume profile must have completed parsing",
    ):
        build_candidate_job_match_create(
            candidate_id=UUID(
                "55555555-5555-5555-5555-555555555555"
            ),
            job_id=job_profile.job_id,
            resume_profile=invalid_resume_profile,
            job_requirement_profile=job_profile,
            computation=computation,
            matched_at=datetime.now(timezone.utc),
        )


def test_build_candidate_job_match_create_requires_resume_data(
) -> None:
    resume_profile, job_profile = (
        _build_persistence_profiles()
    )
    computation = _build_persistence_computation(
        resume_profile,
        job_profile,
    )

    invalid_resume_profile = resume_profile.model_copy(
        update={
            "profile_data": None,
        }
    )

    with pytest.raises(
        ValueError,
        match="Completed resume profile must contain profile data",
    ):
        build_candidate_job_match_create(
            candidate_id=UUID(
                "55555555-5555-5555-5555-555555555555"
            ),
            job_id=job_profile.job_id,
            resume_profile=invalid_resume_profile,
            job_requirement_profile=job_profile,
            computation=computation,
            matched_at=datetime.now(timezone.utc),
        )


@pytest.mark.parametrize(
    (
        "field_name",
        "expected_message",
    ),
    [
        (
            "parser_version",
            "Completed resume profile must contain a parser version",
        ),
        (
            "source_text_sha256",
            "Completed resume profile must contain a source-text hash",
        ),
    ],
)
def test_build_candidate_job_match_create_validates_resume_metadata(
    field_name: str,
    expected_message: str,
) -> None:
    resume_profile, job_profile = (
        _build_persistence_profiles()
    )
    computation = _build_persistence_computation(
        resume_profile,
        job_profile,
    )

    invalid_resume_profile = resume_profile.model_copy(
        update={
            field_name: None,
        }
    )

    with pytest.raises(
        ValueError,
        match=expected_message,
    ):
        build_candidate_job_match_create(
            candidate_id=UUID(
                "55555555-5555-5555-5555-555555555555"
            ),
            job_id=job_profile.job_id,
            resume_profile=invalid_resume_profile,
            job_requirement_profile=job_profile,
            computation=computation,
            matched_at=datetime.now(timezone.utc),
        )


@pytest.mark.parametrize(
    "parsing_status",
    [
        "pending",
        "failed",
    ],
)
def test_build_candidate_job_match_create_requires_completed_job_profile(
    parsing_status: str,
) -> None:
    resume_profile, job_profile = (
        _build_persistence_profiles()
    )
    computation = _build_persistence_computation(
        resume_profile,
        job_profile,
    )

    invalid_job_profile = job_profile.model_copy(
        update={
            "parsing_status": parsing_status,
        }
    )

    with pytest.raises(
        ValueError,
        match=(
            "Job requirement profile must have completed parsing"
        ),
    ):
        build_candidate_job_match_create(
            candidate_id=UUID(
                "55555555-5555-5555-5555-555555555555"
            ),
            job_id=job_profile.job_id,
            resume_profile=resume_profile,
            job_requirement_profile=invalid_job_profile,
            computation=computation,
            matched_at=datetime.now(timezone.utc),
        )


def test_build_candidate_job_match_create_requires_job_profile_data(
) -> None:
    resume_profile, job_profile = (
        _build_persistence_profiles()
    )
    computation = _build_persistence_computation(
        resume_profile,
        job_profile,
    )

    invalid_job_profile = job_profile.model_copy(
        update={
            "profile_data": None,
        }
    )

    with pytest.raises(
        ValueError,
        match=(
            "Completed job requirement profile must contain "
            "profile data"
        ),
    ):
        build_candidate_job_match_create(
            candidate_id=UUID(
                "55555555-5555-5555-5555-555555555555"
            ),
            job_id=job_profile.job_id,
            resume_profile=resume_profile,
            job_requirement_profile=invalid_job_profile,
            computation=computation,
            matched_at=datetime.now(timezone.utc),
        )


@pytest.mark.parametrize(
    (
        "field_name",
        "expected_message",
    ),
    [
        (
            "parser_version",
            (
                "Completed job requirement profile must "
                "contain a parser version"
            ),
        ),
        (
            "source_description_sha256",
            (
                "Completed job requirement profile must "
                "contain a source-description hash"
            ),
        ),
    ],
)
def test_build_candidate_job_match_create_validates_job_metadata(
    field_name: str,
    expected_message: str,
) -> None:
    resume_profile, job_profile = (
        _build_persistence_profiles()
    )
    computation = _build_persistence_computation(
        resume_profile,
        job_profile,
    )

    invalid_job_profile = job_profile.model_copy(
        update={
            field_name: None,
        }
    )

    with pytest.raises(
        ValueError,
        match=expected_message,
    ):
        build_candidate_job_match_create(
            candidate_id=UUID(
                "55555555-5555-5555-5555-555555555555"
            ),
            job_id=job_profile.job_id,
            resume_profile=resume_profile,
            job_requirement_profile=invalid_job_profile,
            computation=computation,
            matched_at=datetime.now(timezone.utc),
        )


def test_build_candidate_job_match_create_validates_job_id(
) -> None:
    resume_profile, job_profile = (
        _build_persistence_profiles()
    )
    computation = _build_persistence_computation(
        resume_profile,
        job_profile,
    )

    with pytest.raises(
        ValueError,
        match="job_id must match",
    ):
        build_candidate_job_match_create(
            candidate_id=UUID(
                "55555555-5555-5555-5555-555555555555"
            ),
            job_id=UUID(
                "66666666-6666-6666-6666-666666666666"
            ),
            resume_profile=resume_profile,
            job_requirement_profile=job_profile,
            computation=computation,
            matched_at=datetime.now(timezone.utc),
        )


def test_build_candidate_job_match_create_requires_aware_datetime(
) -> None:
    resume_profile, job_profile = (
        _build_persistence_profiles()
    )
    computation = _build_persistence_computation(
        resume_profile,
        job_profile,
    )

    with pytest.raises(
        ValueError,
        match="matched_at must be timezone-aware",
    ):
        build_candidate_job_match_create(
            candidate_id=UUID(
                "55555555-5555-5555-5555-555555555555"
            ),
            job_id=job_profile.job_id,
            resume_profile=resume_profile,
            job_requirement_profile=job_profile,
            computation=computation,
            matched_at=datetime(
                2026,
                7,
                20,
                12,
                30,
            ),
        )


def test_build_candidate_job_match_create_is_deterministic(
) -> None:
    resume_profile, job_profile = (
        _build_persistence_profiles()
    )
    computation = _build_persistence_computation(
        resume_profile,
        job_profile,
    )
    matched_at = datetime(
        2026,
        7,
        20,
        12,
        30,
        tzinfo=timezone.utc,
    )

    arguments = {
        "candidate_id": UUID(
            "55555555-5555-5555-5555-555555555555"
        ),
        "job_id": job_profile.job_id,
        "resume_profile": resume_profile,
        "job_requirement_profile": job_profile,
        "computation": computation,
        "matched_at": matched_at,
    }

    first_result = build_candidate_job_match_create(
        **arguments
    )
    second_result = build_candidate_job_match_create(
        **arguments
    )

    assert first_result == second_result