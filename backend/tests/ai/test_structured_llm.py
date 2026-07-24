from decimal import Decimal

import pytest
from pydantic import BaseModel, Field

from app.ai.structured_llm import (
    StructuredLLMClient,
    StructuredLLMConfigurationError,
    StructuredLLMEmptyResponseError,
    StructuredLLMError,
    StructuredLLMInvalidOutputError,
    StructuredLLMRateLimitError,
    StructuredLLMResult,
    StructuredLLMTimeoutError,
    StructuredLLMUnavailableError,
)


class ExampleStructuredOutput(BaseModel):
    summary: str = Field(
        min_length=1,
        max_length=200,
    )


class ExampleStructuredLLMClient:
    def generate_structured_output(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_model: type[ExampleStructuredOutput],
    ) -> StructuredLLMResult[
        ExampleStructuredOutput
    ]:
        assert system_prompt
        assert user_prompt

        output = response_model(
            summary="Predictable structured output."
        )

        return StructuredLLMResult(
            output=output,
            provider="fake",
            model_name="fake-model-v1",
            input_tokens=0,
            output_tokens=0,
            total_tokens=0,
            estimated_cost=Decimal("0"),
            processing_time_ms=1,
        )


def test_structured_llm_client_matches_protocol() -> None:
    client = ExampleStructuredLLMClient()

    assert isinstance(
        client,
        StructuredLLMClient,
    )


def test_structured_llm_client_returns_validated_output(
) -> None:
    client = ExampleStructuredLLMClient()

    result = client.generate_structured_output(
        system_prompt="Follow the schema.",
        user_prompt="Generate a summary.",
        response_model=ExampleStructuredOutput,
    )

    assert isinstance(
        result.output,
        ExampleStructuredOutput,
    )
    assert (
        result.output.summary
        == "Predictable structured output."
    )
    assert result.provider == "fake"
    assert result.model_name == "fake-model-v1"
    assert result.total_tokens == 0
    assert result.estimated_cost == Decimal("0")


def test_structured_llm_result_normalizes_metadata(
) -> None:
    result = StructuredLLMResult(
        output=ExampleStructuredOutput(
            summary="Valid output."
        ),
        provider=" fake ",
        model_name=" fake-model-v1 ",
    )

    assert result.provider == "fake"
    assert result.model_name == "fake-model-v1"


@pytest.mark.parametrize(
    (
        "field_name",
        "field_value",
        "expected_message",
    ),
    [
        (
            "input_tokens",
            -1,
            "input_tokens must not be negative",
        ),
        (
            "output_tokens",
            -1,
            "output_tokens must not be negative",
        ),
        (
            "total_tokens",
            -1,
            "total_tokens must not be negative",
        ),
        (
            "processing_time_ms",
            -1,
            "processing_time_ms must not be negative",
        ),
    ],
)
def test_structured_llm_result_rejects_negative_values(
    field_name: str,
    field_value: int,
    expected_message: str,
) -> None:
    arguments: dict[str, object] = {
        "output": ExampleStructuredOutput(
            summary="Valid output."
        ),
        "provider": "fake",
        "model_name": "fake-model-v1",
        field_name: field_value,
    }

    with pytest.raises(
        ValueError,
        match=expected_message,
    ):
        StructuredLLMResult(**arguments)


def test_structured_llm_result_rejects_negative_cost(
) -> None:
    with pytest.raises(
        ValueError,
        match="estimated_cost must not be negative",
    ):
        StructuredLLMResult(
            output=ExampleStructuredOutput(
                summary="Valid output."
            ),
            provider="fake",
            model_name="fake-model-v1",
            estimated_cost=Decimal("-0.01"),
        )


@pytest.mark.parametrize(
    (
        "provider",
        "model_name",
        "expected_message",
    ),
    [
        (
            "",
            "fake-model-v1",
            "provider must not be empty",
        ),
        (
            "fake",
            "",
            "model_name must not be empty",
        ),
        (
            "   ",
            "fake-model-v1",
            "provider must not be empty",
        ),
        (
            "fake",
            "   ",
            "model_name must not be empty",
        ),
    ],
)
def test_structured_llm_result_requires_metadata(
    provider: str,
    model_name: str,
    expected_message: str,
) -> None:
    with pytest.raises(
        ValueError,
        match=expected_message,
    ):
        StructuredLLMResult(
            output=ExampleStructuredOutput(
                summary="Valid output."
            ),
            provider=provider,
            model_name=model_name,
        )


def test_structured_llm_result_requires_pydantic_output(
) -> None:
    with pytest.raises(
        TypeError,
        match="validated Pydantic model",
    ):
        StructuredLLMResult(
            output={  # type: ignore[arg-type]
                "summary": "Unvalidated dictionary."
            },
            provider="fake",
            model_name="fake-model-v1",
        )


@pytest.mark.parametrize(
    (
        "error_type",
        "expected_code",
        "expected_retryable",
    ),
    [
        (
            StructuredLLMConfigurationError,
            "structured_llm_not_configured",
            False,
        ),
        (
            StructuredLLMTimeoutError,
            "structured_llm_timeout",
            True,
        ),
        (
            StructuredLLMRateLimitError,
            "structured_llm_rate_limited",
            True,
        ),
        (
            StructuredLLMUnavailableError,
            "structured_llm_unavailable",
            True,
        ),
        (
            StructuredLLMInvalidOutputError,
            "structured_llm_invalid_output",
            False,
        ),
        (
            StructuredLLMEmptyResponseError,
            "structured_llm_empty_response",
            False,
        ),
    ],
)
def test_structured_llm_errors_expose_metadata(
    error_type: type[StructuredLLMError],
    expected_code: str,
    expected_retryable: bool,
) -> None:
    error = error_type(
        "Provider operation failed.",
        provider="fake",
        model_name="fake-model-v1",
    )

    assert error.code == expected_code
    assert error.retryable is expected_retryable
    assert error.provider == "fake"
    assert error.model_name == "fake-model-v1"
    assert str(error) == "Provider operation failed."


def test_structured_llm_error_requires_message() -> None:
    with pytest.raises(
        ValueError,
        match="error message must not be empty",
    ):
        StructuredLLMError("   ")