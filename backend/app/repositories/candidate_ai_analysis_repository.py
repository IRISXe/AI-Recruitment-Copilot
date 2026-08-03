from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.candidate_ai_analysis import CandidateAIAnalysis


CandidateAIAnalysisStatus = Literal[
    "pending",
    "completed",
    "failed",
]


def create_candidate_ai_analysis(
    session: Session,
    *,
    candidate_id: UUID,
    job_id: UUID,
    resume_id: UUID,
    candidate_job_match_id: UUID,
    provider: str,
    model_name: str,
    prompt_version: str,
    input_fingerprint_sha256: str,
    source_match_updated_at: datetime,
    source_scoring_version: str,
    source_resume_profile_hash: str,
    source_job_profile_hash: str,
) -> CandidateAIAnalysis:
    analysis = CandidateAIAnalysis(
        candidate_id=candidate_id,
        job_id=job_id,
        resume_id=resume_id,
        candidate_job_match_id=candidate_job_match_id,
        analysis_data=None,
        status="pending",
        provider=provider,
        model_name=model_name,
        prompt_version=prompt_version,
        input_fingerprint_sha256=(
            input_fingerprint_sha256
        ),
        source_match_updated_at=source_match_updated_at,
        source_scoring_version=source_scoring_version,
        source_resume_profile_hash=(
            source_resume_profile_hash
        ),
        source_job_profile_hash=(
            source_job_profile_hash
        ),
        input_tokens=None,
        output_tokens=None,
        total_tokens=None,
        estimated_cost=None,
        processing_time_ms=None,
        error_code=None,
        error_message=None,
        generated_at=None,
    )

    session.add(analysis)
    session.flush()

    return analysis


def get_candidate_ai_analysis_by_id(
    session: Session,
    analysis_id: UUID,
) -> CandidateAIAnalysis | None:
    return session.get(
        CandidateAIAnalysis,
        analysis_id,
    )


def get_candidate_ai_analysis_by_candidate_and_job(
    session: Session,
    *,
    candidate_id: UUID,
    job_id: UUID,
) -> CandidateAIAnalysis | None:
    statement = select(CandidateAIAnalysis).where(
        CandidateAIAnalysis.candidate_id == candidate_id,
        CandidateAIAnalysis.job_id == job_id,
    )

    return session.scalar(statement)


def update_candidate_ai_analysis(
    session: Session,
    *,
    analysis: CandidateAIAnalysis,
    resume_id: UUID,
    candidate_job_match_id: UUID,
    analysis_data: dict[str, object] | None,
    status: CandidateAIAnalysisStatus,
    provider: str,
    model_name: str,
    prompt_version: str,
    input_fingerprint_sha256: str,
    source_match_updated_at: datetime,
    source_scoring_version: str,
    source_resume_profile_hash: str,
    source_job_profile_hash: str,
    input_tokens: int | None,
    output_tokens: int | None,
    total_tokens: int | None,
    estimated_cost: Decimal | None,
    processing_time_ms: int | None,
    error_code: str | None,
    error_message: str | None,
    generated_at: datetime | None,
) -> CandidateAIAnalysis:
    analysis.resume_id = resume_id
    analysis.candidate_job_match_id = (
        candidate_job_match_id
    )
    analysis.analysis_data = analysis_data
    analysis.status = status
    analysis.provider = provider
    analysis.model_name = model_name
    analysis.prompt_version = prompt_version
    analysis.input_fingerprint_sha256 = (
        input_fingerprint_sha256
    )
    analysis.source_match_updated_at = (
        source_match_updated_at
    )
    analysis.source_scoring_version = (
        source_scoring_version
    )
    analysis.source_resume_profile_hash = (
        source_resume_profile_hash
    )
    analysis.source_job_profile_hash = (
        source_job_profile_hash
    )
    analysis.input_tokens = input_tokens
    analysis.output_tokens = output_tokens
    analysis.total_tokens = total_tokens
    analysis.estimated_cost = estimated_cost
    analysis.processing_time_ms = processing_time_ms
    analysis.error_code = error_code
    analysis.error_message = error_message
    analysis.generated_at = generated_at

    session.flush()

    return analysis


def delete_candidate_ai_analysis(
    session: Session,
    *,
    analysis: CandidateAIAnalysis,
) -> None:
    session.delete(analysis)
    session.flush()