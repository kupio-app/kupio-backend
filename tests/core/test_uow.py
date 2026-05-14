import pytest

from src.core.database.uow import UoW


class FakeSession:
    def __init__(self) -> None:
        self.added = []
        self.added_all = []
        self.deleted = []
        self.merged = []
        self.flushed = False
        self.committed = False
        self.rolled_back = False

    def add(self, instance) -> None:
        self.added.append(instance)

    def add_all(self, instances) -> None:
        self.added_all.extend(instances)

    async def delete(self, instance) -> None:
        self.deleted.append(instance)

    async def merge(self, instance) -> None:
        self.merged.append(instance)

    async def flush(self) -> None:
        self.flushed = True

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True


async def test_uow_commit_on_success():
    session = FakeSession()

    async with UoW(session) as uow:
        uow.add("item")
        uow.add_all("a", "b")
        await uow.delete("c")
        await uow.merge("d")
        await uow.flush()

    assert session.committed is True
    assert session.rolled_back is False
    assert session.added == ["item"]
    assert session.added_all == ["a", "b"]
    assert session.deleted == ["c"]
    assert session.merged == ["d"]
    assert session.flushed is True


async def test_uow_rollback_on_error():
    session = FakeSession()

    with pytest.raises(RuntimeError):
        async with UoW(session):
            raise RuntimeError("boom")

    assert session.rolled_back is True
    assert session.committed is False
