import uuid
from typing import Annotated, TypeAlias

from sqlalchemy import BigInteger, Integer, UUID as DB_UUID
from sqlalchemy.orm import DeclarativeBase, registry

Int16: TypeAlias = Annotated[int, 16]
Int64: TypeAlias = Annotated[int, 64]
UUID: TypeAlias = uuid.UUID


class Base(DeclarativeBase):
    registry = registry(
        type_annotation_map={Int16: Integer, UUID: DB_UUID, Int64: BigInteger}
    )
