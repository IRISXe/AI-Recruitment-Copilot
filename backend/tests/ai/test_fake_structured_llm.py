from decimal import Decimal

import pytest
from pydantic import BaseModel, Field

from app.ai.fake_structured_llm import (
    FakeStructuredLLMClient,
)
from app.ai.structured_llm import (
    StructuredLLMClient,
    StructuredLLMEmptyResponseError,
    StructuredLLMInvalidOutputError,
    StructuredLLMRateLimitError,
    StructuredLLMTimeoutError,
    StructuredLLMUnavailableError,
)


class ExampleStructuredOutput(BaseModel):
    summary: str = Field(
        min_length=10,
        max_length=200,
    )

    questions: list[str] = Field(
        min_length=1,
        max_length=10,
    )


def _build_valid_payload() -> dict[str, object]:
    return {
        "summary": (
            "The candidate has relevant frontend experience."
        ),
        "questions": [
            "Describe your React application architecture.",
        ],
    }


def test_fake_client_matches_structured_llm_protocol(
) -> None:
    client = FakeStructuredLLMClient(
        response_payload=_build_valid_payload()
    )

    assert isinstance(
        client,
        StructuredLLMClient,
    )


def test_fake_client_returns_validated_output() -> None:
    client = FakeStructuredLLMClient(
        response_payload=_build_valid_payload()
    )

    result = client.generate_structured_output(
        system_prompt="Return schema-compliant output.",
        user_prompt="Analyse the candidate.",
        response_model=ExampleStructuredOutput,
    )

    assert isinstance(
        result.output,
        ExampleStructuredOutput,
    )
    assert result.output.summary == (
        "The candidate has relevant frontend experience."
    )
    assert result.provider == "fake"
    assert result.model_name == "fake-structured-llm-v1"


def test_fake_client_returns_configured_usage_metadata(
) -> None:
    client = FakeStructuredLLMClient(
        response_payload=_build_valid_payload(),
        input_tokens=100,
        output_tokens=50,
        total_tokens=150,
        estimated_cost=Decimal("0.0015"),
        processing_time_ms=25,
    )

    result = client.generate_structured_output(
        system_prompt="Return schema-compliant output.",
        user_prompt="Analyse the candidate.",
        response_model=ExampleStructuredOutput,
    )

    assert result.input_tokens == 100
    assert result.output_tokens == 50
    assert result.total_tokens == 150
    assert result.estimated_cost == Decimal("0.0015")
    assert result.processing_time_ms == 25


def test_fake_client_records_request() -> None:
    client = FakeStructuredLLMClient(
        response_payload=_build_valid_payload()
    )

    client.generate_structured_output(
        system_prompt="  System instructions.  ",
        user_prompt="  User instructions.  ",
        response_model=ExampleStructuredOutput,
    )

    assert client.call_count == 1
    assert client.last_request is not None
    assert (
        client.last_request.system_prompt
        == "System instructions."
    )
    assert (
        client.last_request.user_prompt
        == "User instructions."
    )
    assert (
        client.last_request.response_model_name
        == "ExampleStructuredOutput"
    )


def test_fake_client_returns_independent_outputs() -> None:
    client = FakeStructuredLLMClient(
        response_payload=_build_valid_payload()
    )

    first_result = client.generate_structured_output(
        system_prompt="System instructions.",
        user_prompt="First request.",
        response_model=ExampleStructuredOutput,
    )

    first_result.output.questions.append(
        "A question added after generation."
    )

    second_result = client.generate_structured_output(
        system_prompt="System instructions.",
        user_prompt="Second request.",
        response_model=ExampleStructuredOutput,
    )

    assert second_result.output.questions == [
        "Describe your React application architecture.",
    ]
    assert client.call_count == 2


@pytest.mark.parametrize(
    "system_prompt",
    [
        "",
        "   ",
    ],
)
def test_fake_client_rejects_empty_system_prompt(
    system_prompt: str,
) -> None:
    client = FakeStructuredLLMClient(
        response_payload=_build_valid_payload()
    )

    with pytest.raises(
        ValueError,
        match="system_prompt must not be empty",
    ):
        client.generate_structured_output(
            system_prompt=system_prompt,
            user_prompt="Analyse the candidate.",
            response_model=ExampleStructuredOutput,
        )


@pytest.mark.parametrize(
    "user_prompt",
    [
        "",
        "   ",
    ],
)
def test_fake_client_rejects_empty_user_prompt(
    user_prompt: str,
) -> None:
    client = FakeStructuredLLMClient(
        response_payload=_build_valid_payload()
    )

    with pytest.raises(
        ValueError,
        match="user_prompt must not be empty",
    ):
        client.generate_structured_output(
            system_prompt="System instructions.",
            user_prompt=user_prompt,
            response_model=ExampleStructuredOutput,
        )


def test_fake_client_simulates_timeout() -> None:
    client = FakeStructuredLLMClient(
        response_payload=_build_valid_payload(),
        failure_mode="timeout",
    )

    with pytest.raises(
        StructuredLLMTimeoutError,
    ) as exc_info:
        client.generate_structured_output(
            system_prompt="System instructions.",
            user_prompt="Analyse the candidate.",
            response_model=ExampleStructuredOutput,
        )

    assert exc_info.value.provider == "fake"
    assert (
        exc_info.value.model_name
        == "fake-structured-llm-v1"
    )
    assert exc_info.value.retryable is True


def test_fake_client_simulates_rate_limit() -> None:
    client = FakeStructuredLLMClient(
        response_payload=_build_valid_payload(),
        failure_mode="rate_limit",
    )

    with pytest.raises(
        StructuredLLMRateLimitError,
    ):
        client.generate_structured_output(
            system_prompt="System instructions.",
            user_prompt="Analyse the candidate.",
            response_model=ExampleStructuredOutput,
        )


def test_fake_client_simulates_unavailable_provider(
) -> None:
    client = FakeStructuredLLMClient(
        response_payload=_build_valid_payload(),
        failure_mode="unavailable",
    )

    with pytest.raises(
        StructuredLLMUnavailableError,
    ):
        client.generate_structured_output(
            system_prompt="System instructions.",
            user_prompt="Analyse the candidate.",
            response_model=ExampleStructuredOutput,
        )


def test_fake_client_simulates_empty_response() -> None:
    client = FakeStructuredLLMClient(
        response_payload=_build_valid_payload(),
        failure_mode="empty_response",
    )

    with pytest.raises(
        StructuredLLMEmptyResponseError,
    ):
        client.generate_structured_output(
            system_prompt="System instructions.",
            user_prompt="Analyse the candidate.",
            response_model=ExampleStructuredOutput,
        )


def test_fake_client_simulates_invalid_output() -> None:
    client = FakeStructuredLLMClient(
        response_payload=_build_valid_payload(),
        failure_mode="invalid_output",
    )

    with pytest.raises(
        StructuredLLMInvalidOutputError,
    ):
        client.generate_structured_output(
            system_prompt="System instructions.",
            user_prompt="Analyse the candidate.",
            response_model=ExampleStructuredOutput,
        )


def test_fake_client_rejects_payload_that_fails_schema(
) -> None:
    client = FakeStructuredLLMClient(
        response_payload={
            "summary": "Too short",
            "questions": [],
        }
    )

    with pytest.raises(
        StructuredLLMInvalidOutputError,
        match="did not satisfy",
    ) as exc_info:
        client.generate_structured_output(
            system_prompt="System instructions.",
            user_prompt="Analyse the candidate.",
            response_model=ExampleStructuredOutput,
        )

    assert exc_info.value.__cause__ is not None


def test_fake_client_requires_response_payload() -> None:
    client = FakeStructuredLLMClient()

    with pytest.raises(
        StructuredLLMEmptyResponseError,
        match="No fake structured response payload",
    ):
        client.generate_structured_output(
            system_prompt="System instructions.",
            user_prompt="Analyse the candidate.",
            response_model=ExampleStructuredOutput,
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
def test_fake_client_requires_provider_metadata(
    provider: str,
    model_name: str,
    expected_message: str,
) -> None:
    with pytest.raises(
        ValueError,
        match=expected_message,
    ):
        FakeStructuredLLMClient(
            response_payload=_build_valid_payload(),
            provider=provider,
            model_name=model_name,
        )