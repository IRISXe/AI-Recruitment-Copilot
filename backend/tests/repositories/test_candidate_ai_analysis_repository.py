from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.candidate import Candidate
from app.models.candidate_ai_analysis import (
    CandidateAIAnalysis,
)
from app.models.candidate_job_match import CandidateJobMatch
from app.models.job import Job
from app.models.job_requirement_profile import (
    JobRequirementProfile,
)
from app.models.resume import Resume
from app.models.resume_profile import ResumeProfile
from app.repositories.candidate_ai_analysis_repository import (
    create_candidate_ai_analysis,
    delete_candidate_ai_analysis,
    get_candidate_ai_analysis_by_candidate_and_job,
    get_candidate_ai_analysis_by_id,
    update_candidate_ai_analysis,
)
from app.repositories.candidate_repository import (
    create_candidate,
)
from app.repositories.job_repository import create_job
from app.schemas.candidate import CandidateCreate
from app.schemas.job import JobCreate


def persist_analysis_dependencies(
    db_session: Session,
) -> tuple[
    Candidate,
    Job,
    Resume,
    CandidateJobMatch,
]:
    candidate = create_candidate(
        session=db_session,
        payload=CandidateCreate(
            full_name="AI Analysis Candidate",
            email=(
                f"ai-analysis-{uuid4()}@example.com"
            ),
            phone="+91 9876543210",
            current_location="Hyderabad",
            current_role="Backend Developer",
            total_experience_months=36,
            skills=[
                "Python",
                "FastAPI",
                "PostgreSQL",
            ],
        ),
    )

    job = create_job(
        session=db_session,
        payload=JobCreate(
            title="Backend Engineer",
            description=(
                "Backend Engineer role requiring Python, "
                "FastAPI, PostgreSQL, and Docker."
            ),
            department="Engineering",
            location="Hyderabad",
            employment_type="full_time",
            minimum_experience=2,
            required_skills=[
                "Python",
                "FastAPI",
            ],
            preferred_skills=[
                "PostgreSQL",
                "Docker",
            ],
        ),
    )

    resume_id = uuid4()

    resume = Resume(
        id=resume_id,
        candidate_id=candidate.id,
        original_filename="candidate-resume.pdf",
        stored_filename=f"{resume_id}.pdf",
        storage_path=(
            f"uploads/resumes/{resume_id}.pdf"
        ),
        content_type="application/pdf",
        file_size_bytes=2048,
        is_primary=True,
    )

    db_session.add(resume)
    db_session.flush()

    now = datetime.now(UTC)

    resume_profile = ResumeProfile(
        resume_id=resume.id,
        profile_data={
            "current_role": "Backend Developer",
            "total_experience_months": 36,
            "skills": [
                "Python",
                "FastAPI",
                "PostgreSQL",
            ],
            "education": [],
            "work_experience": [],
            "projects": [],
            "certifications": [],
            "warnings": [],
            "missing_sections": [],
            "confidence": 0.9,
        },
        parsing_status="completed",
        parsing_error=None,
        parser_version="rule-based-v1",
        source_text_sha256="a" * 64,
        parsed_at=now,
    )

    job_profile = JobRequirementProfile(
        job_id=job.id,
        profile_data={
            "job_title": "Backend Engineer",
            "location": "Hyderabad",
            "work_mode": "hybrid",
            "required_skills": [
                "Python",
                "FastAPI",
            ],
            "preferred_skills": [
                "PostgreSQL",
                "Docker",
            ],
            "minimum_experience_years": 2,
            "maximum_experience_years": 5,
            "required_education": [],
            "preferred_education": [],
            "required_certifications": [],
            "preferred_certifications": [],
            "warnings": [],
            "missing_sections": [],
            "confidence": 0.9,
        },
        parsing_status="completed",
        parsing_error=None,
        parser_version="job-rule-based-v1",
        source_description_sha256="b" * 64,
        parsed_at=now,
    )

    db_session.add_all(
        [
            resume_profile,
            job_profile,
        ]
    )
    db_session.flush()

    match = CandidateJobMatch(
        candidate_id=candidate.id,
        job_id=job.id,
        resume_id=resume.id,
        resume_profile_id=resume_profile.id,
        job_requirement_profile_id=job_profile.id,
        overall_score=Decimal("82.50"),
        skill_score=Decimal("87.50"),
        experience_score=Decimal("100.00"),
        education_score=Decimal("50.00"),
        certification_score=Decimal("50.00"),
        location_score=Decimal("100.00"),
        work_mode_score=Decimal("100.00"),
        confidence_score=Decimal("90.00"),
        recommendation="good_match",
        analysis_data={
            "strengths": [
                "All required skills matched",
            ],
            "gaps": [
                "Docker was not found",
            ],
        },
        scoring_version=(
            "candidate-job-rule-based-v1"
        ),
        source_resume_text_sha256="a" * 64,
        source_resume_parser_version=(
            "rule-based-v1"
        ),
        source_job_description_sha256="b" * 64,
        source_job_parser_version=(
            "job-rule-based-v1"
        ),
        matched_at=now,
    )

    db_session.add(match)
    db_session.flush()

    return candidate, job, resume, match


def create_analysis_record(
    db_session: Session,
    *,
    candidate: Candidate,
    job: Job,
    resume: Resume,
    match: CandidateJobMatch,
) -> CandidateAIAnalysis:
    return create_candidate_ai_analysis(
        db_session,
        candidate_id=candidate.id,
        job_id=job.id,
        resume_id=resume.id,
        candidate_job_match_id=match.id,
        provider="fake",
        model_name="fake-structured-v1",
        prompt_version="candidate-analysis-v1",
        input_fingerprint_sha256="c" * 64,
        source_match_updated_at=(
            match.updated_at
        ),
        source_scoring_version=(
            match.scoring_version
        ),
        source_resume_profile_hash="d" * 64,
        source_job_profile_hash="e" * 64,
    )


def test_create_candidate_ai_analysis_adds_pending_record(
    db_session: Session,
) -> None:
    candidate, job, resume, match = (
        persist_analysis_dependencies(db_session)
    )

    analysis = create_analysis_record(
        db_session,
        candidate=candidate,
        job=job,
        resume=resume,
        match=match,
    )

    persisted_analysis = db_session.get(
        CandidateAIAnalysis,
        analysis.id,
    )

    assert analysis.id is not None
    assert persisted_analysis is not None
    assert analysis.status == "pending"
    assert analysis.analysis_data is None
    assert analysis.provider == "fake"
    assert analysis.model_name == "fake-structured-v1"
    assert analysis.input_tokens is None
    assert analysis.error_message is None
    assert analysis.generated_at is None


def test_get_candidate_ai_analysis_returns_record_or_none(
    db_session: Session,
) -> None:
    candidate, job, resume, match = (
        persist_analysis_dependencies(db_session)
    )

    analysis = create_analysis_record(
        db_session,
        candidate=candidate,
        job=job,
        resume=resume,
        match=match,
    )

    by_id = get_candidate_ai_analysis_by_id(
        db_session,
        analysis.id,
    )

    by_pair = (
        get_candidate_ai_analysis_by_candidate_and_job(
            db_session,
            candidate_id=candidate.id,
            job_id=job.id,
        )
    )

    missing = (
        get_candidate_ai_analysis_by_candidate_and_job(
            db_session,
            candidate_id=uuid4(),
            job_id=uuid4(),
        )
    )

    assert by_id is analysis
    assert by_pair is analysis
    assert missing is None


def test_update_candidate_ai_analysis_changes_result(
    db_session: Session,
) -> None:
    candidate, job, resume, match = (
        persist_analysis_dependencies(db_session)
    )

    analysis = create_analysis_record(
        db_session,
        candidate=candidate,
        job=job,
        resume=resume,
        match=match,
    )

    original_candidate_id = analysis.candidate_id
    original_job_id = analysis.job_id
    generated_at = datetime.now(UTC)

    analysis_data: dict[str, object] = {
        "summary": (
            "The candidate aligns with the core "
            "backend requirements."
        ),
        "strengths": [
            {
                "title": "Required skills",
                "explanation": (
                    "Python and FastAPI are present."
                ),
            }
        ],
        "gaps": [],
    }

    updated_analysis = update_candidate_ai_analysis(
        db_session,
        analysis=analysis,
        resume_id=resume.id,
        candidate_job_match_id=match.id,
        analysis_data=analysis_data,
        status="completed",
        provider="fake",
        model_name="fake-structured-v2",
        prompt_version="candidate-analysis-v2",
        input_fingerprint_sha256="f" * 64,
        source_match_updated_at=match.updated_at,
        source_scoring_version=match.scoring_version,
        source_resume_profile_hash="1" * 64,
        source_job_profile_hash="2" * 64,
        input_tokens=500,
        output_tokens=250,
        total_tokens=750,
        estimated_cost=Decimal("0.00125000"),
        processing_time_ms=125,
        error_code=None,
        error_message=None,
        generated_at=generated_at,
    )

    assert updated_analysis is analysis
    assert analysis.candidate_id == original_candidate_id
    assert analysis.job_id == original_job_id
    assert analysis.status == "completed"
    assert analysis.analysis_data == analysis_data
    assert analysis.model_name == "fake-structured-v2"
    assert analysis.prompt_version == (
        "candidate-analysis-v2"
    )
    assert analysis.input_tokens == 500
    assert analysis.output_tokens == 250
    assert analysis.total_tokens == 750
    assert analysis.estimated_cost == Decimal(
        "0.00125000"
    )
    assert analysis.processing_time_ms == 125
    assert analysis.generated_at == generated_at


def test_candidate_job_analysis_combination_is_unique(
    db_session: Session,
) -> None:
    candidate, job, resume, match = (
        persist_analysis_dependencies(db_session)
    )

    create_analysis_record(
        db_session,
        candidate=candidate,
        job=job,
        resume=resume,
        match=match,
    )

    with pytest.raises(IntegrityError):
        create_analysis_record(
            db_session,
            candidate=candidate,
            job=job,
            resume=resume,
            match=match,
        )


def test_delete_candidate_ai_analysis_removes_record(
    db_session: Session,
) -> None:
    candidate, job, resume, match = (
        persist_analysis_dependencies(db_session)
    )

    analysis = create_analysis_record(
        db_session,
        candidate=candidate,
        job=job,
        resume=resume,
        match=match,
    )

    analysis_id = analysis.id

    delete_candidate_ai_analysis(
        db_session,
        analysis=analysis,
    )
    db_session.expire_all()

    assert (
        db_session.get(
            CandidateAIAnalysis,
            analysis_id,
        )
        is None
    )


def test_deleting_match_cascades_candidate_ai_analysis(
    db_session: Session,
) -> None:
    candidate, job, resume, match = (
        persist_analysis_dependencies(db_session)
    )

    analysis = create_analysis_record(
        db_session,
        candidate=candidate,
        job=job,
        resume=resume,
        match=match,
    )

    analysis_id = analysis.id

    db_session.delete(match)
    db_session.flush()
    db_session.expire_all()

    assert (
        db_session.get(
            CandidateAIAnalysis,
            analysis_id,
        )
        is None
    )