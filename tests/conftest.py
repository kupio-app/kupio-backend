import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from src.app import get_app
from src.core.config import get_config
from src.core.database.base_model import Base
from src.core.dependencies import get_db_session

# Ensure models are registered in SQLAlchemy metadata before create_all.
import src.domains.auth.models  # noqa: F401
import src.domains.users.models  # noqa: F401
import src.domains.categories.models  # noqa: F401
import src.domains.listings.models  # noqa: F401
import src.domains.favourites.models  # noqa: F401
import src.domains.payments.models  # noqa: F401
import src.domains.promotions.models  # noqa: F401
import src.domains.images.models  # noqa: F401


@pytest_asyncio.fixture(scope="session")
async def engine(tmp_path_factory: pytest.TempPathFactory):
    db_file = tmp_path_factory.mktemp("db") / "test.sqlite3"
    db_url = f"sqlite+aiosqlite:///{db_file}"

    engine = create_async_engine(db_url)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="session")
async def session_factory(engine):
    return async_sessionmaker(engine, autoflush=False, expire_on_commit=False)


@pytest_asyncio.fixture(autouse=True)
async def reset_schema(engine: AsyncEngine):
    async with engine.begin() as conn:  # type: ignore[attr-defined]
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


@pytest_asyncio.fixture
async def app(session_factory, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("POSTGRES__HOST", "localhost")
    monkeypatch.setenv("POSTGRES__DB", "kupio_test")
    monkeypatch.setenv("POSTGRES__PASSWORD", "test")
    monkeypatch.setenv("POSTGRES__PORT", "5432")
    monkeypatch.setenv("POSTGRES__USER", "test")
    monkeypatch.setenv("REDIS__HOST", "localhost")
    monkeypatch.setenv("REDIS__PORT", "6379")
    monkeypatch.setenv("REDIS__DB", "0")
    monkeypatch.setenv("AUTH__JWT_SECRET", "test-secret")
    monkeypatch.setenv("AUTH__GOOGLE_CLIENT_IDS", '["test-google-client-id"]')
    monkeypatch.setenv("STRIPE__SECRET_KEY", "sk_test_123")
    monkeypatch.setenv("STRIPE__WEBHOOK_SECRET", "whsec_test_123")
    monkeypatch.setenv("STRIPE__SUCCESS_URL", "http://test/success")
    monkeypatch.setenv("STRIPE__CANCEL_URL", "http://test/cancel")
    monkeypatch.setenv("S3__BUCKET", "test-bucket")
    monkeypatch.setenv("S3__REGION", "test-region")
    monkeypatch.setenv("S3__ACCESS_KEY_ID", "test")
    monkeypatch.setenv("S3__SECRET_ACCESS_KEY", "test")

    get_config.cache_clear()
    app = get_app()

    # Tests don't run lifespan startup, so app.state.s3_storage isn't set.
    # Provide a tiny in-memory storage stub.
    class _StubS3Storage:
        def __init__(self, bucket: str, region: str):
            self._bucket = bucket
            self._region = region
            self._objects: dict[str, bytes] = {}

        def upload_file(self, fileobj, key: str, content_type: str) -> None:
            self._objects[key] = fileobj.read()

        def delete_object(self, key: str) -> None:
            self._objects.pop(key, None)

        def download_object(self, key: str) -> bytes:
            return self._objects[key]

    cfg = get_config()
    app.state.s3_storage = _StubS3Storage(cfg.s3.bucket, cfg.s3.region)

    async def _override_get_db_session():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = _override_get_db_session

    yield app

    app.dependency_overrides.clear()
    get_config.cache_clear()


@pytest_asyncio.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
