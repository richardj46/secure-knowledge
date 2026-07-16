from typing import Never, cast
from uuid import uuid4

import httpx
import pytest
from google import genai
from google.genai import errors, types

from secure_knowledge_core.answers.context import ContextPassage
from secure_knowledge_core.answers.schemas import CitationDraft, GeneratedAnswer
from secure_knowledge_core.database.enums import Answerability
from secure_knowledge_core.llm.exceptions import (
    LLMInvalidStructuredOutputError,
    LLMProviderRateLimitError,
    LLMProviderTimeoutError,
    LLMProviderUnavailableError,
    LLMRefusalError,
)
from secure_knowledge_core.llm.gemini_provider import GeminiAnswerProvider
from secure_knowledge_core.llm.interface import ModelUsage


class StubModels:
    def __init__(self, response: types.GenerateContentResponse) -> None:
        self.response = response
        self.received: dict[str, object] | None = None
        self.call_count = 0

    def generate_content(
        self,
        **kwargs: object,
    ) -> types.GenerateContentResponse:
        self.call_count += 1
        self.received = kwargs
        return self.response


class StubClient:
    def __init__(self, response: types.GenerateContentResponse) -> None:
        self.models = StubModels(response)


class RaisingModels:
    def __init__(self, error: Exception) -> None:
        self.error = error
        self.call_count = 0

    def generate_content(self, **kwargs: object) -> Never:
        del kwargs
        self.call_count += 1
        raise self.error


class RaisingClient:
    def __init__(self, error: Exception) -> None:
        self.models = RaisingModels(error)


def build_passage() -> ContextPassage:
    return ContextPassage(
        chunk_id=uuid4(),
        document_id=uuid4(),
        document_title="Incident Response Guide",
        page_number=7,
        section_title="Escalation",
        content="Critical incidents must be escalated immediately.",
    )


def test_gemini_provider_returns_structured_answer_and_usage() -> None:
    passage = build_passage()
    generated = GeneratedAnswer(
        answer=passage.content,
        answerability=Answerability.ANSWERABLE,
        confidence=0.9,
        citations=[
            CitationDraft(
                chunk_id=passage.chunk_id,
                claims=["Critical incidents require immediate escalation."],
            )
        ],
    )
    response = types.GenerateContentResponse(
        parsed=generated,
        response_id="gemini-request-id",
        usage_metadata=types.GenerateContentResponseUsageMetadata(
            prompt_token_count=100,
            candidates_token_count=30,
            total_token_count=130,
        ),
    )
    client = StubClient(response)
    provider = GeminiAnswerProvider(
        client=cast(genai.Client, client),
        model="gemini-test-model",
    )

    result = provider.generate_answer(
        question="How should a critical incident be escalated?",
        context=[passage],
    )

    assert result.generated_answer == generated
    assert result.model_name == "gemini-test-model"
    assert result.provider_request_id == "gemini-request-id"
    assert result.usage == ModelUsage(
        input_tokens=100,
        output_tokens=30,
        total_tokens=130,
    )
    assert client.models.received is not None
    user_input = client.models.received["contents"]
    assert isinstance(user_input, str)
    assert str(passage.chunk_id) in user_input
    assert passage.document_title in user_input


def test_gemini_provider_maps_blocked_response_to_refusal() -> None:
    response = types.GenerateContentResponse(
        parsed=None,
        prompt_feedback=types.GenerateContentResponsePromptFeedback(
            block_reason=types.BlockedReason.SAFETY,
        ),
    )
    provider = GeminiAnswerProvider(
        client=cast(genai.Client, StubClient(response)),
        model="gemini-test-model",
    )

    with pytest.raises(LLMRefusalError):
        provider.generate_answer(
            question="Question",
            context=[build_passage()],
        )


def test_gemini_provider_maps_timeout() -> None:
    client = RaisingClient(httpx.ReadTimeout("request timed out"))
    provider = GeminiAnswerProvider(
        client=cast(genai.Client, client),
        model="gemini-test-model",
    )

    with pytest.raises(LLMProviderTimeoutError):
        provider.generate_answer(
            question="Question",
            context=[build_passage()],
        )

    assert client.models.call_count == 1


def test_gemini_provider_maps_rate_limit() -> None:
    error = errors.ClientError(
        429,
        {
            "error": {
                "code": 429,
                "message": "Quota exceeded.",
                "status": "RESOURCE_EXHAUSTED",
            }
        },
    )
    client = RaisingClient(error)
    provider = GeminiAnswerProvider(
        client=cast(genai.Client, client),
        model="gemini-test-model",
    )

    with pytest.raises(LLMProviderRateLimitError):
        provider.generate_answer(
            question="Question",
            context=[build_passage()],
        )

    assert client.models.call_count == 1


def test_gemini_provider_maps_connection_failure() -> None:
    client = RaisingClient(httpx.ConnectError("connection failed"))
    provider = GeminiAnswerProvider(
        client=cast(genai.Client, client),
        model="gemini-test-model",
    )

    with pytest.raises(LLMProviderUnavailableError):
        provider.generate_answer(
            question="Question",
            context=[build_passage()],
        )

    assert client.models.call_count == 1


def test_gemini_provider_rejects_missing_parsed_output() -> None:
    client = StubClient(types.GenerateContentResponse(parsed=None))
    provider = GeminiAnswerProvider(
        client=cast(genai.Client, client),
        model="gemini-test-model",
    )

    with pytest.raises(LLMInvalidStructuredOutputError):
        provider.generate_answer(
            question="Question",
            context=[build_passage()],
        )

    assert client.models.call_count == 1


def test_gemini_provider_rejects_unknown_structured_fields() -> None:
    passage = build_passage()
    client = StubClient(
        types.GenerateContentResponse(
            parsed={
                "answer": "Supported answer.",
                "answerability": "answerable",
                "confidence": 0.8,
                "citations": [
                    {
                        "chunk_id": str(passage.chunk_id),
                        "claims": ["Supported claim."],
                    }
                ],
                "unexpected_provider_field": "must be rejected",
            }
        )
    )
    provider = GeminiAnswerProvider(
        client=cast(genai.Client, client),
        model="gemini-test-model",
    )

    with pytest.raises(LLMInvalidStructuredOutputError):
        provider.generate_answer(
            question="Question",
            context=[passage],
        )

    assert client.models.call_count == 1


def test_gemini_provider_does_not_retry_malformed_semantic_output() -> None:
    response = types.GenerateContentResponse(
        parsed={
            "answer": "Answer without citations.",
            "answerability": "answerable",
            "confidence": 0.8,
            "citations": [],
        }
    )
    client = StubClient(response)
    provider = GeminiAnswerProvider(
        client=cast(genai.Client, client),
        model="gemini-test-model",
    )

    with pytest.raises(LLMInvalidStructuredOutputError):
        provider.generate_answer(
            question="Question",
            context=[build_passage()],
        )

    assert client.models.call_count == 1
