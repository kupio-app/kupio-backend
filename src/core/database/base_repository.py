from typing import Any, Optional, Sequence, TypeVar, cast

from sqlalchemy import ColumnExpressionArgument, delete, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.base import ExecutableOption

from .base_model import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository:
    session: AsyncSession

    __slots__ = ("session",)

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _get(
        self,
        model: type[ModelType],
        *conditions: ColumnExpressionArgument[Any],
        options: Sequence[ExecutableOption] = None,
    ) -> Optional[ModelType]:
        if options is None:
            options = []

        return cast(
            Optional[ModelType],
            await self.session.scalar(
                select(model).where(*conditions).options(*options)
            ),
        )

    async def _get_many(
        self,
        model: type[ModelType],
        *conditions: ColumnExpressionArgument[Any],
    ) -> list[ModelType]:
        return list(
            (await self.session.scalars(select(model).where(*conditions))).unique()
        )

    async def _scalars_all(self, stmt) -> list:
        return list(await self.session.scalars(stmt))

    async def _add(self, model: type[ModelType], **kwargs: Any) -> ModelType:
        stmt = insert(model).values(**kwargs).returning(model)
        resp = await self.session.scalar(stmt)
        await self.session.flush()
        return cast(ModelType, resp)

    async def _update(
        self,
        model: type[ModelType],
        conditions: list[ColumnExpressionArgument[Any]],
        load_result: bool = True,
        multiple_returning: bool = False,
        **kwargs: Any,
    ) -> Optional[ModelType] | Sequence[ModelType]:
        if not kwargs:
            if not load_result:
                return None
            return cast(Optional[ModelType], await self._get(model, *conditions))

        query = update(model).where(*conditions).values(**kwargs)
        if load_result:
            query = query.returning(model)

        result = await self.session.execute(query)
        await self.session.flush()

        if load_result:
            result = result.unique()
            return (
                result.scalar_one_or_none()
                if not multiple_returning
                else list(result.scalars())
            )

        return None

    async def _delete(
        self, model: type[ModelType], *conditions: ColumnExpressionArgument[Any]
    ) -> bool:
        result = await self.session.execute(delete(model).where(*conditions))
        await self.session.flush()
        return bool(getattr(result, "rowcount", 0) > 0)
