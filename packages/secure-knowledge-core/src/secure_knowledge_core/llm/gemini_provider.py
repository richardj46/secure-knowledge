from typing import Never

import httpx
from google import genai
from google.genai import errors, types
from pydantic import ValidationError

from secure_knowledge_core.answers.context import ContextPassage
from secure_knowledge_core.answers.schemas import GeneratedAnswer
from secure_knowledge_core.core.settings import get_settings
from secure_knowledge_core.llm.exceptions import (
    LLMInvalidStructuredOutputError,
    LLMProviderConfigurationError,
    LLMProviderError,
    LLMProviderRateLimitError,
    LLMProviderTimeoutError,
    LLMProviderUnavailableError,
    LLMRefusalError,
)
from secure_knowledge_core.llm.interface import AnswerProviderResult, ModelUsage
from secure_knowledge_core.llm.prompts import SYSTEM_INSTRUCTIONS, build_user_input

REFUSAL_FINISH_REASONS = {
    types.FinishReason.SAFETY,
    types.FinishReason.RECITATION,
    types.FinishReason.BLOCKLIST,
    types.FinishReason.PROHIBITED_CONTENT,
    types.FinishReason.SPII,
}

RETRYABLE_HTTP_STATUS_CODES = [
    408,
    429,
    500,
    502,
    503,
    504,
]


class GeminiAnswerProvider:
    provider = "gemini"

    def __init__(
        self,
        *,
        client: genai.Client | None = None,
        model: str | None = None,
    ) -> None:
        settings = get_settings() if client is None or model is None else None
        api_key = settings.gemini_api_key if settings is not None else None

        if client is None and not api_key:
            raise LLMProviderConfigurationError(
                "GEMINI_API_KEY is not configured."
            )

        if model is None:
            assert settings is not None
            model = settings.answer_model

        self.model = model

        if client is not None:
            self.client = client
            return

        assert settings is not None
        self.client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(
                timeout=int(settings.answer_model_timeout_seconds * 1000),
                retry_options=types.HttpRetryOptions(
                    attempts=settings.answer_model_max_retries + 1,
                    http_status_codes=RETRYABLE_HTTP_STATUS_CODES,
                ),
            ),
        )

    def generate_answer(
        self,
        *,
        question: str,
        context: list[ContextPassage],
    ) -> AnswerProviderResult:
        user_input = build_user_input(
            question=question,
            passages=context,
        )

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=user_input,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTIONS,
                    response_mime_type="application/json",
                    response_schema=GeneratedAnswer,
                ),
            )
        except ValidationError as exc:
            raise LLMInvalidStructuredOutputError(
                "The provider returned an invalid structured answer."
            ) from exc
        except (TimeoutError, httpx.TimeoutException) as exc:
            raise LLMProviderTimeoutError(
                "The answer provider timed out."
            ) from exc
        except httpx.ConnectError as exc:
            raise LLMProviderUnavailableError(
                "The answer provider is unavailable."
            ) from exc
        except errors.APIError as exc:
            self._raise_api_error(exc)
        except Exception as exc:
            raise LLMProviderError(
                "The answer provider request failed."
            ) from exc

        parsed = response.parsed
        if parsed is None:
            refusal_reason = self._extract_refusal_reason(response)
            if refusal_reason is not None:
                raise LLMRefusalError(refusal_reason)

            raise LLMInvalidStructuredOutputError(
                "The provider returned no structured answer."
            )

        try:
            generated_answer = GeneratedAnswer.model_validate(parsed)
        except (TypeError, ValidationError) as exc:
            raise LLMInvalidStructuredOutputError(
                "The provider returned an invalid structured answer."
            ) from exc

        usage = self._build_usage(response)

        return AnswerProviderResult(
            generated_answer=generated_answer,
            model_name=self.model,
            provider_request_id=response.response_id,
            usage=usage,
        )

    @staticmethod
    def _raise_api_error(error: errors.APIError) -> Never:
        if error.code in {408, 504}:
            raise LLMProviderTimeoutError(
                "The answer provider timed out."
            ) from error

        if error.code == 429:
            raise LLMProviderRateLimitError(
                "The answer provider rate limit was reached."
            ) from error

        if error.code >= 500:
            raise LLMProviderUnavailableError(
                "The answer provider is unavailable."
            ) from error

        raise LLMProviderError(
            "The answer provider request failed."
        ) from error

    @staticmethod
    def _extract_refusal_reason(
        response: types.GenerateContentResponse,
    ) -> str | None:
        prompt_feedback = response.prompt_feedback
        if prompt_feedback is not None and prompt_feedback.block_reason is not None:
            return "The answer provider refused the request."

        for candidate in response.candidates or []:
            if candidate.finish_reason in REFUSAL_FINISH_REASONS:
                return "The answer provider refused the request."

        return None

    @staticmethod
    def _build_usage(
        response: types.GenerateContentResponse,
    ) -> ModelUsage | None:
        metadata = response.usage_metadata
        if metadata is None:
            return None

        input_tokens = metadata.prompt_token_count or 0
        output_tokens = metadata.candidates_token_count or 0
        total_tokens = metadata.total_token_count

        return ModelUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=(
                total_tokens
                if total_tokens is not None
                else input_tokens + output_tokens
            ),
        )
