import base64
import binascii
import json
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class InvalidAdminCursorError(ValueError):
    """Raised when an admin pagination cursor cannot be decoded."""


class Page[T](BaseModel):
    items: list[T]
    next_cursor: str | None


def encode_datetime_cursor(value: datetime, item_id: UUID) -> str:
    return _encode_cursor(value=value.isoformat(), item_id=item_id)


def decode_datetime_cursor(cursor: str) -> tuple[datetime, UUID]:
    value, item_id = _decode_cursor(cursor)
    try:
        return datetime.fromisoformat(value), item_id
    except ValueError as exc:
        raise InvalidAdminCursorError("Invalid datetime cursor.") from exc


def encode_integer_cursor(value: int, item_id: UUID) -> str:
    return _encode_cursor(value=str(value), item_id=item_id)


def decode_integer_cursor(cursor: str) -> tuple[int, UUID]:
    value, item_id = _decode_cursor(cursor)
    try:
        return int(value), item_id
    except ValueError as exc:
        raise InvalidAdminCursorError("Invalid integer cursor.") from exc


def _encode_cursor(*, value: str, item_id: UUID) -> str:
    payload = json.dumps(
        {"id": str(item_id), "value": value},
        separators=(",", ":"),
    ).encode("utf-8")
    return base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")


def _decode_cursor(cursor: str) -> tuple[str, UUID]:
    try:
        padding = "=" * (-len(cursor) % 4)
        raw = base64.urlsafe_b64decode(cursor + padding)
        payload = json.loads(raw.decode("utf-8"))
        if set(payload) != {"id", "value"}:
            raise ValueError
        return str(payload["value"]), UUID(str(payload["id"]))
    except (TypeError, ValueError, binascii.Error) as exc:
        raise InvalidAdminCursorError("Invalid pagination cursor.") from exc
