import json
from datetime import UTC, datetime
from uuid import UUID

from app.ai.candidate_analysis_prompt import (
    CANDIDATE_ANALYSIS_PROMPT_VERSION,
    build_candidate_analysis_input_payload,
    build_candidate_analysis_prompt,
    calculate_candidate_analysis_input_fingerprint,
)
from app.schemas.candidate_job_match import (
    CandidateJobMatchAnalysisData,
    CandidateJobMatchResponse,
)
from app.schemas.job_requirement_profile import (
    JobRequirementProfileData,
)
from app.schemas.resume_profile import (
    ResumeCertificationEntry,
    ResumeEducationEntry,
    ResumeExperienceEntry,
    ResumeProfileData,
    ResumeProjectEntry,
)


def _build_resume_profile() -> ResumeProfileData:
    return ResumeProfileData(
        full_name="Harsha Vardhan",
        email="harsha.private@example.com",
        phone="+91 9999999999",
        location="Hyderabad",
        current_role="Frontend Developer",
        professional_summary=(
            "Frontend developer experienced in React and "
            "production API integration."
        ),
        total_experience_months=30,
        skills=[
            "React",
            "TypeScript",
            "PostgreSQL",
        ],
        education=[
            ResumeEducationEntry(
                institution="Prestige University",
                degree="Bachelor of Technology",
                field_of_study="Computer Science",
                start_date="2020",
                end_date="2024",
                description=(
                    "Studied software engineering fundamentals."
                ),
            )
        ],
        work_experience=[
            ResumeExperienceEntry(
                company="Famous Technology Company",
                role="Frontend Developer",
                location="Private Office Location",
                start_date="2024-01",
                end_date=None,
                is_current=True,
                highlights=[
                    "Developed reusable React components.",
                    "Integrated REST APIs.",
                ],
            )
        ],
        projects=[
            ResumeProjectEntry(
                name="AI Recruitment Copilot",
                description=(
                    "Built a structured recruitment platform."
                ),
                technologies=[
                    "React",
                    "FastAPI",
                    "PostgreSQL",
                ],
                url="https://private-project.example.com",
                highlights=[
                    "Implemented deterministic matching.",
                ],
            )
        ],
        certifications=[
            ResumeCertificationEntry(
                name="AWS Cloud Practitioner",
                issuer="Amazon Web Services",
                issue_date="2025-01",
                expiry_date="2028-01",
                credential_id="PRIVATE-CREDENTIAL-ID",
                credential_url=(
                    "https://private-credential.example.com"
                ),
            )
        ],
        languages=[
            "Telugu",
            "English",
        ],
        warnings=[
            "Work-mode preference is unavailable.",
        ],
        missing_sections=[
            "languages",
        ],
        confidence=0.90,
    )


def _build_job_profile(
) -> JobRequirementProfileData:
    return JobRequirementProfileData(
        job_title="Full-Stack AI Engineer",
        department="Engineering",
        location="Hyderabad",
        employment_type="full_time",
        work_mode="hybrid",
        seniority_level="mid",
        summary=(
            "Build production AI-powered web applications."
        ),
        responsibilities=[
            "Develop frontend and backend features.",
            "Integrate structured LLM workflows.",
        ],
        required_skills=[
            "React",
            "Python",
            "FastAPI",
        ],
        preferred_skills=[
            "PostgreSQL",
            "AWS",
        ],
        minimum_experience_years=2,
        maximum_experience_years=4,
        required_education=[
            "Bachelor's degree in Computer Science",
        ],
        preferred_education=[],
        required_certifications=[],
        preferred_certifications=[
            "AWS certification",
        ],
        keywords=[
            "structured output",
            "REST API",
        ],
        warnings=[],
        missing_sections=[],
        confidence=0.85,
    )


def _build_candidate_job_match(
) -> CandidateJobMatchResponse:
    now = datetime(
        2026,
        7,
        24,
        12,
        0,
        tzinfo=UTC,
    )

    return CandidateJobMatchResponse(
        id=UUID(
            "11111111-1111-1111-1111-111111111111"
        ),
        candidate_id=UUID(
            "22222222-2222-2222-2222-222222222222"
        ),
        job_id=UUID(
            "33333333-3333-3333-3333-333333333333"
        ),
        resume_id=UUID(
            "44444444-4444-4444-4444-444444444444"
        ),
        resume_profile_id=UUID(
            "55555555-5555-5555-5555-555555555555"
        ),
        job_requirement_profile_id=UUID(
            "66666666-6666-6666-6666-666666666666"
        ),
        overall_score=72.50,
        skill_score=65.00,
        experience_score=100.00,
        education_score=100.00,
        certification_score=50.00,
        location_score=100.00,
        work_mode_score=0.00,
        confidence_score=82.00,
        recommendation="good_match",
        analysis_data=CandidateJobMatchAnalysisData(
            matched_required_skills=[
                "React",
            ],
            missing_required_skills=[
                "Python",
                "FastAPI",
            ],
            matched_preferred_skills=[
                "PostgreSQL",
            ],
            missing_preferred_skills=[
                "AWS",
            ],
            experience_analysis=(
                "The candidate meets the minimum experience."
            ),
            education_analysis=(
                "The candidate meets the education requirement."
            ),
            certification_analysis=(
                "The preferred AWS certification is present."
            ),
            location_analysis=(
                "The candidate location matches the job."
            ),
            work_mode_analysis=(
                "Candidate work-mode preference is unavailable."
            ),
            strengths=[
                "Relevant React experience.",
            ],
            gaps=[
                "Python experience is not verified.",
            ],
            warnings=[
                "Work-mode preference requires verification.",
            ],
            missing_data=[
                "Candidate work-mode preference is unavailable.",
            ],
        ),
        scoring_version="candidate-job-matcher-v1",
        source_resume_text_sha256="a" * 64,
        source_resume_parser_version="resume-parser-v1",
        source_job_description_sha256="b" * 64,
        source_job_parser_version="job-parser-v1",
        matched_at=now,
        created_at=now,
        updated_at=now,
    )


def test_prompt_builder_uses_versioned_contract() -> None:
    prompt = build_candidate_analysis_prompt(
        resume_profile=_build_resume_profile(),
        job_requirement_profile=_build_job_profile(),
        candidate_job_match=(
            _build_candidate_job_match()
        ),
    )

    assert prompt.prompt_version == (
        CANDIDATE_ANALYSIS_PROMPT_VERSION
    )
    assert prompt.prompt_version == (
        "candidate-analysis-v1"
    )
    assert len(prompt.input_fingerprint_sha256) == 64


def test_input_payload_contains_required_professional_data(
) -> None:
    payload = build_candidate_analysis_input_payload(
        resume_profile=_build_resume_profile(),
        job_requirement_profile=_build_job_profile(),
        candidate_job_match=(
            _build_candidate_job_match()
        ),
    )

    candidate_profile = payload["candidate_profile"]
    job_profile = payload["job_requirement_profile"]
    deterministic_match = payload["deterministic_match"]

    assert isinstance(candidate_profile, dict)
    assert isinstance(job_profile, dict)
    assert isinstance(deterministic_match, dict)

    assert candidate_profile["current_role"] == (
        "Frontend Developer"
    )
    assert "React" in candidate_profile["skills"]

    assert job_profile["job_title"] == (
        "Full-Stack AI Engineer"
    )
    assert "Python" in job_profile["required_skills"]

    assert deterministic_match["overall_score"] == 72.50
    assert deterministic_match["recommendation"] == (
        "good_match"
    )


def test_prompt_excludes_unnecessary_personal_data(
) -> None:
    prompt = build_candidate_analysis_prompt(
        resume_profile=_build_resume_profile(),
        job_requirement_profile=_build_job_profile(),
        candidate_job_match=(
            _build_candidate_job_match()
        ),
    )

    excluded_values = [
        "Harsha Vardhan",
        "harsha.private@example.com",
        "+91 9999999999",
        "Prestige University",
        "Famous Technology Company",
        "Private Office Location",
        "https://private-project.example.com",
        "PRIVATE-CREDENTIAL-ID",
        "https://private-credential.example.com",
        "Telugu",
    ]

    for value in excluded_values:
        assert value not in prompt.user_prompt


def test_prompt_excludes_persistence_metadata() -> None:
    prompt = build_candidate_analysis_prompt(
        resume_profile=_build_resume_profile(),
        job_requirement_profile=_build_job_profile(),
        candidate_job_match=(
            _build_candidate_job_match()
        ),
    )

    excluded_values = [
        "11111111-1111-1111-1111-111111111111",
        "22222222-2222-2222-2222-222222222222",
        "33333333-3333-3333-3333-333333333333",
        "44444444-4444-4444-4444-444444444444",
        "55555555-5555-5555-5555-555555555555",
        "66666666-6666-6666-6666-666666666666",
        "a" * 64,
        "b" * 64,
    ]

    for value in excluded_values:
        assert value not in prompt.user_prompt


def test_system_prompt_contains_responsible_ai_rules(
) -> None:
    prompt = build_candidate_analysis_prompt(
        resume_profile=_build_resume_profile(),
        job_requirement_profile=_build_job_profile(),
        candidate_job_match=(
            _build_candidate_job_match()
        ),
    )

    assert "deterministic score" in prompt.system_prompt
    assert "immutable" in prompt.system_prompt
    assert "protected personal" in prompt.system_prompt
    assert "Do not make a final hiring" in (
        prompt.system_prompt
    )
    assert "Do not invent experience" in (
        prompt.system_prompt
    )
    assert "human recruiter" in prompt.system_prompt


def test_user_prompt_contains_deterministic_evidence(
) -> None:
    prompt = build_candidate_analysis_prompt(
        resume_profile=_build_resume_profile(),
        job_requirement_profile=_build_job_profile(),
        candidate_job_match=(
            _build_candidate_job_match()
        ),
    )

    assert '"overall_score": 72.5' in prompt.user_prompt
    assert '"skill_score": 65.0' in prompt.user_prompt
    assert '"Python"' in prompt.user_prompt
    assert '"FastAPI"' in prompt.user_prompt
    assert "Python experience is not verified." in (
        prompt.user_prompt
    )
    assert (
        "Candidate work-mode preference is unavailable."
        in prompt.user_prompt
    )


def test_prompt_is_deterministic() -> None:
    arguments = {
        "resume_profile": _build_resume_profile(),
        "job_requirement_profile": _build_job_profile(),
        "candidate_job_match": (
            _build_candidate_job_match()
        ),
    }

    first_prompt = build_candidate_analysis_prompt(
        **arguments
    )
    second_prompt = build_candidate_analysis_prompt(
        **arguments
    )

    assert first_prompt == second_prompt


def test_resume_change_changes_input_fingerprint() -> None:
    resume_profile = _build_resume_profile()

    first_fingerprint = (
        calculate_candidate_analysis_input_fingerprint(
            resume_profile=resume_profile,
            job_requirement_profile=_build_job_profile(),
            candidate_job_match=(
                _build_candidate_job_match()
            ),
        )
    )

    changed_resume_profile = resume_profile.model_copy(
        update={
            "skills": [
                *resume_profile.skills,
                "FastAPI",
            ]
        }
    )

    second_fingerprint = (
        calculate_candidate_analysis_input_fingerprint(
            resume_profile=changed_resume_profile,
            job_requirement_profile=_build_job_profile(),
            candidate_job_match=(
                _build_candidate_job_match()
            ),
        )
    )

    assert first_fingerprint != second_fingerprint


def test_match_change_changes_input_fingerprint() -> None:
    candidate_job_match = _build_candidate_job_match()

    first_fingerprint = (
        calculate_candidate_analysis_input_fingerprint(
            resume_profile=_build_resume_profile(),
            job_requirement_profile=_build_job_profile(),
            candidate_job_match=candidate_job_match,
        )
    )

    changed_match = candidate_job_match.model_copy(
        update={
            "overall_score": 68.25,
        }
    )

    second_fingerprint = (
        calculate_candidate_analysis_input_fingerprint(
            resume_profile=_build_resume_profile(),
            job_requirement_profile=_build_job_profile(),
            candidate_job_match=changed_match,
        )
    )

    assert first_fingerprint != second_fingerprint


def test_input_payload_is_json_serializable() -> None:
    payload = build_candidate_analysis_input_payload(
        resume_profile=_build_resume_profile(),
        job_requirement_profile=_build_job_profile(),
        candidate_job_match=(
            _build_candidate_job_match()
        ),
    )

    serialized_payload = json.dumps(
        payload,
        sort_keys=True,
    )

    assert "candidate_profile" in serialized_payload
    assert "job_requirement_profile" in (
        serialized_payload
    )
    assert "deterministic_match" in serialized_payload