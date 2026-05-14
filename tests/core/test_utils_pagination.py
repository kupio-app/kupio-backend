import base64
import datetime
import json
from uuid import UUID, uuid4

from src.core.utils.pagination import (
    decode_cursor,
    decode_int_cursor,
    decode_ranked_cursor,
    decode_ranked_price_cursor,
    encode_cursor,
    encode_int_cursor,
    encode_ranked_cursor,
    encode_ranked_price_cursor,
)


def test_cursor_roundtrip_normalizes_timezone():
    created_at = datetime.datetime(2024, 1, 1, 12, 0, tzinfo=datetime.UTC)
    cursor_id = uuid4()

    cursor = encode_cursor(created_at, cursor_id)
    decoded_at, decoded_id = decode_cursor(cursor)

    assert decoded_id == cursor_id
    assert decoded_at == created_at.replace(tzinfo=None)


def test_decode_cursor_invalid_payload_returns_none():
    assert decode_cursor("not-base64") == (None, None)


def test_decode_cursor_invalid_id_returns_none():
    payload = {"created_at": "2024-01-01T00:00:00", "id": "nope"}
    cursor = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()

    assert decode_cursor(cursor) == (None, None)


def test_int_cursor_roundtrip():
    created_at = datetime.datetime(2024, 2, 1, 12, 0)
    cursor_id = 123

    cursor = encode_int_cursor(created_at, cursor_id)
    decoded_at, decoded_id = decode_int_cursor(cursor)

    assert decoded_at == created_at
    assert decoded_id == cursor_id


def test_ranked_cursor_roundtrip():
    created_at = datetime.datetime(2024, 3, 1, 8, 30)
    cursor_id = uuid4()

    cursor = encode_ranked_cursor(5, created_at, cursor_id)
    decoded_rank, decoded_at, decoded_id = decode_ranked_cursor(cursor)

    assert decoded_rank == 5
    assert decoded_at == created_at
    assert decoded_id == cursor_id


def test_ranked_cursor_invalid_returns_none_tuple():
    payload = {"created_at": "invalid", "id": str(uuid4()), "rank": "x"}
    cursor = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()

    assert decode_ranked_cursor(cursor) == (None, None, None)


def test_ranked_price_cursor_roundtrip():
    cursor_id = uuid4()
    cursor = encode_ranked_price_cursor(3, 999, cursor_id)
    decoded_rank, decoded_price, decoded_id = decode_ranked_price_cursor(cursor)

    assert decoded_rank == 3
    assert decoded_price == 999
    assert decoded_id == cursor_id


def test_ranked_price_cursor_invalid_returns_none_tuple():
    payload = {"rank": "bad", "price": 1, "id": "not-a-uuid"}
    cursor = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()

    assert decode_ranked_price_cursor(cursor) == (None, None, None)


def test_decode_cursor_missing_fields_returns_none():
    payload = {"created_at": "2024-01-01T00:00:00"}
    cursor = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()

    created_at, cursor_id = decode_cursor(cursor)
    assert created_at is None
    assert cursor_id is None


def test_decode_int_cursor_invalid_id_returns_none():
    payload = {"created_at": "2024-01-01T00:00:00", "id": "x"}
    cursor = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()

    decoded_at, decoded_id = decode_int_cursor(cursor)
    assert decoded_at is None
    assert decoded_id is None


def test_ranked_cursor_missing_rank_returns_none_tuple():
    payload = {"created_at": "2024-01-01T00:00:00", "id": str(uuid4())}
    cursor = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()

    assert decode_ranked_cursor(cursor) == (None, None, None)


def test_decode_cursor_invalid_datetime_returns_none():
    payload = {"created_at": "not-a-date", "id": str(uuid4())}
    cursor = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()

    created_at, cursor_id = decode_cursor(cursor)
    assert created_at is None
    assert cursor_id is None


def test_decode_ranked_cursor_invalid_uuid_returns_none():
    payload = {"created_at": "2024-01-01T00:00:00", "id": "bad", "rank": 1}
    cursor = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()

    assert decode_ranked_cursor(cursor) == (None, None, None)


def test_decode_ranked_price_cursor_invalid_payload_returns_none():
    assert decode_ranked_price_cursor("invalid") == (None, None, None)


def test_decode_int_cursor_invalid_datetime_returns_none():
    payload = {"created_at": "nope", "id": 1}
    cursor = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()

    decoded_at, decoded_id = decode_int_cursor(cursor)
    assert decoded_at is None
    assert decoded_id is None


def test_encode_cursor_returns_base64():
    created_at = datetime.datetime(2024, 1, 1, 0, 0)
    cursor = encode_cursor(created_at, UUID("00000000-0000-0000-0000-000000000001"))
    assert isinstance(cursor, str)
