import logging
from datetime import UTC, datetime
from uuid import UUID

from fastapi import status
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.ai.candidate_analysis_prompt import (
    CandidateAnalysisPrompt,
    build_candidate_analysis_prompt,
)
from app.ai.structured_llm import (
    StructuredLLMClient,
    StructuredLLMConfigurationError,
    StructuredLLMError,
)
from app.core.exceptions import AppException
from app.matching.candidate_job_matcher import (
    SCORING_VERSION,
)
from app.models.candidate_ai_analysis import (
    CandidateAIAnalysis,
)
from app.models.candidate_job_match import (
    CandidateJobMatch,
)
from app.models.job_requirement_profile import (
    JobRequirementProfile,
)
from app.models.resume import Resume
from app.models.resume_profile import ResumeProfile
from app.repositories.candidate_ai_analysis_repository import (
    create_candidate_ai_analysis as create_analysis_record,
)
from app.repositories.candidate_ai_analysis_repository import (
    get_candidate_ai_analysis_by_candidate_and_job
    as get_analysis_record,
)
from app.repositories.candidate_ai_analysis_repository import (
    update_candidate_ai_analysis as update_analysis_record,
)
from app.repositories.candidate_job_match_repository import (
    get_candidate_job_match_by_candidate_and_job
    as get_match_record,
)
from app.repositories.candidate_repository import (
    get_candidate_by_id as get_candidate_record,
)
from app.repositories.job_repository import (
    get_job_by_id as get_job_record,
)
from app.repositories.job_requirement_profile_repository import (
    get_job_requirement_profile_by_job_id
    as get_job_profile_record,
)
from app.repositories.resume_profile_repository import (
    get_resume_profile_by_resume_id
    as get_resume_profile_record,
)
from app.repositories.resume_repository import (
    get_primary_resume_by_candidate_id
    as get_primary_resume_record,
)
from app.schemas.candidate_ai_analysis import (
    CandidateAIAnalysisData,
)
from app.schemas.candidate_job_match import (
    CandidateJobMatchResponse,
)
from app.schemas.job_requirement_profile import (
    JobRequirementProfileData,
)
from app.schemas.resume_profile import ResumeProfileData


logger = logging.getLogger(__name__)


def _get_llm_identity_or_raise(
    llm_client: StructuredLLMClient,
) -> tuple[str, str]:
    provider = llm_client.provider.strip()
    model_name = llm_client.model_name.strip()

    if not provider or not model_name:
        raise AppException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code="structured_llm_not_configured",
            message=(
                "A valid structured LLM provider and model "
                "must be configured before generating an "
                "AI Candidate analysis."
            ),
        )

    return provider, model_name


def _get_candidate_or_raise(
    session: Session,
    candidate_id: UUID,
) -> None:
    candidate = get_candidate_record(
        session,
        candidate_id,
    )

    if candidate is None:
        raise AppException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="candidate_not_found",
            message="The requested candidate does not exist.",
        )


def _get_job_or_raise(
    session: Session,
    job_id: UUID,
) -> None:
    job = get_job_record(
        session,
        job_id,
    )

    if job is None:
        raise AppException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="job_not_found",
            message="The requested job does not exist.",
        )


def _get_primary_resume_or_raise(
    session: Session,
    candidate_id: UUID,
) -> Resume:
    primary_resume = get_primary_resume_record(
        session,
        candidate_id,
    )

    if primary_resume is None:
        raise AppException(
            status_code=status.HTTP_409_CONFLICT,
            code="primary_resume_not_found",
            message=(
                "The candidate must have an explicitly selected "
                "primary Resume before AI analysis."
            ),
        )

    return primary_resume


def _get_completed_resume_profile_or_raise(
    session: Session,
    *,
    resume_id: UUID,
) -> ResumeProfile:
    resume_profile = get_resume_profile_record(
        session,
        resume_id=resume_id,
    )

    if resume_profile is None:
        raise AppException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="resume_profile_not_found",
            message=(
                "A structured profile is not available for "
                "the candidate's primary Resume."
            ),
        )

    if (
        resume_profile.parsing_status != "completed"
        or resume_profile.profile_data is None
        or resume_profile.parser_version is None
        or resume_profile.source_text_sha256 is None
    ):
        raise AppException(
            status_code=status.HTTP_409_CONFLICT,
            code="resume_profile_not_ready",
            message=(
                "The candidate's primary Resume must have a "
                "completed structured profile before AI analysis."
            ),
        )

    return resume_profile


def _get_completed_job_profile_or_raise(
    session: Session,
    *,
    job_id: UUID,
) -> JobRequirementProfile:
    job_profile = get_job_profile_record(
        session,
        job_id=job_id,
    )

    if job_profile is None:
        raise AppException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="job_requirement_profile_not_found",
            message=(
                "A structured requirement profile is not "
                "available for this job."
            ),
        )

    if (
        job_profile.parsing_status != "completed"
        or job_profile.profile_data is None
        or job_profile.parser_version is None
        or job_profile.source_description_sha256 is None
    ):
        raise AppException(
            status_code=status.HTTP_409_CONFLICT,
            code="job_requirement_profile_not_ready",
            message=(
                "The job must have a completed structured "
                "requirement profile before AI analysis."
            ),
        )

    return job_profile


def _is_match_current(
    *,
    candidate_job_match: CandidateJobMatch,
    resume_profile: ResumeProfile,
    job_profile: JobRequirementProfile,
) -> bool:
    return (
        candidate_job_match.resume_id
        == resume_profile.resume_id
        and candidate_job_match.resume_profile_id
        == resume_profile.id
        and candidate_job_match.job_requirement_profile_id
        == job_profile.id
        and candidate_job_match.scoring_version
        == SCORING_VERSION
        and candidate_job_match.source_resume_text_sha256
        == resume_profile.source_text_sha256
        and candidate_job_match.source_resume_parser_version
        == resume_profile.parser_version
        and candidate_job_match.source_job_description_sha256
        == job_profile.source_description_sha256
        and candidate_job_match.source_job_parser_version
        == job_profile.parser_version
    )


def _get_current_match_or_raise(
    session: Session,
    *,
    candidate_id: UUID,
    job_id: UUID,
    resume_profile: ResumeProfile,
    job_profile: JobRequirementProfile,
) -> CandidateJobMatch:
    candidate_job_match = get_match_record(
        session,
        candidate_id=candidate_id,
        job_id=job_id,
    )

    if candidate_job_match is None:
        raise AppException(
            status_code=status.HTTP_409_CONFLICT,
            code="candidate_job_match_not_found",
            message=(
                "A deterministic Candidate–Job match must be "
                "generated before requesting AI analysis."
            ),
        )

    if not _is_match_current(
        candidate_job_match=candidate_job_match,
        resume_profile=resume_profile,
        job_profile=job_profile,
    ):
        raise AppException(
            status_code=status.HTTP_409_CONFLICT,
            code="candidate_job_match_stale",
            message=(
                "The deterministic Candidate–Job match is stale "
                "and must be regenerated before AI analysis."
            ),
        )

    return candidate_job_match


def _validate_resume_profile_data(
    resume_profile: ResumeProfile,
) -> ResumeProfileData:
    try:
        return ResumeProfileData.model_validate(
            resume_profile.profile_data
        )
    except ValidationError as exc:
        raise AppException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            code="resume_profile_data_invalid",
            message=(
                "The structured Resume profile contains "
                "invalid data."
            ),
        ) from exc


def _validate_job_profile_data(
    job_profile: JobRequirementProfile,
) -> JobRequirementProfileData:
    try:
        return JobRequirementProfileData.model_validate(
            job_profile.profile_data
        )
    except ValidationError as exc:
        raise AppException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            code="job_requirement_profile_data_invalid",
            message=(
                "The structured job requirement profile "
                "contains invalid data."
            ),
        ) from exc


def _validate_candidate_job_match_data(
    candidate_job_match: CandidateJobMatch,
) -> CandidateJobMatchResponse:
    try:
        return CandidateJobMatchResponse.model_validate(
            candidate_job_match
        )
    except ValidationError as exc:
        raise AppException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            code="candidate_job_match_data_invalid",
            message=(
                "The deterministic Candidate–Job match "
                "contains invalid data."
            ),
        ) from exc


def _build_prompt_or_raise(
    *,
    resume_profile_data: ResumeProfileData,
    job_profile_data: JobRequirementProfileData,
    candidate_job_match_data: CandidateJobMatchResponse,
) -> CandidateAnalysisPrompt:
    try:
        return build_candidate_analysis_prompt(
            resume_profile=resume_profile_data,
            job_requirement_profile=job_profile_data,
            candidate_job_match=candidate_job_match_data,
        )
    except ValueError as exc:
        raise AppException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            code="candidate_ai_analysis_input_invalid",
            message=(
                "The verified Candidate and Job data could not "
                "be prepared for AI analysis."
            ),
        ) from exc


def _is_existing_analysis_current(
    *,
    existing_analysis: CandidateAIAnalysis,
    primary_resume: Resume,
    candidate_job_match: CandidateJobMatch,
    resume_profile: ResumeProfile,
    job_profile: JobRequirementProfile,
    prompt: CandidateAnalysisPrompt,
    provider: str,
    model_name: str,
) -> bool:
    return (
        existing_analysis.status == "completed"
        and existing_analysis.analysis_data is not None
        and existing_analysis.generated_at is not None
        and existing_analysis.resume_id == primary_resume.id
        and existing_analysis.candidate_job_match_id
        == candidate_job_match.id
        and existing_analysis.provider == provider
        and existing_analysis.model_name == model_name
        and existing_analysis.prompt_version
        == prompt.prompt_version
        and existing_analysis.input_fingerprint_sha256
        == prompt.input_fingerprint_sha256
        and existing_analysis.source_match_updated_at
        == candidate_job_match.updated_at
        and existing_analysis.source_scoring_version
        == candidate_job_match.scoring_version
        and existing_analysis.source_resume_profile_hash
        == resume_profile.source_text_sha256
        and existing_analysis.source_job_profile_hash
        == job_profile.source_description_sha256
    )


def _create_or_reset_pending_analysis(
    session: Session,
    *,
    existing_analysis: CandidateAIAnalysis | None,
    candidate_id: UUID,
    job_id: UUID,
    primary_resume: Resume,
    candidate_job_match: CandidateJobMatch,
    resume_profile: ResumeProfile,
    job_profile: JobRequirementProfile,
    prompt: CandidateAnalysisPrompt,
    provider: str,
    model_name: str,
) -> CandidateAIAnalysis:
    source_resume_profile_hash = (
        resume_profile.source_text_sha256
    )
    source_job_profile_hash = (
        job_profile.source_description_sha256
    )

    if (
        source_resume_profile_hash is None
        or source_job_profile_hash is None
    ):
        raise AppException(
            status_code=status.HTTP_409_CONFLICT,
            code="candidate_ai_analysis_source_not_ready",
            message=(
                "The structured source profiles are not ready "
                "for AI analysis."
            ),
        )

    if existing_analysis is None:
        return create_analysis_record(
            session,
            candidate_id=candidate_id,
            job_id=job_id,
            resume_id=primary_resume.id,
            candidate_job_match_id=candidate_job_match.id,
            provider=provider,
            model_name=model_name,
            prompt_version=prompt.prompt_version,
            input_fingerprint_sha256=(
                prompt.input_fingerprint_sha256
            ),
            source_match_updated_at=(
                candidate_job_match.updated_at
            ),
            source_scoring_version=(
                candidate_job_match.scoring_version
            ),
            source_resume_profile_hash=(
                source_resume_profile_hash
            ),
            source_job_profile_hash=(
                source_job_profile_hash
            ),
        )

    return update_analysis_record(
        session,
        analysis=existing_analysis,
        resume_id=primary_resume.id,
        candidate_job_match_id=candidate_job_match.id,
        analysis_data=None,
        status="pending",
        provider=provider,
        model_name=model_name,
        prompt_version=prompt.prompt_version,
        input_fingerprint_sha256=(
            prompt.input_fingerprint_sha256
        ),
        source_match_updated_at=(
            candidate_job_match.updated_at
        ),
        source_scoring_version=(
            candidate_job_match.scoring_version
        ),
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


def _mark_analysis_failed(
    session: Session,
    *,
    analysis: CandidateAIAnalysis,
    primary_resume: Resume,
    candidate_job_match: CandidateJobMatch,
    resume_profile: ResumeProfile,
    job_profile: JobRequirementProfile,
    prompt: CandidateAnalysisPrompt,
    provider: str,
    model_name: str,
    error: StructuredLLMError,
) -> CandidateAIAnalysis:
    source_resume_profile_hash = (
        resume_profile.source_text_sha256
    )
    source_job_profile_hash = (
        job_profile.source_description_sha256
    )

    if (
        source_resume_profile_hash is None
        or source_job_profile_hash is None
    ):
        raise AppException(
            status_code=status.HTTP_409_CONFLICT,
            code="candidate_ai_analysis_source_not_ready",
            message=(
                "The structured source profiles are not ready "
                "for AI analysis."
            ),
        )

    return update_analysis_record(
        session,
        analysis=analysis,
        resume_id=primary_resume.id,
        candidate_job_match_id=candidate_job_match.id,
        analysis_data=None,
        status="failed",
        provider=provider,
        model_name=model_name,
        prompt_version=prompt.prompt_version,
        input_fingerprint_sha256=(
            prompt.input_fingerprint_sha256
        ),
        source_match_updated_at=(
            candidate_job_match.updated_at
        ),
        source_scoring_version=(
            candidate_job_match.scoring_version
        ),
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
        error_code=error.code,
        error_message=str(error),
        generated_at=datetime.now(UTC),
    )


def _structured_llm_error_status(
    error: StructuredLLMError,
) -> int:
    if (
        error.retryable
        or isinstance(
            error,
            StructuredLLMConfigurationError,
        )
    ):
        return status.HTTP_503_SERVICE_UNAVAILABLE

    return status.HTTP_502_BAD_GATEWAY


def generate_candidate_ai_analysis(
    session: Session,
    *,
    candidate_id: UUID,
    job_id: UUID,
    llm_client: StructuredLLMClient,
    force: bool = False,
) -> CandidateAIAnalysis:
    provider, model_name = _get_llm_identity_or_raise(
        llm_client
    )

    try:
        _get_candidate_or_raise(
            session,
            candidate_id,
        )
        _get_job_or_raise(
            session,
            job_id,
        )

        primary_resume = _get_primary_resume_or_raise(
            session,
            candidate_id,
        )

        resume_profile = (
            _get_completed_resume_profile_or_raise(
                session,
                resume_id=primary_resume.id,
            )
        )
        job_profile = _get_completed_job_profile_or_raise(
            session,
            job_id=job_id,
        )

        candidate_job_match = _get_current_match_or_raise(
            session,
            candidate_id=candidate_id,
            job_id=job_id,
            resume_profile=resume_profile,
            job_profile=job_profile,
        )

        resume_profile_data = (
            _validate_resume_profile_data(
                resume_profile
            )
        )
        job_profile_data = _validate_job_profile_data(
            job_profile
        )
        candidate_job_match_data = (
            _validate_candidate_job_match_data(
                candidate_job_match
            )
        )

        prompt = _build_prompt_or_raise(
            resume_profile_data=resume_profile_data,
            job_profile_data=job_profile_data,
            candidate_job_match_data=(
                candidate_job_match_data
            ),
        )

        existing_analysis = get_analysis_record(
            session,
            candidate_id=candidate_id,
            job_id=job_id,
        )

        if (
            existing_analysis is not None
            and not force
            and _is_existing_analysis_current(
                existing_analysis=existing_analysis,
                primary_resume=primary_resume,
                candidate_job_match=candidate_job_match,
                resume_profile=resume_profile,
                job_profile=job_profile,
                prompt=prompt,
                provider=provider,
                model_name=model_name,
            )
        ):
            return existing_analysis

        analysis = _create_or_reset_pending_analysis(
            session,
            existing_analysis=existing_analysis,
            candidate_id=candidate_id,
            job_id=job_id,
            primary_resume=primary_resume,
            candidate_job_match=candidate_job_match,
            resume_profile=resume_profile,
            job_profile=job_profile,
            prompt=prompt,
            provider=provider,
            model_name=model_name,
        )

        session.commit()
        session.refresh(analysis)

        try:
            result = llm_client.generate_structured_output(
                system_prompt=prompt.system_prompt,
                user_prompt=prompt.user_prompt,
                response_model=CandidateAIAnalysisData,
            )

            if (
                result.provider != provider
                or result.model_name != model_name
            ):
                raise StructuredLLMConfigurationError(
                    (
                        "The structured LLM result identity did "
                        "not match the configured client."
                    ),
                    provider=result.provider,
                    model_name=result.model_name,
                )

        except StructuredLLMError as exc:
            failed_analysis = _mark_analysis_failed(
                session,
                analysis=analysis,
                primary_resume=primary_resume,
                candidate_job_match=candidate_job_match,
                resume_profile=resume_profile,
                job_profile=job_profile,
                prompt=prompt,
                provider=provider,
                model_name=model_name,
                error=exc,
            )

            session.commit()
            session.refresh(failed_analysis)

            raise AppException(
                status_code=_structured_llm_error_status(
                    exc
                ),
                code=exc.code,
                message=(
                    "The AI Candidate analysis could not "
                    "be generated."
                ),
            ) from exc

        completed_analysis = update_analysis_record(
            session,
            analysis=analysis,
            resume_id=primary_resume.id,
            candidate_job_match_id=candidate_job_match.id,
            analysis_data=result.output.model_dump(
                mode="json"
            ),
            status="completed",
            provider=result.provider,
            model_name=result.model_name,
            prompt_version=prompt.prompt_version,
            input_fingerprint_sha256=(
                prompt.input_fingerprint_sha256
            ),
            source_match_updated_at=(
                candidate_job_match.updated_at
            ),
            source_scoring_version=(
                candidate_job_match.scoring_version
            ),
            source_resume_profile_hash=(
                resume_profile.source_text_sha256
            ),
            source_job_profile_hash=(
                job_profile.source_description_sha256
            ),
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            total_tokens=result.total_tokens,
            estimated_cost=result.estimated_cost,
            processing_time_ms=result.processing_time_ms,
            error_code=None,
            error_message=None,
            generated_at=datetime.now(UTC),
        )

        session.commit()
        session.refresh(completed_analysis)

        return completed_analysis

    except AppException:
        raise

    except SQLAlchemyError as exc:
        session.rollback()

        logger.exception(
            "Database error while generating an AI "
            "Candidate analysis."
        )

        raise AppException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="candidate_ai_analysis_persistence_failed",
            message=(
                "The AI Candidate analysis could not be "
                "generated or saved."
            ),
        ) from exc
