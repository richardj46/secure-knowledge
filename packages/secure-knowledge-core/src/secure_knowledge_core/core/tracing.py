from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from enum import Enum
from typing import Any
from uuid import UUID

from opentelemetry import trace
from opentelemetry.trace import Span, Status, StatusCode

_ALLOWED_ATTRIBUTES = frozenset(
    {
        "answer_run_id",
        "chunk_count",
        "document_id",
        "document_version_id",
        "evaluation_case_id",
        "evaluation_run_id",
        "http.method",
        "http.status_code",
        "model",
        "organization_id",
        "request_id",
        "retrieval_run_id",
        "status",
        "token_count",
        "user_id",
        "workspace_id",
    }
)

_tracer = trace.get_tracer("secure_knowledge_core")


def _normalize_attribute(value: Any) -> str | bool | int | float | None:
    if value is None:
        return None
    if isinstance(value, UUID | Enum):
        return str(value.value if isinstance(value, Enum) else value)
    if isinstance(value, str | bool | int | float):
        return value
    return None


def set_span_attributes(
    span: Span,
    attributes: Mapping[str, Any],
) -> None:
    for key, value in attributes.items():
        if key not in _ALLOWED_ATTRIBUTES:
            continue
        normalized = _normalize_attribute(value)
        if normalized is not None:
            span.set_attribute(key, normalized)


@contextmanager
def start_span(
    name: str,
    attributes: Mapping[str, Any] | None = None,
) -> Iterator[Span]:
    with _tracer.start_as_current_span(
        name,
        record_exception=False,
        set_status_on_exception=False,
    ) as span:
        set_span_attributes(span, attributes or {})
        if "status" not in (attributes or {}):
            span.set_attribute("status", "succeeded")
        try:
            yield span
        except Exception:
            span.set_attribute("status", "failed")
            span.set_status(Status(StatusCode.ERROR))
            raise
