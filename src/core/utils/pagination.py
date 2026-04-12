import base64
import binascii
import datetime
import json

from dataclasses import dataclass
from uuid import UUID
from fastapi import Query


@dataclass
class PaginationParams:
    limit: int = Query(20, gt=0, lt=200)
    cursor: str | None = None


@dataclass
class LimitOffsetPaginationParams:
    limit: int = Query(20, gt=0, lt=200)
    offset: int = Query(0, ge=0)


def _decode_cursor_payload(cursor: str) -> dict | None:
    try:
        data = json.loads(base64.urlsafe_b64decode(cursor))
    except TypeError, ValueError, binascii.Error:
        return None

    if "created_at" not in data or "id" not in data:
        return None

    return data


def _normalize_cursor_datetime(value: str) -> datetime.datetime | None:
    try:
        created_at = datetime.datetime.fromisoformat(value)
    except TypeError, ValueError:
        return None

    if created_at.tzinfo is not None:
        created_at = created_at.astimezone(datetime.UTC).replace(tzinfo=None)

    return created_at


def decode_cursor(cursor: str) -> tuple[datetime.datetime | None, UUID | None]:
    data = _decode_cursor_payload(cursor)
    if data is None:
        return None, None

    created_at = _normalize_cursor_datetime(data["created_at"])
    if created_at is None:
        return None, None

    try:
        cursor_id = UUID(data["id"])
    except TypeError, ValueError:
        return None, None

    return created_at, cursor_id


def encode_cursor(created_at: datetime.datetime, _id: UUID) -> str:
    data = {"created_at": created_at.isoformat(), "id": str(_id)}
    return base64.urlsafe_b64encode(json.dumps(data).encode()).decode()


def decode_int_cursor(cursor: str) -> tuple[datetime.datetime | None, int | None]:
    data = _decode_cursor_payload(cursor)
    if data is None:
        return None, None

    created_at = _normalize_cursor_datetime(data["created_at"])
    if created_at is None:
        return None, None

    try:
        cursor_id = int(data["id"])
    except TypeError, ValueError:
        return None, None

    return created_at, cursor_id


def encode_int_cursor(created_at: datetime.datetime, _id: int) -> str:
    data = {"created_at": created_at.isoformat(), "id": _id}
    return base64.urlsafe_b64encode(json.dumps(data).encode()).decode()
