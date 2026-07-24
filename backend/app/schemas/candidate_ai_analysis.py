from typing import Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


CandidateAIAnalysisEvidenceSource = Literal[
    "resume_profile",
    "job_requirement_profile",
    "candidate_job_match",
]

CandidateAIAnalysisStrengthCategory = Literal[
    "skills",
    "experience",
    "education",
    "certifications",
    "projects",
    "location",
    "work_mode",
    "other",
]

CandidateAIAnalysisGapCategory = Literal[
    "required_skill",
    "preferred_skill",
    "experience",
    "education",
    "certification",
    "location",
    "work_mode",
    "missing_data",
    "other",
]

CandidateAIAnalysisRiskSeverity = Literal[
    "low",
    "medium",
    "high",
]

CandidateAIInterviewQuestionCategory = Literal[
    "screening",
    "technical",
    "behavioural",
]

CandidateAIAnalysisRecommendationValue = Literal[
    "recommend_interview",
    "consider_interview",
    "additional_screening_required",
    "insufficient_data",
]


class CandidateAIAnalysisSchemaBase(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )


class CandidateAIAnalysisEvidence(
    CandidateAIAnalysisSchemaBase
):
    source: CandidateAIAnalysisEvidenceSource

    field_path: str = Field(
        min_length=1,
        max_length=200,
    )

    summary: str = Field(
        min_length=3,
        max_length=1000,
    )


class CandidateAIAnalysisStrength(
    CandidateAIAnalysisSchemaBase
):
    title: str = Field(
        min_length=3,
        max_length=200,
    )

    category: CandidateAIAnalysisStrengthCategory

    explanation: str = Field(
        min_length=10,
        max_length=2000,
    )

    evidence: list[CandidateAIAnalysisEvidence] = Field(
        min_length=1,
        max_length=20,
    )


class CandidateAIAnalysisGap(
    CandidateAIAnalysisSchemaBase
):
    title: str = Field(
        min_length=3,
        max_length=200,
    )

    category: CandidateAIAnalysisGapCategory

    explanation: str = Field(
        min_length=10,
        max_length=2000,
    )

    evidence: list[CandidateAIAnalysisEvidence] = Field(
        min_length=1,
        max_length=20,
    )


class CandidateAIAnalysisRisk(
    CandidateAIAnalysisSchemaBase
):
    title: str = Field(
        min_length=3,
        max_length=200,
    )

    severity: CandidateAIAnalysisRiskSeverity

    explanation: str = Field(
        min_length=10,
        max_length=2000,
    )

    mitigation_or_follow_up: str = Field(
        min_length=10,
        max_length=2000,
    )

    evidence: list[CandidateAIAnalysisEvidence] = Field(
        min_length=1,
        max_length=20,
    )


class CandidateAIInterviewQuestion(
    CandidateAIAnalysisSchemaBase
):
    question: str = Field(
        min_length=10,
        max_length=1000,
    )

    category: CandidateAIInterviewQuestionCategory

    reason_for_asking: str = Field(
        min_length=10,
        max_length=1500,
    )

    expected_evidence: str = Field(
        min_length=10,
        max_length=1500,
    )

    related_evidence: list[
        CandidateAIAnalysisEvidence
    ] = Field(
        default_factory=list,
        max_length=20,
    )


class CandidateAIAnalysisRecommendation(
    CandidateAIAnalysisSchemaBase
):
    value: CandidateAIAnalysisRecommendationValue

    rationale: str = Field(
        min_length=20,
        max_length=3000,
    )

    human_review_required: Literal[True] = True


class CandidateAIAnalysisData(
    CandidateAIAnalysisSchemaBase
):
    candidate_summary: str = Field(
        min_length=20,
        max_length=4000,
    )

    job_summary: str = Field(
        min_length=20,
        max_length=4000,
    )

    match_explanation: str = Field(
        min_length=20,
        max_length=5000,
    )

    key_strengths: list[
        CandidateAIAnalysisStrength
    ] = Field(
        min_length=1,
        max_length=30,
    )

    missing_required_skills: list[str] = Field(
        default_factory=list,
        max_length=100,
    )

    missing_preferred_skills: list[str] = Field(
        default_factory=list,
        max_length=100,
    )

    gaps: list[CandidateAIAnalysisGap] = Field(
        default_factory=list,
        max_length=30,
    )

    risks_or_concerns: list[
        CandidateAIAnalysisRisk
    ] = Field(
        default_factory=list,
        max_length=30,
    )

    recruiter_notes: list[str] = Field(
        min_length=1,
        max_length=30,
    )

    interview_questions: list[
        CandidateAIInterviewQuestion
    ] = Field(
        min_length=3,
        max_length=50,
    )

    recommended_interview_focus_areas: list[str] = Field(
        min_length=1,
        max_length=30,
    )

    overall_recommendation: (
        CandidateAIAnalysisRecommendation
    )

    limitations: list[str] = Field(
        min_length=1,
        max_length=30,
    )

    disclaimer: str = Field(
        min_length=20,
        max_length=1000,
    )

    @field_validator(
        "missing_required_skills",
        "missing_preferred_skills",
        "recruiter_notes",
        "recommended_interview_focus_areas",
        "limitations",
    )
    @classmethod
    def normalize_string_lists(
        cls,
        values: list[str],
    ) -> list[str]:
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

    @model_validator(mode="after")
    def validate_interview_question_categories(
        self,
    ) -> Self:
        required_categories = {
            "screening",
            "technical",
            "behavioural",
        }

        present_categories = {
            question.category
            for question in self.interview_questions
        }

        missing_categories = (
            required_categories - present_categories
        )

        if missing_categories:
            missing_values = ", ".join(
                sorted(missing_categories)
            )

            raise ValueError(
                "interview_questions must include at least "
                "one question for each category. Missing: "
                f"{missing_values}."
            )

        normalized_questions: set[str] = set()

        for question in self.interview_questions:
            comparison_value = (
                question.question.strip().casefold()
            )

            if comparison_value in normalized_questions:
                raise ValueError(
                    "interview_questions must not contain "
                    "duplicate questions."
                )

            normalized_questions.add(comparison_value)

        return self