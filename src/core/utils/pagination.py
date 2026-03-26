import base64
import datetime
import json

from dataclasses import dataclass
from uuid import UUID
from fastapi import Query


@dataclass
class PaginationParams:
    limit: int = Query(20, gt=0, lt=200)
    cursor: str | None = None


def decode_cursor(cursor: str) -> tuple[datetime.datetime | None, UUID | None]:
    try:
        data = json.loads(base64.urlsafe_b64decode(cursor))
    except ValueError:
        return None, None

    if "created_at" not in data or "id" not in data:
        return None, None

    return datetime.datetime.fromisoformat(data["created_at"]), UUID(data["id"])


def encode_cursor(created_at: datetime.datetime, _id: UUID) -> str:
    data = {"created_at": created_at.isoformat(), "id": str(_id)}
    return base64.urlsafe_b64encode(json.dumps(data).encode()).decode()
