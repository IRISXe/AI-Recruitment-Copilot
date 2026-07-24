from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.candidate_job_match import CandidateJobMatch
from app.models.job import Job
from app.models.job_requirement_profile import JobRequirementProfile
from app.models.resume import Resume
from app.models.resume_profile import ResumeProfile
from app.repositories.candidate_job_match_repository import (
    create_candidate_job_match,
    get_candidate_job_match_by_candidate_and_job,
    get_candidate_job_match_by_id,
    update_candidate_job_match,
)
from app.repositories.candidate_repository import create_candidate
from app.repositories.job_repository import create_job
from app.schemas.candidate import CandidateCreate
from app.schemas.candidate_job_match import (
    CandidateJobMatchCreate,
    CandidateJobMatchUpdate,
)
from app.schemas.job import JobCreate


def persist_match_dependencies(
    db_session: Session,
) -> tuple[
    Job,
    Resume,
    ResumeProfile,
    JobRequirementProfile,
]:
    candidate = create_candidate(
        session=db_session,
        payload=CandidateCreate(
            full_name="Candidate Match User",
            email=f"candidate-match-{uuid4()}@example.com",
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
        storage_path=f"uploads/resumes/{resume_id}.pdf",
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
            "full_name": candidate.full_name,
            "location": "Hyderabad",
            "total_experience_months": 36,
            "skills": [
                "Python",
                "FastAPI",
                "PostgreSQL",
            ],
            "education": [],
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

    job_requirement_profile = JobRequirementProfile(
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
            job_requirement_profile,
        ]
    )
    db_session.flush()

    return (
        job,
        resume,
        resume_profile,
        job_requirement_profile,
    )


def build_create_payload(
    *,
    job: Job,
    resume: Resume,
    resume_profile: ResumeProfile,
    job_requirement_profile: JobRequirementProfile,
) -> CandidateJobMatchCreate:
    return CandidateJobMatchCreate(
        candidate_id=resume.candidate_id,
        job_id=job.id,
        resume_id=resume.id,
        resume_profile_id=resume_profile.id,
        job_requirement_profile_id=job_requirement_profile.id,
        overall_score=82.5,
        skill_score=87.5,
        experience_score=100.0,
        education_score=50.0,
        certification_score=50.0,
        location_score=100.0,
        work_mode_score=100.0,
        confidence_score=90.0,
        recommendation="good_match",
        analysis_data={
            "matched_required_skills": [
                "Python",
                "FastAPI",
            ],
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
        },
        scoring_version="candidate-job-rule-based-v1",
        source_resume_text_sha256="a" * 64,
        source_resume_parser_version="rule-based-v1",
        source_job_description_sha256="b" * 64,
        source_job_parser_version="job-rule-based-v1",
        matched_at=datetime.now(UTC),
    )


def test_create_candidate_job_match_persists_result(
    db_session: Session,
) -> None:
    (
        job,
        resume,
        resume_profile,
        job_requirement_profile,
    ) = persist_match_dependencies(db_session)

    match = create_candidate_job_match(
        session=db_session,
        payload=build_create_payload(
            job=job,
            resume=resume,
            resume_profile=resume_profile,
            job_requirement_profile=job_requirement_profile,
        ),
    )

    persisted_match = db_session.get(
        CandidateJobMatch,
        match.id,
    )

    assert match.id is not None
    assert persisted_match is not None
    assert persisted_match.candidate_id == resume.candidate_id
    assert persisted_match.job_id == job.id
    assert persisted_match.resume_id == resume.id
    assert persisted_match.overall_score == 82.5
    assert persisted_match.recommendation == "good_match"


def test_get_candidate_job_match_returns_result_or_none(
    db_session: Session,
) -> None:
    (
        job,
        resume,
        resume_profile,
        job_requirement_profile,
    ) = persist_match_dependencies(db_session)

    created_match = create_candidate_job_match(
        session=db_session,
        payload=build_create_payload(
            job=job,
            resume=resume,
            resume_profile=resume_profile,
            job_requirement_profile=job_requirement_profile,
        ),
    )

    by_id = get_candidate_job_match_by_id(
        session=db_session,
        match_id=created_match.id,
    )

    by_candidate_and_job = (
        get_candidate_job_match_by_candidate_and_job(
            session=db_session,
            candidate_id=resume.candidate_id,
            job_id=job.id,
        )
    )

    missing_match = get_candidate_job_match_by_candidate_and_job(
        session=db_session,
        candidate_id=uuid4(),
        job_id=uuid4(),
    )

    assert by_id is created_match
    assert by_candidate_and_job is created_match
    assert missing_match is None


def test_update_candidate_job_match_changes_recalculated_values(
    db_session: Session,
) -> None:
    (
        job,
        resume,
        resume_profile,
        job_requirement_profile,
    ) = persist_match_dependencies(db_session)

    match = create_candidate_job_match(
        session=db_session,
        payload=build_create_payload(
            job=job,
            resume=resume,
            resume_profile=resume_profile,
            job_requirement_profile=job_requirement_profile,
        ),
    )

    original_candidate_id = match.candidate_id
    original_job_id = match.job_id

    updated_match = update_candidate_job_match(
        session=db_session,
        match=match,
        payload=CandidateJobMatchUpdate(
            resume_id=resume.id,
            resume_profile_id=resume_profile.id,
            job_requirement_profile_id=job_requirement_profile.id,
            overall_score=91.0,
            skill_score=95.0,
            experience_score=100.0,
            education_score=75.0,
            certification_score=75.0,
            location_score=100.0,
            work_mode_score=100.0,
            confidence_score=95.0,
            recommendation="strong_match",
            analysis_data={
                "matched_required_skills": [
                    "Python",
                    "FastAPI",
                ],
                "matched_preferred_skills": [
                    "PostgreSQL",
                    "Docker",
                ],
                "strengths": [
                    "All required and preferred skills matched",
                ],
            },
            scoring_version="candidate-job-rule-based-v2",
            source_resume_text_sha256="c" * 64,
            source_resume_parser_version="rule-based-v2",
            source_job_description_sha256="d" * 64,
            source_job_parser_version="job-rule-based-v2",
            matched_at=datetime.now(UTC),
        ),
    )

    assert updated_match is match
    assert updated_match.candidate_id == original_candidate_id
    assert updated_match.job_id == original_job_id
    assert updated_match.overall_score == 91.0
    assert updated_match.recommendation == "strong_match"
    assert (
        updated_match.scoring_version
        == "candidate-job-rule-based-v2"
    )
    assert updated_match.source_resume_text_sha256 == "c" * 64


def test_candidate_job_combination_is_unique(
    db_session: Session,
) -> None:
    (
        job,
        resume,
        resume_profile,
        job_requirement_profile,
    ) = persist_match_dependencies(db_session)

    payload = build_create_payload(
        job=job,
        resume=resume,
        resume_profile=resume_profile,
        job_requirement_profile=job_requirement_profile,
    )

    create_candidate_job_match(
        session=db_session,
        payload=payload,
    )

    with pytest.raises(IntegrityError):
        create_candidate_job_match(
            session=db_session,
            payload=payload,
        )


def test_deleting_job_cascades_candidate_job_match(
    db_session: Session,
) -> None:
    (
        job,
        resume,
        resume_profile,
        job_requirement_profile,
    ) = persist_match_dependencies(db_session)

    match = create_candidate_job_match(
        session=db_session,
        payload=build_create_payload(
            job=job,
            resume=resume,
            resume_profile=resume_profile,
            job_requirement_profile=job_requirement_profile,
        ),
    )

    match_id = match.id

    db_session.delete(job)
    db_session.flush()
    db_session.expire_all()

    deleted_match = db_session.get(
        CandidateJobMatch,
        match_id,
    )

    assert deleted_match is None