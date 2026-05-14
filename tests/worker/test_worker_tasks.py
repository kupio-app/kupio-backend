import importlib
from contextlib import asynccontextmanager
from types import SimpleNamespace
from uuid import uuid4

import pytest

from src.core.config import get_config
from src.core.worker.schemas import FcmPushPayload


def _set_required_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("POSTGRES__HOST", "localhost")
    monkeypatch.setenv("POSTGRES__PORT", "5432")
    monkeypatch.setenv("POSTGRES__DB", "kupio_test")
    monkeypatch.setenv("POSTGRES__USER", "test")
    monkeypatch.setenv("POSTGRES__PASSWORD", "test")
    monkeypatch.setenv("REDIS__HOST", "localhost")
    monkeypatch.setenv("REDIS__PORT", "6379")
    monkeypatch.setenv("REDIS__DB", "0")
    monkeypatch.setenv("AUTH__JWT_SECRET", "test-secret")
    monkeypatch.setenv("STRIPE__SECRET_KEY", "sk_test_123")
    monkeypatch.setenv("STRIPE__WEBHOOK_SECRET", "whsec_test_123")
    monkeypatch.setenv("STRIPE__SUCCESS_URL", "http://test/success")
    monkeypatch.setenv("STRIPE__CANCEL_URL", "http://test/cancel")
    monkeypatch.setenv("S3__BUCKET", "test-bucket")
    monkeypatch.setenv("S3__REGION", "test-region")
    monkeypatch.setenv("S3__ACCESS_KEY_ID", "test")
    monkeypatch.setenv("S3__SECRET_ACCESS_KEY", "test")


class FakeSession:
    def __init__(self) -> None:
        self.committed = False

    async def commit(self) -> None:
        self.committed = True


class FakeNotificationTokens:
    def __init__(self, tokens):
        self._tokens = tokens
        self.deleted_ids = []

    async def get_tokens_for_user(self, user_id):
        return self._tokens

    async def delete_by_id(self, token_id):
        self.deleted_ids.append(token_id)


class FakeRepos:
    def __init__(self, tokens):
        self.notification_tokens = FakeNotificationTokens(tokens)


class FakeCtx:
    def __init__(self, session: FakeSession):
        self._session = session

    def session_factory(self):
        @asynccontextmanager
        async def _factory():
            yield self._session

        return _factory()


class FakeMessaging:
    class UnregisteredError(Exception):
        pass

    class Notification:
        def __init__(self, title, body):
            self.title = title
            self.body = body

    class Message:
        def __init__(self, notification, data, token):
            self.notification = notification
            self.data = data
            self.token = token

    def __init__(self):
        self.sent = []
        self.raise_unregistered = False

    def send(self, message):
        if self.raise_unregistered:
            raise FakeMessaging.UnregisteredError("unregistered")
        self.sent.append(message)


async def test_send_fcm_push_skips_when_no_tokens(monkeypatch: pytest.MonkeyPatch):
    _set_required_env(monkeypatch)
    get_config.cache_clear()

    import src.worker as worker

    importlib.reload(worker)

    fake_repos = FakeRepos([])
    monkeypatch.setattr(worker.Repositories, "from_session", lambda session: fake_repos)

    fake_messaging = FakeMessaging()
    monkeypatch.setattr(worker, "messaging", fake_messaging)

    async def _run_in_executor(_executor, func, *args):
        return func(*args)

    monkeypatch.setattr(
        worker.asyncio,
        "get_running_loop",
        lambda: SimpleNamespace(run_in_executor=_run_in_executor),
    )

    session = FakeSession()
    ctx = FakeCtx(session)

    payload = FcmPushPayload(title="t", body="b", type="x", data={"k": "v"})
    await worker.send_fcm_push(str(uuid4()), payload, ctx=ctx)

    assert fake_messaging.sent == []
    assert session.committed is False


async def test_send_fcm_push_deletes_unregistered_tokens(
    monkeypatch: pytest.MonkeyPatch,
):
    _set_required_env(monkeypatch)
    get_config.cache_clear()

    import src.worker as worker

    importlib.reload(worker)

    token = SimpleNamespace(id=uuid4(), token="tok")
    fake_repos = FakeRepos([token])
    monkeypatch.setattr(worker.Repositories, "from_session", lambda session: fake_repos)

    fake_messaging = FakeMessaging()
    fake_messaging.raise_unregistered = True
    monkeypatch.setattr(worker, "messaging", fake_messaging)

    async def _run_in_executor(_executor, func, *args):
        return func(*args)

    monkeypatch.setattr(
        worker.asyncio,
        "get_running_loop",
        lambda: SimpleNamespace(run_in_executor=_run_in_executor),
    )

    session = FakeSession()
    ctx = FakeCtx(session)

    payload = FcmPushPayload(title="t", body="b", type="x", data={})
    await worker.send_fcm_push(str(uuid4()), payload, ctx=ctx)

    assert fake_repos.notification_tokens.deleted_ids == [token.id]
    assert session.committed is True
