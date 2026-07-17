from datetime import UTC, datetime
from uuid import uuid4

import pytest

from secure_knowledge_core.admin.pagination import (
    InvalidAdminCursorError,
    decode_datetime_cursor,
    decode_integer_cursor,
    encode_datetime_cursor,
    encode_integer_cursor,
)


def test_datetime_cursor_round_trip() -> None:
    created_at = datetime(2026, 7, 17, 12, 30, tzinfo=UTC)
    item_id = uuid4()

    cursor = encode_datetime_cursor(created_at, item_id)

    assert decode_datetime_cursor(cursor) == (created_at, item_id)
    assert created_at.isoformat() not in cursor


def test_integer_cursor_round_trip() -> None:
    item_id = uuid4()

    cursor = encode_integer_cursor(42, item_id)

    assert decode_integer_cursor(cursor) == (42, item_id)


@pytest.mark.parametrize("cursor", ["", "not-base64", "e30"])
def test_invalid_cursor_is_rejected(cursor: str) -> None:
    with pytest.raises(InvalidAdminCursorError):
        decode_datetime_cursor(cursor)
