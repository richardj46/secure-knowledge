from __future__ import annotations

import json
import logging
import re
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import UTC, date, datetime
from enum import Enum
from typing import Any
from uuid import UUID

from secure_knowledge_core.core.settings import Settings, get_settings

request_id_context: ContextVar[str | None] = ContextVar(
    "request_id",
    default=None,
)
log_context: ContextVar[dict[str, Any] | None] = ContextVar(
    "structured_log_context",
    default=None,
)

STANDARD_FIELDS = (
    "timestamp",
    "level",
    "service",
    "environment",
    "request_id",
    "organization_id",
    "user_id",
    "resource_type",
    "resource_id",
    "event",
    "duration_ms",
    "status",
    "error_code",
)

_NEVER_LOG_FIELDS = {
    "api_key",
    "authorization",
    "embedding",
    "embeddings",
    "jwt",
    "password",
    "password_hash",
    "query_embedding",
    "raw_embedding",
    "raw_embeddings",
    "secret",
    "vector",
    "vectors",
}
_DEVELOPMENT_CONTENT_FIELDS = {
    "answer",
    "chunks",
    "content",
    "context_passages",
    "document",
    "document_content",
    "documents",
    "full_answer",
    "messages",
    "passage",
    "passages",
    "prompt",
    "raw_prompt",
    "restricted_document",
    "text",
}
_LOG_RECORD_FIELDS = frozenset(
    logging.LogRecord("", 0, "", 0, "", (), None).__dict__
) | {"asctime", "message"}
_EVENT_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_]*(?:\.[a-z0-9_]+)+$")


def _is_never_log_field(name: str) -> bool:
    normalized = name.lower()
    return normalized in _NEVER_LOG_FIELDS or normalized.endswith(
        (
            "_api_key",
            "_jwt",
            "_password",
            "_secret",
            "_secret_key",
            "_token",
        )
    )


def _sanitize(
    value: Any,
    *,
    field_name: str | None = None,
    allow_development_content: bool = False,
) -> Any:
    if field_name is not None:
        normalized = field_name.lower()
        if _is_never_log_field(normalized):
            return "[REDACTED]"
        if (
            normalized in _DEVELOPMENT_CONTENT_FIELDS
            and not allow_development_content
        ):
            return "[REDACTED]"

    if isinstance(value, Mapping):
        return {
            str(key): _sanitize(
                item,
                field_name=str(key),
                allow_development_content=allow_development_content,
            )
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple, set, frozenset)):
        return [
            _sanitize(
                item,
                allow_development_content=allow_development_content,
            )
            for item in value
        ]
    if isinstance(value, (UUID, date, datetime, Enum)):
        return str(value)
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return f"<{type(value).__name__}>"


def _normalize_event_name(value: Any) -> str:
    if isinstance(value, str) and _EVENT_NAME_PATTERN.fullmatch(value):
        return value
    return "log.message"


class JsonLogFormatter(logging.Formatter):
    def __init__(
        self,
        *,
        service: str,
        environment: str,
        allow_development_content: bool = False,
    ) -> None:
        super().__init__()
        self.service = service
        self.environment = environment
        self.allow_development_content = allow_development_content

    def format(self, record: logging.LogRecord) -> str:
        context = log_context.get() or {}
        record_values = record.__dict__
        event = _normalize_event_name(
            record_values.get("event") or record.getMessage()
        )
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname.lower(),
            "service": record_values.get("service", self.service),
            "environment": record_values.get("environment", self.environment),
            "request_id": record_values.get("request_id")
            or request_id_context.get(),
            "organization_id": record_values.get("organization_id")
            or context.get("organization_id"),
            "user_id": record_values.get("user_id") or context.get("user_id"),
            "resource_type": record_values.get("resource_type")
            or context.get("resource_type"),
            "resource_id": record_values.get("resource_id")
            or context.get("resource_id"),
            "event": event,
            "duration_ms": record_values.get("duration_ms"),
            "status": record_values.get("status"),
            "error_code": record_values.get("error_code"),
            "logger": record.name,
        }

        for key, value in context.items():
            payload.setdefault(key, value)
        for key, value in record_values.items():
            if key not in _LOG_RECORD_FIELDS and key not in payload:
                payload[key] = value
        if record.exc_info is not None and record.exc_info[0] is not None:
            payload["exception_type"] = record.exc_info[0].__name__

        sanitized = _sanitize(
            payload,
            allow_development_content=self.allow_development_content,
        )
        return json.dumps(sanitized, separators=(",", ":"), sort_keys=True)


@contextmanager
def bind_log_context(**values: Any) -> Iterator[None]:
    current = log_context.get() or {}
    token = log_context.set({**current, **values})
    try:
        yield
    finally:
        log_context.reset(token)


def configure_logging(
    *,
    service: str,
    settings: Settings | None = None,
) -> None:
    settings = settings or get_settings()
    allow_development_content = (
        settings.log_sensitive_content
        and settings.environment.lower() in {"development", "local", "test"}
    )
    handler = logging.StreamHandler()
    use_json = settings.log_json or settings.environment.lower() == "production"
    if use_json:
        handler.setFormatter(
            JsonLogFormatter(
                service=service,
                environment=settings.environment,
                allow_development_content=allow_development_content,
            )
        )
    else:
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s %(levelname)s %(name)s %(message)s"
            )
        )

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(settings.log_level.upper())


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
