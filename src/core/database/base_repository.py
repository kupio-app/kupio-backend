from typing import Any, Optional, Sequence, TypeVar

from sqlalchemy import ColumnExpressionArgument, delete, insert, select, update, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.base import ExecutableOption

from .base_model import Base
from .mixins import SoftDeleteMixin, SoftDeletableModel

ModelType = TypeVar("ModelType", bound=Base)
SoftDeleteModelType = TypeVar("SoftDeleteModelType", bound=SoftDeletableModel)


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
        populate_existing: bool = False,
    ) -> Optional[ModelType]:
        if options is None:
            options = []

        all_conditions = list(conditions)
        if issubclass(model, SoftDeleteMixin):
            all_conditions.append(model.deleted_at.is_(None))

        stmt = (
            select(model)
            .where(*all_conditions)
            .options(*options)
            .execution_options(populate_existing=populate_existing)
        )

        return await self.session.scalar(stmt)

    async def _get_many(
        self,
        model: type[ModelType],
        *conditions: ColumnExpressionArgument[Any],
        limit: int | None = None,
        offset: int = 0,
        order_by: Sequence[ColumnExpressionArgument[Any]] | None = None,
    ) -> list[ModelType]:
        all_conditions = list(conditions)
        if issubclass(model, SoftDeleteMixin):
            all_conditions.append(model.deleted_at.is_(None))

        stmt = select(model).where(*all_conditions).limit(limit).offset(offset)
        if order_by:
            stmt = stmt.order_by(*order_by)

        return list((await self.session.scalars(stmt)).unique())

    async def _scalars_all(self, stmt) -> list:
        return list(await self.session.scalars(stmt))

    async def _add(self, model: type[ModelType], **kwargs: Any) -> ModelType:
        stmt = insert(model).values(**kwargs).returning(model)
        resp = await self.session.scalar(stmt)
        await self.session.flush()

        return resp

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
            return await self._get(model, *conditions)

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

    async def _soft_delete(
        self,
        model: type[SoftDeleteModelType],
        *conditions: ColumnExpressionArgument[Any],
        return_rowcount: bool = False,
    ) -> bool | int:
        result = await self.session.execute(
            update(model)
            .where(*conditions, model.deleted_at.is_(None))
            .values(deleted_at=func.now())
        )
        await self.session.flush()
        rowcount = int(getattr(result, "rowcount", 0))
        if return_rowcount:
            return rowcount
        return bool(rowcount > 0)

    async def _delete(
        self, model: type[ModelType], *conditions: ColumnExpressionArgument[Any]
    ) -> bool:
        result = await self.session.execute(delete(model).where(*conditions))
        await self.session.flush()
        return bool(getattr(result, "rowcount", 0) > 0)
