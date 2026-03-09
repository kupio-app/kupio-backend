from typing import Any, Optional, TypeVar, cast, Sequence

from fastapi import Depends
from sqlalchemy import ColumnExpressionArgument, delete, select, update, insert
from sqlalchemy.ext.asyncio import AsyncSession

from ..dependencies import get_db_session
from .uow import UoW
from .base_model import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository:
    session: AsyncSession
    uow: UoW

    def __init__(self, session: AsyncSession = Depends(get_db_session)) -> None:
        self.session = session
        self.uow = UoW(session=session)

    async def _get(
        self,
        model: type[ModelType],
        *conditions: ColumnExpressionArgument[Any],
    ) -> Optional[ModelType]:
        return cast(
            Optional[ModelType],
            await self.session.scalar(select(model).where(*conditions)),
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

    async def _add(self, model: type[ModelType], **kwargs) -> ModelType:
        stmt = insert(model).values(**kwargs).returning(model)
        resp = await self.session.scalar(stmt)
        await self.session.commit()
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
            return cast(Optional[ModelType], await self._get(model, *conditions))

        query = update(model).where(*conditions).values(**kwargs)
        if load_result:
            query = query.returning(model)

        result = await self.session.execute(query)
        await self.session.commit()

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
        await self.session.commit()
        return cast(bool, result.rowcount > 0)
