import re
from typing import Any

REDACTED_VALUE = "[REDACTED]"

_SENSITIVE_KEYS = frozenset(
    {
        "access_token",
        "answer",
        "api_key",
        "authorization",
        "authorization_header",
        "client_secret",
        "content",
        "cookie",
        "credentials",
        "document_content",
        "document_bytes",
        "embedding",
        "embeddings",
        "file_content",
        "file_bytes",
        "full_answer",
        "id_token",
        "jwt",
        "password",
        "password_hash",
        "private_key",
        "prompt",
        "query",
        "question",
        "refresh_token",
        "raw_document",
        "secret",
        "set_cookie",
        "system_prompt",
        "token",
        "uploaded_document",
        "uploaded_file",
        "user_prompt",
    }
)
_SENSITIVE_SUFFIXES = (
    "_access_token",
    "_api_key",
    "_credential",
    "_credentials",
    "_password",
    "_private_key",
    "_refresh_token",
    "_secret",
    "_token",
    "_answer",
    "_authorization_header",
    "_content",
    "_document",
    "_embedding",
    "_embeddings",
    "_prompt",
    "_query",
    "_question",
)
_BEARER_PATTERN = re.compile(
    r"(?i)\bbearer\s+[a-z0-9._~+/=-]+",
)
_ASSIGNMENT_PATTERN = re.compile(
    r"(?i)\b(api[_-]?key|authorization|password|secret|token)"
    r"\s*([:=])\s*([^\s,;]+)",
)
_PRIVATE_KEY_PATTERN = re.compile(
    r"-----BEGIN [^-]*PRIVATE KEY-----.*?"
    r"-----END [^-]*PRIVATE KEY-----",
    re.DOTALL,
)


def redact_audit_details(details: dict[str, Any]) -> dict[str, Any]:
    return {
        str(key): _redact_value(value, key=str(key))
        for key, value in details.items()
    }


def redact_sensitive_text(value: str) -> str:
    redacted = _BEARER_PATTERN.sub("Bearer [REDACTED]", value)
    redacted = _ASSIGNMENT_PATTERN.sub(
        lambda match: (
            f"{match.group(1)}{match.group(2)}{REDACTED_VALUE}"
        ),
        redacted,
    )
    return _PRIVATE_KEY_PATTERN.sub(REDACTED_VALUE, redacted)


def _redact_value(value: Any, *, key: str | None = None) -> Any:
    if key is not None and _is_sensitive_key(key):
        return REDACTED_VALUE
    if isinstance(value, dict):
        return redact_audit_details(value)
    if isinstance(value, (list, tuple)):
        return [_redact_value(item) for item in value]
    if isinstance(value, str):
        return redact_sensitive_text(value)
    return value


def _is_sensitive_key(key: str) -> bool:
    snake_case = re.sub(r"(?<!^)(?=[A-Z])", "_", key.strip())
    normalized = snake_case.lower().replace("-", "_")
    return normalized in _SENSITIVE_KEYS or normalized.endswith(
        _SENSITIVE_SUFFIXES
    )
