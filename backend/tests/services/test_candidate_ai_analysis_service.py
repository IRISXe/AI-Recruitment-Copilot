from contextlib import ExitStack
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import MagicMock, call, patch
from uuid import UUID, uuid4

import pytest
from fastapi import status
from sqlalchemy.orm import Session

from app.ai.candidate_analysis_prompt import (
    build_candidate_analysis_prompt,
)
from app.ai.fake_structured_llm import (
    FakeStructuredLLMClient,
)
from app.core.exceptions import AppException
from app.matching.candidate_job_matcher import (
    SCORING_VERSION,
)
from app.models.candidate import Candidate
from app.models.candidate_ai_analysis import (
    CandidateAIAnalysis,
)
from app.models.candidate_job_match import (
    CandidateJobMatch,
)
from app.models.job import Job
from app.models.job_requirement_profile import (
    JobRequirementProfile,
)
from app.models.resume import Resume
from app.models.resume_profile import ResumeProfile
from app.schemas.candidate_job_match import (
    CandidateJobMatchResponse,
)
from app.schemas.job_requirement_profile import (
    JobRequirementProfileData,
)
from app.schemas.resume_profile import ResumeProfileData
from app.services.candidate_ai_analysis_service import (
    generate_candidate_ai_analysis,
)


def _build_resume_profile_data() -> ResumeProfileData:
    return ResumeProfileData(
        full_name="AI Analysis Candidate",
        location="Hyderabad",
        current_role="Backend Developer",
        professional_summary=(
            "Backend developer with experience building "
            "production APIs and database integrations."
        ),
        total_experience_months=36,
        skills=[
            "Python",
            "FastAPI",
            "PostgreSQL",
        ],
        confidence=0.90,
    )


def _build_job_profile_data(
) -> JobRequirementProfileData:
    return JobRequirementProfileData(
        job_title="Backend Engineer",
        department="Engineering",
        location="Hyderabad",
        employment_type="full_time",
        work_mode="hybrid",
        seniority_level="mid",
        summary=(
            "Build and maintain production backend services."
        ),
        responsibilities=[
            "Develop scalable REST APIs.",
            "Maintain PostgreSQL integrations.",
        ],
        required_skills=[
            "Python",
            "FastAPI",
        ],
        preferred_skills=[
            "PostgreSQL",
            "Docker",
        ],
        minimum_experience_years=2,
        maximum_experience_years=5,
        required_education=[],
        preferred_education=[],
        required_certifications=[],
        preferred_certifications=[],
        keywords=[
            "REST API",
            "PostgreSQL",
        ],
        warnings=[],
        missing_sections=[],
        confidence=0.90,
    )


def _build_valid_ai_analysis_payload(
) -> dict[str, object]:
    return {
        "candidate_summary": (
            "The candidate has relevant backend development "
            "experience with Python, FastAPI and PostgreSQL."
        ),
        "job_summary": (
            "The role requires production backend engineering "
            "experience with API and database development."
        ),
        "match_explanation": (
            "The deterministic match indicates strong alignment "
            "with the required Python and FastAPI skills."
        ),
        "key_strengths": [
            {
                "title": "Required backend skills",
                "category": "skills",
                "explanation": (
                    "The verified profile contains both Python "
                    "and FastAPI experience."
                ),
                "evidence": [
                    {
                        "source": "resume_profile",
                        "field_path": (
                            "candidate_profile.skills"
                        ),
                        "summary": (
                            "Python and FastAPI are listed in "
                            "the verified Candidate profile."
                        ),
                    }
                ],
            }
        ],
        "missing_required_skills": [],
        "missing_preferred_skills": [
            "Docker",
        ],
        "gaps": [
            {
                "title": "Docker evidence unavailable",
                "category": "preferred_skill",
                "explanation": (
                    "The verified Candidate profile does not "
                    "contain Docker experience."
                ),
                "evidence": [
                    {
                        "source": "candidate_job_match",
                        "field_path": (
                            "deterministic_match.analysis_data."
                            "missing_preferred_skills"
                        ),
                        "summary": (
                            "Docker is identified as a missing "
                            "preferred skill."
                        ),
                    }
                ],
            }
        ],
        "risks_or_concerns": [],
        "recruiter_notes": [
            (
                "Verify the candidate's production API "
                "ownership during screening."
            ),
        ],
        "interview_questions": [
            {
                "question": (
                    "Describe the backend systems you have "
                    "owned in production."
                ),
                "category": "screening",
                "reason_for_asking": (
                    "This verifies the scope of the candidate's "
                    "production ownership."
                ),
                "expected_evidence": (
                    "The candidate should explain responsibilities, "
                    "users, deployments and measurable outcomes."
                ),
                "related_evidence": [],
            },
            {
                "question": (
                    "How would you structure a FastAPI service "
                    "that uses PostgreSQL?"
                ),
                "category": "technical",
                "reason_for_asking": (
                    "This tests practical understanding of the "
                    "role's required backend technologies."
                ),
                "expected_evidence": (
                    "The answer should cover routing, services, "
                    "repositories, transactions and validation."
                ),
                "related_evidence": [
                    {
                        "source": "resume_profile",
                        "field_path": (
                            "candidate_profile.skills"
                        ),
                        "summary": (
                            "FastAPI and PostgreSQL appear in "
                            "the verified profile."
                        ),
                    }
                ],
            },
            {
                "question": (
                    "Tell us about a production issue you "
                    "investigated with another team."
                ),
                "category": "behavioural",
                "reason_for_asking": (
                    "This evaluates collaboration and structured "
                    "problem-solving under operational pressure."
                ),
                "expected_evidence": (
                    "The candidate should describe the situation, "
                    "investigation, communication and outcome."
                ),
                "related_evidence": [],
            },
        ],
        "recommended_interview_focus_areas": [
            "Production API architecture",
            "PostgreSQL integration",
            "Docker exposure",
        ],
        "overall_recommendation": {
            "value": "consider_interview",
            "rationale": (
                "The verified data shows alignment with the "
                "required backend skills, while Docker should "
                "be explored during the interview."
            ),
            "human_review_required": True,
        },
        "limitations": [
            (
                "The analysis uses only the structured data "
                "provided by the application."
            ),
        ],
        "disclaimer": (
            "This analysis provides decision support only and "
            "must be reviewed by a human recruiter before any "
            "employment decision."
        ),
    }


def _build_completed_analysis_inputs() -> tuple[
    UUID,
    UUID,
    Candidate,
    Job,
    Resume,
    ResumeProfile,
    JobRequirementProfile,
    CandidateJobMatch,
    ResumeProfileData,
    JobRequirementProfileData,
]:
    candidate_id = uuid4()
    job_id = uuid4()
    resume_id = uuid4()
    resume_profile_id = uuid4()
    job_profile_id = uuid4()
    match_id = uuid4()

    now = datetime(
        2026,
        8,
        5,
        12,
        0,
        tzinfo=UTC,
    )

    candidate = MagicMock(spec=Candidate)
    candidate.id = candidate_id

    job = MagicMock(spec=Job)
    job.id = job_id

    primary_resume = MagicMock(spec=Resume)
    primary_resume.id = resume_id
    primary_resume.candidate_id = candidate_id
    primary_resume.is_primary = True

    resume_data = _build_resume_profile_data()

    resume_profile = MagicMock(spec=ResumeProfile)
    resume_profile.id = resume_profile_id
    resume_profile.resume_id = resume_id
    resume_profile.profile_data = resume_data.model_dump(
        mode="json"
    )
    resume_profile.parsing_status = "completed"
    resume_profile.parsing_error = None
    resume_profile.parser_version = "rule-based-v1"
    resume_profile.source_text_sha256 = "a" * 64
    resume_profile.parsed_at = now
    resume_profile.created_at = now
    resume_profile.updated_at = now

    job_data = _build_job_profile_data()

    job_profile = MagicMock(
        spec=JobRequirementProfile
    )
    job_profile.id = job_profile_id
    job_profile.job_id = job_id
    job_profile.profile_data = job_data.model_dump(
        mode="json"
    )
    job_profile.parsing_status = "completed"
    job_profile.parsing_error = None
    job_profile.parser_version = (
        "job-rule-based-v1"
    )
    job_profile.source_description_sha256 = "b" * 64
    job_profile.parsed_at = now
    job_profile.created_at = now
    job_profile.updated_at = now

    candidate_job_match = MagicMock(
        spec=CandidateJobMatch
    )
    candidate_job_match.id = match_id
    candidate_job_match.candidate_id = candidate_id
    candidate_job_match.job_id = job_id
    candidate_job_match.resume_id = resume_id
    candidate_job_match.resume_profile_id = (
        resume_profile_id
    )
    candidate_job_match.job_requirement_profile_id = (
        job_profile_id
    )
    candidate_job_match.overall_score = 82.50
    candidate_job_match.skill_score = 87.50
    candidate_job_match.experience_score = 100.00
    candidate_job_match.education_score = 50.00
    candidate_job_match.certification_score = 50.00
    candidate_job_match.location_score = 100.00
    candidate_job_match.work_mode_score = 100.00
    candidate_job_match.confidence_score = 90.00
    candidate_job_match.recommendation = "good_match"
    candidate_job_match.analysis_data = {
        "matched_required_skills": [
            "Python",
            "FastAPI",
        ],
        "missing_required_skills": [],
        "matched_preferred_skills": [
            "PostgreSQL",
        ],
        "missing_preferred_skills": [
            "Docker",
        ],
        "strengths": [
            "All required skills matched",
        ],
        "gaps": [
            "Docker was not found",
        ],
    }
    candidate_job_match.scoring_version = (
        SCORING_VERSION
    )
    candidate_job_match.source_resume_text_sha256 = (
        resume_profile.source_text_sha256
    )
    candidate_job_match.source_resume_parser_version = (
        resume_profile.parser_version
    )
    candidate_job_match.source_job_description_sha256 = (
        job_profile.source_description_sha256
    )
    candidate_job_match.source_job_parser_version = (
        job_profile.parser_version
    )
    candidate_job_match.matched_at = now
    candidate_job_match.created_at = now
    candidate_job_match.updated_at = now

    return (
        candidate_id,
        job_id,
        candidate,
        job,
        primary_resume,
        resume_profile,
        job_profile,
        candidate_job_match,
        resume_data,
        job_data,
    )


def _common_dependency_patches(
    *,
    candidate: Candidate,
    job: Job,
    primary_resume: Resume,
    resume_profile: ResumeProfile,
    job_profile: JobRequirementProfile,
    candidate_job_match: CandidateJobMatch,
) -> tuple[object, ...]:
    service_path = (
        "app.services.candidate_ai_analysis_service."
    )

    return (
        patch(
            f"{service_path}get_candidate_record",
            return_value=candidate,
        ),
        patch(
            f"{service_path}get_job_record",
            return_value=job,
        ),
        patch(
            f"{service_path}get_primary_resume_record",
            return_value=primary_resume,
        ),
        patch(
            f"{service_path}get_resume_profile_record",
            return_value=resume_profile,
        ),
        patch(
            f"{service_path}get_job_profile_record",
            return_value=job_profile,
        ),
        patch(
            f"{service_path}get_match_record",
            return_value=candidate_job_match,
        ),
    )


def test_generate_candidate_ai_analysis_creates_completed_analysis(
) -> None:
    session = MagicMock(spec=Session)

    (
        candidate_id,
        job_id,
        candidate,
        job,
        primary_resume,
        resume_profile,
        job_profile,
        candidate_job_match,
        _,
        _,
    ) = _build_completed_analysis_inputs()

    pending_analysis = MagicMock(
        spec=CandidateAIAnalysis
    )
    completed_analysis = MagicMock(
        spec=CandidateAIAnalysis
    )

    llm_client = FakeStructuredLLMClient(
        response_payload=(
            _build_valid_ai_analysis_payload()
        ),
        input_tokens=500,
        output_tokens=250,
        total_tokens=750,
        estimated_cost=Decimal("0.00125000"),
        processing_time_ms=125,
    )

    dependency_patches = _common_dependency_patches(
        candidate=candidate,
        job=job,
        primary_resume=primary_resume,
        resume_profile=resume_profile,
        job_profile=job_profile,
        candidate_job_match=candidate_job_match,
    )

    with ExitStack() as stack:
        for dependency_patch in dependency_patches:
            stack.enter_context(dependency_patch)

        stack.enter_context(
            patch(
                "app.services."
                "candidate_ai_analysis_service."
                "get_analysis_record",
                return_value=None,
            )
        )

        create_analysis = stack.enter_context(
            patch(
                "app.services."
                "candidate_ai_analysis_service."
                "create_analysis_record",
                return_value=pending_analysis,
            )
        )

        update_analysis = stack.enter_context(
            patch(
                "app.services."
                "candidate_ai_analysis_service."
                "update_analysis_record",
                return_value=completed_analysis,
            )
        )

        result = generate_candidate_ai_analysis(
            session=session,
            candidate_id=candidate_id,
            job_id=job_id,
            llm_client=llm_client,
        )

    create_analysis.assert_called_once()

    create_arguments = create_analysis.call_args.kwargs

    assert create_arguments["candidate_id"] == candidate_id
    assert create_arguments["job_id"] == job_id
    assert create_arguments["resume_id"] == (
        primary_resume.id
    )
    assert (
        create_arguments["candidate_job_match_id"]
        == candidate_job_match.id
    )
    assert create_arguments["provider"] == "fake"
    assert (
        create_arguments["model_name"]
        == "fake-structured-llm-v1"
    )
    assert (
        create_arguments["prompt_version"]
        == "candidate-analysis-v1"
    )
    assert (
        len(
            create_arguments[
                "input_fingerprint_sha256"
            ]
        )
        == 64
    )

    update_analysis.assert_called_once()

    update_arguments = update_analysis.call_args.kwargs

    assert update_arguments["analysis"] is pending_analysis
    assert update_arguments["status"] == "completed"
    assert update_arguments["provider"] == "fake"
    assert (
        update_arguments["model_name"]
        == "fake-structured-llm-v1"
    )
    assert update_arguments["input_tokens"] == 500
    assert update_arguments["output_tokens"] == 250
    assert update_arguments["total_tokens"] == 750
    assert update_arguments["estimated_cost"] == Decimal(
        "0.00125000"
    )
    assert update_arguments["processing_time_ms"] == 125
    assert update_arguments["error_code"] is None
    assert update_arguments["error_message"] is None
    assert update_arguments["generated_at"] is not None
    assert isinstance(
        update_arguments["analysis_data"],
        dict,
    )

    assert llm_client.call_count == 1
    assert llm_client.last_request is not None
    assert (
        llm_client.last_request.response_model_name
        == "CandidateAIAnalysisData"
    )

    assert session.commit.call_count == 2
    assert session.refresh.call_args_list == [
        call(pending_analysis),
        call(completed_analysis),
    ]
    session.rollback.assert_not_called()

    assert result is completed_analysis


def test_generate_candidate_ai_analysis_returns_current_analysis(
) -> None:
    session = MagicMock(spec=Session)

    (
        candidate_id,
        job_id,
        candidate,
        job,
        primary_resume,
        resume_profile,
        job_profile,
        candidate_job_match,
        resume_data,
        job_data,
    ) = _build_completed_analysis_inputs()

    match_data = CandidateJobMatchResponse.model_validate(
        candidate_job_match
    )

    prompt = build_candidate_analysis_prompt(
        resume_profile=resume_data,
        job_requirement_profile=job_data,
        candidate_job_match=match_data,
    )

    existing_analysis = MagicMock(
        spec=CandidateAIAnalysis
    )
    existing_analysis.status = "completed"
    existing_analysis.analysis_data = (
        _build_valid_ai_analysis_payload()
    )
    existing_analysis.generated_at = datetime.now(UTC)
    existing_analysis.resume_id = primary_resume.id
    existing_analysis.candidate_job_match_id = (
        candidate_job_match.id
    )
    existing_analysis.provider = "fake"
    existing_analysis.model_name = (
        "fake-structured-llm-v1"
    )
    existing_analysis.prompt_version = (
        prompt.prompt_version
    )
    existing_analysis.input_fingerprint_sha256 = (
        prompt.input_fingerprint_sha256
    )
    existing_analysis.source_match_updated_at = (
        candidate_job_match.updated_at
    )
    existing_analysis.source_scoring_version = (
        candidate_job_match.scoring_version
    )
    existing_analysis.source_resume_profile_hash = (
        resume_profile.source_text_sha256
    )
    existing_analysis.source_job_profile_hash = (
        job_profile.source_description_sha256
    )

    llm_client = FakeStructuredLLMClient(
        response_payload=(
            _build_valid_ai_analysis_payload()
        )
    )

    dependency_patches = _common_dependency_patches(
        candidate=candidate,
        job=job,
        primary_resume=primary_resume,
        resume_profile=resume_profile,
        job_profile=job_profile,
        candidate_job_match=candidate_job_match,
    )

    with ExitStack() as stack:
        for dependency_patch in dependency_patches:
            stack.enter_context(dependency_patch)

        stack.enter_context(
            patch(
                "app.services."
                "candidate_ai_analysis_service."
                "get_analysis_record",
                return_value=existing_analysis,
            )
        )

        create_analysis = stack.enter_context(
            patch(
                "app.services."
                "candidate_ai_analysis_service."
                "create_analysis_record",
            )
        )

        update_analysis = stack.enter_context(
            patch(
                "app.services."
                "candidate_ai_analysis_service."
                "update_analysis_record",
            )
        )

        result = generate_candidate_ai_analysis(
            session=session,
            candidate_id=candidate_id,
            job_id=job_id,
            llm_client=llm_client,
        )

    create_analysis.assert_not_called()
    update_analysis.assert_not_called()

    assert llm_client.call_count == 0
    session.commit.assert_not_called()
    session.refresh.assert_not_called()
    session.rollback.assert_not_called()

    assert result is existing_analysis


def test_generate_candidate_ai_analysis_persists_provider_failure(
) -> None:
    session = MagicMock(spec=Session)

    (
        candidate_id,
        job_id,
        candidate,
        job,
        primary_resume,
        resume_profile,
        job_profile,
        candidate_job_match,
        _,
        _,
    ) = _build_completed_analysis_inputs()

    pending_analysis = MagicMock(
        spec=CandidateAIAnalysis
    )
    failed_analysis = MagicMock(
        spec=CandidateAIAnalysis
    )

    llm_client = FakeStructuredLLMClient(
        failure_mode="timeout",
    )

    dependency_patches = _common_dependency_patches(
        candidate=candidate,
        job=job,
        primary_resume=primary_resume,
        resume_profile=resume_profile,
        job_profile=job_profile,
        candidate_job_match=candidate_job_match,
    )

    with ExitStack() as stack:
        for dependency_patch in dependency_patches:
            stack.enter_context(dependency_patch)

        stack.enter_context(
            patch(
                "app.services."
                "candidate_ai_analysis_service."
                "get_analysis_record",
                return_value=None,
            )
        )

        stack.enter_context(
            patch(
                "app.services."
                "candidate_ai_analysis_service."
                "create_analysis_record",
                return_value=pending_analysis,
            )
        )

        update_analysis = stack.enter_context(
            patch(
                "app.services."
                "candidate_ai_analysis_service."
                "update_analysis_record",
                return_value=failed_analysis,
            )
        )

        with pytest.raises(AppException) as exc_info:
            generate_candidate_ai_analysis(
                session=session,
                candidate_id=candidate_id,
                job_id=job_id,
                llm_client=llm_client,
            )

    exception = exc_info.value

    assert (
        exception.status_code
        == status.HTTP_503_SERVICE_UNAVAILABLE
    )
    assert exception.code == "structured_llm_timeout"
    assert exception.message == (
        "The AI Candidate analysis could not be generated."
    )

    update_analysis.assert_called_once()

    update_arguments = update_analysis.call_args.kwargs

    assert update_arguments["analysis"] is pending_analysis
    assert update_arguments["status"] == "failed"
    assert update_arguments["analysis_data"] is None
    assert (
        update_arguments["error_code"]
        == "structured_llm_timeout"
    )
    assert "timed out" in (
        update_arguments["error_message"]
    )
    assert update_arguments["generated_at"] is not None

    assert llm_client.call_count == 1
    assert session.commit.call_count == 2
    assert session.refresh.call_args_list == [
        call(pending_analysis),
        call(failed_analysis),
    ]
    session.rollback.assert_not_called()