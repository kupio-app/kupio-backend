import datetime
import uuid
from typing import Annotated, TypeAlias

from sqlalchemy import BigInteger, Integer, UUID as DB_UUID, func
from sqlalchemy.orm import DeclarativeBase, registry
from sqlalchemy.orm import Mapped as M, mapped_column as mc

Int16: TypeAlias = Annotated[int, 16]
Int64: TypeAlias = Annotated[int, 64]
UUID: TypeAlias = uuid.UUID


class Base(DeclarativeBase):
    registry = registry(
        type_annotation_map={
            Int16: Integer,
            UUID: DB_UUID,
            Int64: BigInteger().with_variant(Integer, "sqlite"),
        }
    )

    created_at: M[datetime.datetime] = mc(default=func.now())
    updated_at: M[datetime.datetime | None] = mc(onupdate=func.now())
