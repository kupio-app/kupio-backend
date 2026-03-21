import datetime

from sqlalchemy.orm import Mapped as M, mapped_column as mc


class SoftDeleteMixin:
    deleted_at: M[datetime.datetime | None] = mc(default=None)

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None
