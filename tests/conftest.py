import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

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
import src.domains.reports.models  # noqa: F401


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
async def reset_schema(engine):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


@pytest_asyncio.fixture
async def app(session_factory, monkeypatch: pytest.MonkeyPatch):
    # Keep config parsing stable for tests; DB/redis values are placeholders.
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

    get_config.cache_clear()
    app = get_app()

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
