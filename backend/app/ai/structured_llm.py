from dataclasses import dataclass
from decimal import Decimal
from typing import (
    Generic,
    Protocol,
    TypeVar,
    runtime_checkable,
)

from pydantic import BaseModel


ResponseModelT = TypeVar(
    "ResponseModelT",
    bound=BaseModel,
)


@dataclass(
    frozen=True,
    slots=True,
)
class StructuredLLMResult(Generic[ResponseModelT]):
    output: ResponseModelT

    provider: str
    model_name: str

    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None

    estimated_cost: Decimal | None = None
    processing_time_ms: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.output, BaseModel):
            raise TypeError(
                "output must be a validated Pydantic model."
            )

        normalized_provider = self.provider.strip()
        normalized_model_name = self.model_name.strip()

        if not normalized_provider:
            raise ValueError(
                "provider must not be empty."
            )

        if not normalized_model_name:
            raise ValueError(
                "model_name must not be empty."
            )

        object.__setattr__(
            self,
            "provider",
            normalized_provider,
        )
        object.__setattr__(
            self,
            "model_name",
            normalized_model_name,
        )

        token_values = {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
        }

        for field_name, value in token_values.items():
            if value is not None and value < 0:
                raise ValueError(
                    f"{field_name} must not be negative."
                )

        if (
            self.estimated_cost is not None
            and self.estimated_cost < Decimal("0")
        ):
            raise ValueError(
                "estimated_cost must not be negative."
            )

        if (
            self.processing_time_ms is not None
            and self.processing_time_ms < 0
        ):
            raise ValueError(
                "processing_time_ms must not be negative."
            )


@runtime_checkable
class StructuredLLMClient(Protocol):
    @property
    def provider(self) -> str:
        ...

    @property
    def model_name(self) -> str:
        ...

    def generate_structured_output(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_model: type[ResponseModelT],
    ) -> StructuredLLMResult[ResponseModelT]:
        ...

class StructuredLLMError(Exception):
    code = "structured_llm_error"
    retryable = False

    def __init__(
        self,
        message: str,
        *,
        provider: str | None = None,
        model_name: str | None = None,
    ) -> None:
        normalized_message = message.strip()

        if not normalized_message:
            raise ValueError(
                "Structured LLM error message must not be empty."
            )

        self.provider = (
            provider.strip()
            if provider is not None
            else None
        )
        self.model_name = (
            model_name.strip()
            if model_name is not None
            else None
        )

        super().__init__(normalized_message)


class StructuredLLMConfigurationError(
    StructuredLLMError
):
    code = "structured_llm_not_configured"
    retryable = False


class StructuredLLMTimeoutError(
    StructuredLLMError
):
    code = "structured_llm_timeout"
    retryable = True


class StructuredLLMRateLimitError(
    StructuredLLMError
):
    code = "structured_llm_rate_limited"
    retryable = True


class StructuredLLMUnavailableError(
    StructuredLLMError
):
    code = "structured_llm_unavailable"
    retryable = True


class StructuredLLMInvalidOutputError(
    StructuredLLMError
):
    code = "structured_llm_invalid_output"
    retryable = False


class StructuredLLMEmptyResponseError(
    StructuredLLMError
):
    code = "structured_llm_empty_response"
    retryable = False