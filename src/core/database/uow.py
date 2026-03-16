from types import TracebackType
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from .base_model import Base


class UoW:
    session: AsyncSession

    __slots__ = ("session",)

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def __aenter__(self) -> "UoW":
        return self

    async def __aexit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        if exc_type is not None:
            await self.rollback()
            return
        await self.commit()

    def add(self, instance: Base) -> None:
        self.session.add(instance)

    def add_all(self, *instances: Base) -> None:
        self.session.add_all(instances)

    async def delete(self, *instances: Base) -> None:
        for instance in instances:
            await self.session.delete(instance)

    async def merge(self, *instances: Base) -> None:
        for instance in instances:
            await self.session.merge(instance)

    async def flush(self) -> None:
        await self.session.flush()

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()
