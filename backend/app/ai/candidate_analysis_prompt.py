import json
from dataclasses import dataclass
from hashlib import sha256

from app.schemas.candidate_job_match import (
    CandidateJobMatchResponse,
)
from app.schemas.job_requirement_profile import (
    JobRequirementProfileData,
)
from app.schemas.resume_profile import (
    ResumeProfileData,
)


CANDIDATE_ANALYSIS_PROMPT_VERSION = (
    "candidate-analysis-v1"
)


@dataclass(
    frozen=True,
    slots=True,
)
class CandidateAnalysisPrompt:
    prompt_version: str
    system_prompt: str
    user_prompt: str
    input_fingerprint_sha256: str

    def __post_init__(self) -> None:
        if not self.prompt_version.strip():
            raise ValueError(
                "prompt_version must not be empty."
            )

        if not self.system_prompt.strip():
            raise ValueError(
                "system_prompt must not be empty."
            )

        if not self.user_prompt.strip():
            raise ValueError(
                "user_prompt must not be empty."
            )

        if len(self.input_fingerprint_sha256) != 64:
            raise ValueError(
                "input_fingerprint_sha256 must contain "
                "a SHA-256 hexadecimal digest."
            )


def _build_candidate_profile_payload(
    resume_profile: ResumeProfileData,
) -> dict[str, object]:
    return {
        "location": resume_profile.location,
        "current_role": resume_profile.current_role,
        "professional_summary": (
            resume_profile.professional_summary
        ),
        "total_experience_months": (
            resume_profile.total_experience_months
        ),
        "skills": list(resume_profile.skills),
        "education": [
            {
                "degree": entry.degree,
                "field_of_study": entry.field_of_study,
                "start_date": entry.start_date,
                "end_date": entry.end_date,
                "description": entry.description,
            }
            for entry in resume_profile.education
        ],
        "work_experience": [
            {
                "role": entry.role,
                "start_date": entry.start_date,
                "end_date": entry.end_date,
                "is_current": entry.is_current,
                "highlights": list(entry.highlights),
            }
            for entry in resume_profile.work_experience
        ],
        "projects": [
            {
                "name": entry.name,
                "description": entry.description,
                "technologies": list(
                    entry.technologies
                ),
                "highlights": list(entry.highlights),
            }
            for entry in resume_profile.projects
        ],
        "certifications": [
            {
                "name": entry.name,
                "issuer": entry.issuer,
                "issue_date": entry.issue_date,
                "expiry_date": entry.expiry_date,
            }
            for entry in resume_profile.certifications
        ],
        "warnings": list(resume_profile.warnings),
        "missing_sections": list(
            resume_profile.missing_sections
        ),
        "confidence": resume_profile.confidence,
    }


def _build_job_profile_payload(
    job_requirement_profile: JobRequirementProfileData,
) -> dict[str, object]:
    return {
        "job_title": job_requirement_profile.job_title,
        "department": job_requirement_profile.department,
        "location": job_requirement_profile.location,
        "employment_type": (
            job_requirement_profile.employment_type
        ),
        "work_mode": job_requirement_profile.work_mode,
        "seniority_level": (
            job_requirement_profile.seniority_level
        ),
        "summary": job_requirement_profile.summary,
        "responsibilities": list(
            job_requirement_profile.responsibilities
        ),
        "required_skills": list(
            job_requirement_profile.required_skills
        ),
        "preferred_skills": list(
            job_requirement_profile.preferred_skills
        ),
        "minimum_experience_years": (
            job_requirement_profile
            .minimum_experience_years
        ),
        "maximum_experience_years": (
            job_requirement_profile
            .maximum_experience_years
        ),
        "required_education": list(
            job_requirement_profile.required_education
        ),
        "preferred_education": list(
            job_requirement_profile.preferred_education
        ),
        "required_certifications": list(
            job_requirement_profile
            .required_certifications
        ),
        "preferred_certifications": list(
            job_requirement_profile
            .preferred_certifications
        ),
        "keywords": list(
            job_requirement_profile.keywords
        ),
        "warnings": list(
            job_requirement_profile.warnings
        ),
        "missing_sections": list(
            job_requirement_profile.missing_sections
        ),
        "confidence": (
            job_requirement_profile.confidence
        ),
    }


def _build_candidate_job_match_payload(
    candidate_job_match: CandidateJobMatchResponse,
) -> dict[str, object]:
    return {
        "overall_score": (
            candidate_job_match.overall_score
        ),
        "skill_score": candidate_job_match.skill_score,
        "experience_score": (
            candidate_job_match.experience_score
        ),
        "education_score": (
            candidate_job_match.education_score
        ),
        "certification_score": (
            candidate_job_match.certification_score
        ),
        "location_score": (
            candidate_job_match.location_score
        ),
        "work_mode_score": (
            candidate_job_match.work_mode_score
        ),
        "confidence_score": (
            candidate_job_match.confidence_score
        ),
        "recommendation": (
            candidate_job_match.recommendation
        ),
        "analysis_data": (
            candidate_job_match.analysis_data.model_dump(
                mode="json"
            )
        ),
        "scoring_version": (
            candidate_job_match.scoring_version
        ),
    }


def build_candidate_analysis_input_payload(
    *,
    resume_profile: ResumeProfileData,
    job_requirement_profile: JobRequirementProfileData,
    candidate_job_match: CandidateJobMatchResponse,
) -> dict[str, object]:
    return {
        "prompt_version": (
            CANDIDATE_ANALYSIS_PROMPT_VERSION
        ),
        "candidate_profile": (
            _build_candidate_profile_payload(
                resume_profile
            )
        ),
        "job_requirement_profile": (
            _build_job_profile_payload(
                job_requirement_profile
            )
        ),
        "deterministic_match": (
            _build_candidate_job_match_payload(
                candidate_job_match
            )
        ),
    }


def _serialize_canonical_payload(
    payload: dict[str, object],
) -> str:
    return json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def calculate_candidate_analysis_input_fingerprint(
    *,
    resume_profile: ResumeProfileData,
    job_requirement_profile: JobRequirementProfileData,
    candidate_job_match: CandidateJobMatchResponse,
) -> str:
    payload = build_candidate_analysis_input_payload(
        resume_profile=resume_profile,
        job_requirement_profile=(
            job_requirement_profile
        ),
        candidate_job_match=candidate_job_match,
    )

    canonical_payload = _serialize_canonical_payload(
        payload
    )

    return sha256(
        canonical_payload.encode("utf-8")
    ).hexdigest()


def _build_system_prompt() -> str:
    return """
You are an AI recruiter decision-support assistant.

Use only the verified structured Candidate profile, Job
requirement profile and deterministic Candidate-Job match data
provided by the application.

Follow these rules:

1. Treat every deterministic score and deterministic
   recommendation as immutable application data. Do not change,
   recalculate, override or secretly replace them.

2. Do not infer or evaluate religion, caste, race, ethnicity,
   gender, sexual orientation, disability, health information,
   pregnancy, political views or other protected personal
   attributes.

3. Do not make a final hiring, rejection, shortlisting or
   compensation decision.

4. Do not invent experience, skills, education, projects,
   certifications, achievements or job requirements.

5. Clearly distinguish verified evidence from interpretation.

6. State when information is missing, uncertain or unsupported.

7. Generate screening, technical and behavioural interview
   questions grounded in the verified strengths, gaps, risks and
   missing data.

8. Use evidence field paths from the supplied JSON wherever
   practical.

9. Return only structured output that satisfies the requested
   response schema.

10. Include a clear statement that the analysis is decision
    support and must be reviewed by a human recruiter.
""".strip()


def _build_user_prompt(
    payload: dict[str, object],
) -> str:
    formatted_payload = json.dumps(
        payload,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )

    return (
        "Generate a recruiter-friendly Candidate analysis using "
        "the verified structured input below.\n\n"
        "Do not use or infer information that is not present in "
        "this input. Use the JSON field paths when referring to "
        "evidence.\n\n"
        "VERIFIED_INPUT_JSON:\n"
        f"{formatted_payload}"
    )


def build_candidate_analysis_prompt(
    *,
    resume_profile: ResumeProfileData,
    job_requirement_profile: JobRequirementProfileData,
    candidate_job_match: CandidateJobMatchResponse,
) -> CandidateAnalysisPrompt:
    payload = build_candidate_analysis_input_payload(
        resume_profile=resume_profile,
        job_requirement_profile=(
            job_requirement_profile
        ),
        candidate_job_match=candidate_job_match,
    )

    fingerprint = (
        calculate_candidate_analysis_input_fingerprint(
            resume_profile=resume_profile,
            job_requirement_profile=(
                job_requirement_profile
            ),
            candidate_job_match=candidate_job_match,
        )
    )

    return CandidateAnalysisPrompt(
        prompt_version=(
            CANDIDATE_ANALYSIS_PROMPT_VERSION
        ),
        system_prompt=_build_system_prompt(),
        user_prompt=_build_user_prompt(payload),
        input_fingerprint_sha256=fingerprint,
    )