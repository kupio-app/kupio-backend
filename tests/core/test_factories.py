import types

import pytest
from fastapi import FastAPI
from sqlalchemy import URL

from src.core.factories import database as db_factory
from src.core.factories import firebase as fb_factory
from src.core.factories import redis as redis_factory
from src.core.factories import s3 as s3_factory
from src.core.factories import stripe as stripe_factory
from tests.helpers.fakes import FakeSecret


class FakePostgres:
    def __init__(self, url: URL) -> None:
        self._url = url

    def build_url(self) -> URL:
        return self._url


class FakeRedis:
    def __init__(self, url: str) -> None:
        self._url = url

    def build_url(self) -> str:
        return self._url


class FakeStripe:
    def __init__(self) -> None:
        self.secret_key = FakeSecret("sk_test")


class FakeS3:
    def __init__(self) -> None:
        self.bucket = "bucket"
        self.region = "region"
        self.access_key_id = "access"
        self.secret_access_key = FakeSecret("secret")


class FakeFirebase:
    def __init__(self, credentials_path: str, project_id: str) -> None:
        self.credentials_path = credentials_path
        self.project_id = project_id


class FakeConfig:
    def __init__(self) -> None:
        self.postgres = FakePostgres(
            URL.create("sqlite+aiosqlite", database=":memory:")
        )
        self.redis = FakeRedis("redis://localhost:6379/0")
        self.stripe = FakeStripe()
        self.s3 = FakeS3()
        self.firebase = FakeFirebase("/tmp/creds.json", "project")


async def test_init_and_shutdown_db(monkeypatch: pytest.MonkeyPatch):
    app = FastAPI()
    config = FakeConfig()

    disposed = {"called": False}

    class FakeEngine:
        async def dispose(self):
            disposed["called"] = True

    fake_engine = FakeEngine()
    fake_session_factory = object()

    monkeypatch.setattr(
        db_factory, "_create_db_pool", lambda url: (fake_engine, fake_session_factory)
    )

    engine, session_factory = db_factory.init_db(app, config)

    assert app.state.db_engine is engine
    assert app.state.db_session_factory is session_factory

    await db_factory.shutdown_db(app)
    assert disposed["called"] is True


def test_create_firebase_app_returns_none_when_missing_config():
    config = types.SimpleNamespace(firebase=FakeFirebase("", ""))
    assert fb_factory.create_firebase_app(config) is None


def test_create_firebase_app_initializes_when_configured(
    monkeypatch: pytest.MonkeyPatch,
):
    config = types.SimpleNamespace(firebase=FakeFirebase("/tmp/creds.json", "proj"))

    monkeypatch.setattr(
        fb_factory.credentials, "Certificate", lambda path: f"cred:{path}"
    )
    monkeypatch.setattr(
        fb_factory.firebase_admin, "initialize_app", lambda cred, opts: "fb_app"
    )

    assert fb_factory.create_firebase_app(config) == "fb_app"


def test_init_and_shutdown_firebase(monkeypatch: pytest.MonkeyPatch):
    app = FastAPI()

    monkeypatch.setattr(fb_factory, "create_firebase_app", lambda config: "fb_app")
    fb_factory.init_firebase(app, types.SimpleNamespace(firebase=None))
    assert app.state.firebase_app == "fb_app"

    deleted = {}

    def _delete_app(app_obj):
        deleted["app"] = app_obj

    monkeypatch.setattr(fb_factory.firebase_admin, "delete_app", _delete_app)
    fb_factory.shutdown_firebase(app)
    assert deleted["app"] == "fb_app"


async def test_init_and_shutdown_redis(monkeypatch: pytest.MonkeyPatch):
    app = FastAPI()
    config = FakeConfig()

    monkeypatch.setattr(redis_factory.ConnectionPool, "from_url", lambda url: "pool")

    class FakeRedisClient:
        def __init__(self, connection_pool):
            self.connection_pool = connection_pool

        async def aclose(self):
            return None

    monkeypatch.setattr(redis_factory, "Redis", FakeRedisClient)

    redis = redis_factory.init_redis(app, config)
    assert app.state.redis is redis
    assert redis.connection_pool == "pool"

    await redis_factory.shutdown_redis(app)


async def test_init_and_shutdown_s3(monkeypatch: pytest.MonkeyPatch):
    app = FastAPI()
    config = FakeConfig()

    class FakeService:
        def __init__(self, cfg):
            self.cfg = cfg
            self.closed = False

        def close(self):
            self.closed = True

    monkeypatch.setattr(s3_factory, "S3StorageService", FakeService)

    service = s3_factory.init_s3(app, config)
    assert app.state.s3_storage is service

    async def _run_in_threadpool(func):
        func()

    monkeypatch.setattr(s3_factory, "run_in_threadpool", _run_in_threadpool)

    await s3_factory.shutdown_s3(app)
    assert service.closed is True


def test_init_stripe(monkeypatch: pytest.MonkeyPatch):
    app = FastAPI()
    config = FakeConfig()

    monkeypatch.setattr(stripe_factory, "StripeClient", lambda key: f"client:{key}")

    client = stripe_factory.init_stripe(app, config)
    assert app.state.stripe_client == client
    assert client == "client:sk_test"
