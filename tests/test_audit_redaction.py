from secure_knowledge_core.audit.redaction import (
    REDACTED_VALUE,
    redact_audit_details,
    redact_sensitive_text,
)
from secure_knowledge_core.database.models import AuditEvent


def test_redact_audit_details_removes_nested_sensitive_values() -> None:
    details = redact_audit_details(
        {
            "target_user_id": "user-id",
            "input_tokens": 120,
            "query": "confidential question",
            "raw_embeddings": [[0.1, 0.2]],
            "authorization_header": "Bearer header-secret",
            "request": {
                "Authorization": "Bearer secret-token",
                "clientSecret": "secret-value",
            },
            "rendered_prompt": "private prompt",
        }
    )

    assert details == {
        "target_user_id": "user-id",
        "input_tokens": 120,
        "query": REDACTED_VALUE,
        "raw_embeddings": REDACTED_VALUE,
        "authorization_header": REDACTED_VALUE,
        "request": {
            "Authorization": REDACTED_VALUE,
            "clientSecret": REDACTED_VALUE,
        },
        "rendered_prompt": REDACTED_VALUE,
    }


def test_audit_details_preserve_safe_operational_metadata() -> None:
    details = {
        "target_user_id": "uuid",
        "workspace_id": "uuid",
        "role": "member",
    }

    assert redact_audit_details(details) == details


def test_audit_details_redact_every_prohibited_data_category() -> None:
    details = redact_audit_details(
        {
            "password": "secret",
            "access_token": "access-secret",
            "refresh_token": "refresh-secret",
            "gemini_api_key": "api-secret",
            "raw_embeddings": [[0.1, 0.2]],
            "complete_uploaded_document": "complete document text",
            "rendered_model_prompt": "complete prompt",
            "authorization_header": "Bearer eyJ...",
        }
    )

    assert set(details.values()) == {REDACTED_VALUE}


def test_redact_sensitive_text_removes_inline_credentials() -> None:
    message = "provider failed: api_key=secret Bearer another-secret"

    assert redact_sensitive_text(message) == (
        "provider failed: api_key=[REDACTED] Bearer [REDACTED]"
    )


def test_audit_event_redacts_direct_model_assignments() -> None:
    event = AuditEvent(
        details={"auth_token": "secret", "retry_count": 2},
        failure_message="password:secret-value",
    )

    assert event.details == {
        "auth_token": REDACTED_VALUE,
        "retry_count": 2,
    }
    assert event.failure_message == "password:[REDACTED]"
