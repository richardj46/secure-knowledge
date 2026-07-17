import json
import logging

from secure_knowledge_core.core.logging import (
    JsonLogFormatter,
    bind_log_context,
    request_id_context,
)


def _record(**values):
    return logging.makeLogRecord(
        {
            "name": "secure_knowledge.test",
            "levelno": logging.INFO,
            "levelname": "INFO",
            "msg": "answer.completed",
            "args": (),
            **values,
        }
    )


def test_json_log_contains_standard_context_and_metrics() -> None:
    formatter = JsonLogFormatter(
        service="api",
        environment="production",
    )
    request_token = request_id_context.set("req-123")

    try:
        with bind_log_context(
            organization_id="org-id",
            user_id="user-id",
        ):
            payload = json.loads(
                formatter.format(
                    _record(
                        answer_run_id="answer-run-id",
                        duration_ms=1840,
                        event="answer.completed",
                        input_tokens=3240,
                        output_tokens=310,
                        retrieval_run_id="retrieval-run-id",
                        status="succeeded",
                    )
                )
            )
    finally:
        request_id_context.reset(request_token)

    assert payload["level"] == "info"
    assert payload["service"] == "api"
    assert payload["environment"] == "production"
    assert payload["request_id"] == "req-123"
    assert payload["organization_id"] == "org-id"
    assert payload["user_id"] == "user-id"
    assert payload["event"] == "answer.completed"
    assert payload["duration_ms"] == 1840
    assert payload["input_tokens"] == 3240
    assert payload["output_tokens"] == 310
    assert payload["status"] == "succeeded"


def test_json_log_redacts_credentials_embeddings_and_production_content() -> None:
    formatter = JsonLogFormatter(
        service="worker",
        environment="production",
    )

    payload = json.loads(
        formatter.format(
            _record(
                answer="full answer",
                api_key="secret-key",
                input_tokens=100,
                password_hash="hash",
                prompt="full prompt",
                query_embedding=[0.1, 0.2],
            )
        )
    )

    assert payload["answer"] == "[REDACTED]"
    assert payload["api_key"] == "[REDACTED]"
    assert payload["password_hash"] == "[REDACTED]"
    assert payload["prompt"] == "[REDACTED]"
    assert payload["query_embedding"] == "[REDACTED]"
    assert payload["input_tokens"] == 100


def test_secure_development_may_log_content_but_never_credentials() -> None:
    formatter = JsonLogFormatter(
        service="api",
        environment="development",
        allow_development_content=True,
    )

    payload = json.loads(
        formatter.format(
            _record(
                answer="development answer",
                authorization="Bearer secret",
            )
        )
    )

    assert payload["answer"] == "development answer"
    assert payload["authorization"] == "[REDACTED]"


def test_unstructured_message_content_is_not_logged() -> None:
    formatter = JsonLogFormatter(
        service="api",
        environment="production",
    )
    sensitive_message = "The complete answer contains restricted content."
    record = _record(msg=sensitive_message)

    serialized = formatter.format(record)
    payload = json.loads(serialized)

    assert payload["event"] == "log.message"
    assert sensitive_message not in serialized
