from copy import deepcopy

import pytest
from pydantic import ValidationError

from app.schemas.candidate_ai_analysis import (
    CandidateAIAnalysisData,
)


def _build_valid_payload() -> dict[str, object]:
    return {
        "candidate_summary": (
            "The candidate has relevant frontend development "
            "experience with React, JavaScript and API "
            "integration."
        ),
        "job_summary": (
            "The role requires frontend engineering experience "
            "with React, TypeScript and production API "
            "integration."
        ),
        "match_explanation": (
            "The deterministic match shows strong alignment in "
            "frontend skills, with some remaining areas that "
            "should be verified during the interview."
        ),
        "key_strengths": [
            {
                "title": "Relevant React experience",
                "category": "skills",
                "explanation": (
                    "The candidate's verified profile includes "
                    "React experience required by the job."
                ),
                "evidence": [
                    {
                        "source": "candidate_job_match",
                        "field_path": (
                            "analysis_data."
                            "matched_required_skills"
                        ),
                        "summary": (
                            "React appears in the matched "
                            "required skills."
                        ),
                    }
                ],
            }
        ],
        "missing_required_skills": [
            "Python",
        ],
        "missing_preferred_skills": [
            "Next.js",
        ],
        "gaps": [
            {
                "title": "Python evidence unavailable",
                "category": "required_skill",
                "explanation": (
                    "The structured Resume profile does not "
                    "provide verified Python experience."
                ),
                "evidence": [
                    {
                        "source": "candidate_job_match",
                        "field_path": (
                            "analysis_data."
                            "missing_required_skills"
                        ),
                        "summary": (
                            "Python is listed as a missing "
                            "required skill."
                        ),
                    }
                ],
            }
        ],
        "risks_or_concerns": [
            {
                "title": "Backend depth requires verification",
                "severity": "medium",
                "explanation": (
                    "The available structured data contains "
                    "limited evidence of production backend "
                    "ownership."
                ),
                "mitigation_or_follow_up": (
                    "Ask the candidate to explain a backend "
                    "feature they designed, tested and deployed."
                ),
                "evidence": [
                    {
                        "source": "resume_profile",
                        "field_path": "profile_data.skills",
                        "summary": (
                            "The profile contains stronger "
                            "frontend than backend evidence."
                        ),
                    }
                ],
            }
        ],
        "recruiter_notes": [
            (
                "Confirm the candidate's practical Python "
                "experience before proceeding."
            )
        ],
        "interview_questions": [
            {
                "question": (
                    "Can you summarize the projects most "
                    "relevant to this role?"
                ),
                "category": "screening",
                "reason_for_asking": (
                    "This verifies which experience the "
                    "candidate considers directly relevant."
                ),
                "expected_evidence": (
                    "A clear explanation of responsibilities, "
                    "scope and measurable project outcomes."
                ),
                "related_evidence": [],
            },
            {
                "question": (
                    "How would you structure API state "
                    "management in a React application?"
                ),
                "category": "technical",
                "reason_for_asking": (
                    "The role requires production React and "
                    "API integration experience."
                ),
                "expected_evidence": (
                    "Discussion of loading, error, caching and "
                    "server-state synchronization concerns."
                ),
                "related_evidence": [
                    {
                        "source": "resume_profile",
                        "field_path": "profile_data.skills",
                        "summary": (
                            "React and API integration are "
                            "present in the structured profile."
                        ),
                    }
                ],
            },
            {
                "question": (
                    "Describe a time you handled an unexpected "
                    "production issue."
                ),
                "category": "behavioural",
                "reason_for_asking": (
                    "This evaluates ownership, communication "
                    "and structured problem-solving."
                ),
                "expected_evidence": (
                    "A specific situation, action, outcome and "
                    "lesson learned."
                ),
                "related_evidence": [],
            },
        ],
        "recommended_interview_focus_areas": [
            "Python fundamentals",
            "React architecture",
            "API error handling",
        ],
        "overall_recommendation": {
            "value": "consider_interview",
            "rationale": (
                "The candidate has relevant frontend strengths, "
                "but required backend skills should be verified "
                "through structured screening."
            ),
            "human_review_required": True,
        },
        "limitations": [
            (
                "The analysis is limited to the structured "
                "Resume, job profile and deterministic match."
            )
        ],
        "disclaimer": (
            "This analysis provides decision support and must "
            "be reviewed by a human recruiter."
        ),
    }


def test_candidate_ai_analysis_accepts_valid_data() -> None:
    analysis = CandidateAIAnalysisData.model_validate(
        _build_valid_payload()
    )

    assert (
        analysis.overall_recommendation.value
        == "consider_interview"
    )
    assert len(analysis.interview_questions) == 3


def test_candidate_ai_analysis_rejects_invalid_recommendation(
) -> None:
    payload = _build_valid_payload()

    payload["overall_recommendation"] = {
        "value": "reject_candidate",
        "rationale": (
            "This value must not be accepted because the AI "
            "cannot make an automatic hiring decision."
        ),
        "human_review_required": True,
    }

    with pytest.raises(ValidationError):
        CandidateAIAnalysisData.model_validate(payload)


def test_candidate_ai_analysis_requires_strengths() -> None:
    payload = _build_valid_payload()
    payload["key_strengths"] = []

    with pytest.raises(ValidationError):
        CandidateAIAnalysisData.model_validate(payload)


def test_candidate_ai_analysis_requires_all_question_categories(
) -> None:
    payload = deepcopy(_build_valid_payload())

    questions = payload["interview_questions"]

    assert isinstance(questions, list)

    behavioural_question = questions[2]

    assert isinstance(behavioural_question, dict)

    behavioural_question["category"] = "technical"

    with pytest.raises(
        ValidationError,
        match="Missing: behavioural",
    ):
        CandidateAIAnalysisData.model_validate(payload)


def test_candidate_ai_analysis_rejects_short_summary() -> None:
    payload = _build_valid_payload()
    payload["candidate_summary"] = "Too short"

    with pytest.raises(ValidationError):
        CandidateAIAnalysisData.model_validate(payload)


def test_candidate_ai_analysis_rejects_extra_fields() -> None:
    payload = _build_valid_payload()
    payload["automatic_hiring_decision"] = "hire"

    with pytest.raises(ValidationError):
        CandidateAIAnalysisData.model_validate(payload)


def test_candidate_ai_analysis_rejects_nested_extra_fields(
) -> None:
    payload = deepcopy(_build_valid_payload())

    strengths = payload["key_strengths"]

    assert isinstance(strengths, list)

    first_strength = strengths[0]

    assert isinstance(first_strength, dict)

    evidence = first_strength["evidence"]

    assert isinstance(evidence, list)

    first_evidence = evidence[0]

    assert isinstance(first_evidence, dict)

    first_evidence["unsupported_field"] = "unexpected"

    with pytest.raises(ValidationError):
        CandidateAIAnalysisData.model_validate(payload)


def test_candidate_ai_analysis_normalizes_string_lists(
) -> None:
    payload = _build_valid_payload()

    payload["missing_required_skills"] = [
        " Python ",
        "python",
        "",
        "FastAPI",
    ]

    analysis = CandidateAIAnalysisData.model_validate(
        payload
    )

    assert analysis.missing_required_skills == [
        "Python",
        "FastAPI",
    ]


def test_candidate_ai_analysis_rejects_duplicate_questions(
) -> None:
    payload = deepcopy(_build_valid_payload())

    questions = payload["interview_questions"]

    assert isinstance(questions, list)

    screening_question = questions[0]
    technical_question = questions[1]

    assert isinstance(screening_question, dict)
    assert isinstance(technical_question, dict)

    technical_question["question"] = (
        screening_question["question"]
    )

    with pytest.raises(
        ValidationError,
        match="duplicate questions",
    ):
        CandidateAIAnalysisData.model_validate(payload)