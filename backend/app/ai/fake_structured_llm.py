from copy import deepcopy
from dataclasses import dataclass
from decimal import Decimal
from typing import Literal, Mapping, TypeVar

from pydantic import BaseModel, ValidationError

from app.ai.structured_llm import (
    StructuredLLMEmptyResponseError,
    StructuredLLMInvalidOutputError,
    StructuredLLMRateLimitError,
    StructuredLLMResult,
    StructuredLLMTimeoutError,
    StructuredLLMUnavailableError,
)


ResponseModelT = TypeVar(
    "ResponseModelT",
    bound=BaseModel,
)


FakeStructuredLLMFailureMode = Literal[
    "timeout",
    "rate_limit",
    "unavailable",
    "empty_response",
    "invalid_output",
]


@dataclass(
    frozen=True,
    slots=True,
)
class FakeStructuredLLMRequest:
    system_prompt: str
    user_prompt: str
    response_model_name: str


class FakeStructuredLLMClient:
    def __init__(
        self,
        *,
        response_payload: Mapping[str, object] | None = None,
        failure_mode: FakeStructuredLLMFailureMode | None = None,
        provider: str = "fake",
        model_name: str = "fake-structured-llm-v1",
        input_tokens: int = 0,
        output_tokens: int = 0,
        total_tokens: int = 0,
        estimated_cost: Decimal = Decimal("0"),
        processing_time_ms: int = 0,
    ) -> None:
        normalized_provider = provider.strip()
        normalized_model_name = model_name.strip()

        if not normalized_provider:
            raise ValueError(
                "provider must not be empty."
            )

        if not normalized_model_name:
            raise ValueError(
                "model_name must not be empty."
            )

        self.provider = normalized_provider
        self.model_name = normalized_model_name

        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.total_tokens = total_tokens

        self.estimated_cost = estimated_cost
        self.processing_time_ms = processing_time_ms

        self.failure_mode = failure_mode

        self._response_payload = (
            deepcopy(dict(response_payload))
            if response_payload is not None
            else None
        )

        self.call_count = 0
        self.last_request: (
            FakeStructuredLLMRequest | None
        ) = None

    def generate_structured_output(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_model: type[ResponseModelT],
    ) -> StructuredLLMResult[ResponseModelT]:
        normalized_system_prompt = system_prompt.strip()
        normalized_user_prompt = user_prompt.strip()

        if not normalized_system_prompt:
            raise ValueError(
                "system_prompt must not be empty."
            )

        if not normalized_user_prompt:
            raise ValueError(
                "user_prompt must not be empty."
            )

        self.call_count += 1
        self.last_request = FakeStructuredLLMRequest(
            system_prompt=normalized_system_prompt,
            user_prompt=normalized_user_prompt,
            response_model_name=response_model.__name__,
        )

        if self.failure_mode == "timeout":
            raise StructuredLLMTimeoutError(
                "The fake structured LLM request timed out.",
                provider=self.provider,
                model_name=self.model_name,
            )

        if self.failure_mode == "rate_limit":
            raise StructuredLLMRateLimitError(
                "The fake structured LLM rate limit was reached.",
                provider=self.provider,
                model_name=self.model_name,
            )

        if self.failure_mode == "unavailable":
            raise StructuredLLMUnavailableError(
                "The fake structured LLM is unavailable.",
                provider=self.provider,
                model_name=self.model_name,
            )

        if self.failure_mode == "empty_response":
            raise StructuredLLMEmptyResponseError(
                "The fake structured LLM returned no output.",
                provider=self.provider,
                model_name=self.model_name,
            )

        if self.failure_mode == "invalid_output":
            raise StructuredLLMInvalidOutputError(
                "The fake structured LLM returned invalid output.",
                provider=self.provider,
                model_name=self.model_name,
            )

        if self._response_payload is None:
            raise StructuredLLMEmptyResponseError(
                "No fake structured response payload is configured.",
                provider=self.provider,
                model_name=self.model_name,
            )

        try:
            output = response_model.model_validate(
                deepcopy(self._response_payload)
            )
        except ValidationError as exc:
            raise StructuredLLMInvalidOutputError(
                (
                    "The fake structured LLM response did not "
                    "satisfy the requested response schema."
                ),
                provider=self.provider,
                model_name=self.model_name,
            ) from exc

        return StructuredLLMResult(
            output=output,
            provider=self.provider,
            model_name=self.model_name,
            input_tokens=self.input_tokens,
            output_tokens=self.output_tokens,
            total_tokens=self.total_tokens,
            estimated_cost=self.estimated_cost,
            processing_time_ms=self.processing_time_ms,
        )