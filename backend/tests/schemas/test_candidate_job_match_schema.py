from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.candidate_job_match import (
    CandidateJobMatchAnalysisData,
    CandidateJobMatchCreate,
    CandidateJobMatchResponse,
)


def build_valid_match_data() -> dict[str, object]:
    return {
        "candidate_id": uuid4(),
        "job_id": uuid4(),
        "resume_id": uuid4(),
        "resume_profile_id": uuid4(),
        "job_requirement_profile_id": uuid4(),
        "overall_score": 82.5,
        "skill_score": 90.0,
        "experience_score": 80.0,
        "education_score": 75.0,
        "certification_score": 60.0,
        "location_score": 100.0,
        "work_mode_score": 100.0,
        "confidence_score": 85.0,
        "recommendation": "good_match",
        "analysis_data": {
            "matched_required_skills": [
                "Python",
                "FastAPI",
            ],
            "missing_required_skills": [
                "Docker",
            ],
            "strengths": [
                "Strong required skill coverage",
            ],
            "gaps": [
                "Docker experience was not found",
            ],
        },
        "scoring_version": "candidate-job-rule-based-v1",
        "source_resume_text_sha256": "a" * 64,
        "source_resume_parser_version": "rule-based-v1",
        "source_job_description_sha256": "b" * 64,
        "source_job_parser_version": "job-rule-based-v1",
        "matched_at": datetime.now(UTC),
    }


def test_match_create_accepts_valid_values() -> None:
    match = CandidateJobMatchCreate(
        **build_valid_match_data()
    )

    assert match.overall_score == 82.5
    assert match.skill_score == 90.0
    assert match.recommendation == "good_match"
    assert match.analysis_data.matched_required_skills == [
        "Python",
        "FastAPI",
    ]


@pytest.mark.parametrize(
    "recommendation",
    [
        "strong_match",
        "good_match",
        "partial_match",
        "weak_match",
        "insufficient_data",
    ],
)
def test_match_create_accepts_valid_recommendations(
    recommendation: str,
) -> None:
    match_data = build_valid_match_data()
    match_data["recommendation"] = recommendation

    match = CandidateJobMatchCreate(**match_data)

    assert match.recommendation == recommendation


@pytest.mark.parametrize(
    "score",
    [
        0.0,
        100.0,
    ],
)
def test_match_create_accepts_score_boundaries(
    score: float,
) -> None:
    match_data = build_valid_match_data()

    for field_name in (
        "overall_score",
        "skill_score",
        "experience_score",
        "education_score",
        "certification_score",
        "location_score",
        "work_mode_score",
        "confidence_score",
    ):
        match_data[field_name] = score

    match = CandidateJobMatchCreate(**match_data)

    assert match.overall_score == score
    assert match.skill_score == score
    assert match.experience_score == score
    assert match.education_score == score
    assert match.certification_score == score
    assert match.location_score == score
    assert match.work_mode_score == score
    assert match.confidence_score == score


@pytest.mark.parametrize(
    ("field_name", "invalid_value"),
    [
        ("overall_score", -0.01),
        ("overall_score", 100.01),
        ("skill_score", -0.01),
        ("skill_score", 100.01),
        ("experience_score", -0.01),
        ("experience_score", 100.01),
        ("education_score", -0.01),
        ("education_score", 100.01),
        ("certification_score", -0.01),
        ("certification_score", 100.01),
        ("location_score", -0.01),
        ("location_score", 100.01),
        ("work_mode_score", -0.01),
        ("work_mode_score", 100.01),
        ("confidence_score", -0.01),
        ("confidence_score", 100.01),
    ],
)
def test_match_create_rejects_invalid_scores(
    field_name: str,
    invalid_value: float,
) -> None:
    match_data = build_valid_match_data()
    match_data[field_name] = invalid_value

    with pytest.raises(ValidationError):
        CandidateJobMatchCreate(**match_data)


def test_match_create_rejects_invalid_recommendation() -> None:
    match_data = build_valid_match_data()
    match_data["recommendation"] = "perfect_match"

    with pytest.raises(ValidationError):
        CandidateJobMatchCreate(**match_data)


def test_analysis_normalizes_and_deduplicates_lists() -> None:
    analysis = CandidateJobMatchAnalysisData(
        matched_required_skills=[
            "Python",
            " python ",
            "",
            "FastAPI",
            "FASTAPI",
        ],
        strengths=[
            "Strong skills",
            " strong skills ",
        ],
        warnings=[
            "",
            "Incomplete education data",
            " incomplete education data ",
        ],
    )

    assert analysis.matched_required_skills == [
        "Python",
        "FastAPI",
    ]
    assert analysis.strengths == [
        "Strong skills",
    ]
    assert analysis.warnings == [
        "Incomplete education data",
    ]


def test_match_response_serializes_attribute_object() -> None:
    now = datetime.now(UTC)
    match_data = build_valid_match_data()

    orm_like_match = SimpleNamespace(
        id=uuid4(),
        candidate_id=match_data["candidate_id"],
        job_id=match_data["job_id"],
        resume_id=match_data["resume_id"],
        resume_profile_id=match_data["resume_profile_id"],
        job_requirement_profile_id=(
            match_data["job_requirement_profile_id"]
        ),
        overall_score=82.5,
        skill_score=90.0,
        experience_score=80.0,
        education_score=75.0,
        certification_score=60.0,
        location_score=100.0,
        work_mode_score=100.0,
        confidence_score=85.0,
        recommendation="good_match",
        analysis_data={
            "matched_required_skills": [
                "Python",
                "FastAPI",
            ],
            "missing_required_skills": [
                "Docker",
            ],
        },
        scoring_version="candidate-job-rule-based-v1",
        source_resume_text_sha256="a" * 64,
        source_resume_parser_version="rule-based-v1",
        source_job_description_sha256="b" * 64,
        source_job_parser_version="job-rule-based-v1",
        matched_at=now,
        created_at=now,
        updated_at=now,
    )

    response = CandidateJobMatchResponse.model_validate(
        orm_like_match
    )

    assert response.id == orm_like_match.id
    assert response.candidate_id == match_data["candidate_id"]
    assert response.job_id == match_data["job_id"]
    assert response.overall_score == 82.5
    assert response.recommendation == "good_match"
    assert response.analysis_data.matched_required_skills == [
        "Python",
        "FastAPI",
    ]
    assert response.analysis_data.missing_required_skills == [
        "Docker",
    ]