# kupio-backend

REST API backend for the Kupio marketplace platform. Built with FastAPI, PostgreSQL, and Redis.

## Tech Stack

- **Python 3.14+** with async/await throughout
- **FastAPI** - HTTP framework
- **SQLAlchemy 2 (async)** + **asyncpg** - ORM and PostgreSQL driver
- **Alembic** - database migrations
- **Redis** - session/token storage
- **Poetry** - dependency management
- **Ruff** - linting and formatting

## Prerequisites

| Tool | Version |
|------|---------|
| Python | 3.14+ |
| Poetry | 2.0+ |
| Docker + Docker Compose | latest |

## Quick Start (Docker)

The fastest way to get everything running:

```bash
# 1. Clone the repository
git clone <repo-url>
cd kupio-backend

# 2. Create your environment file
cp .env.dist .env
# Edit .env - at minimum set AUTH__JWT_SECRET to a random string

# 3. Start the full stack (app + PostgreSQL + Redis)
make app-run

# API is now available at http://localhost:8080
# Swagger UI: http://localhost:8080/api/docs  (only when SERVER__DEBUG=true)
```

> **Note:** The app container automatically runs migrations on startup before starting the server.

## Development Setup

For local development you run the app directly (hot-reload) while services run in Docker.

### 1. Install dependencies

```bash
poetry install
```

### 2. Set up environment variables

```bash
cp .env.dist .env
```

Open `.env` and fill in the required values (see [Environment Variables](#environment-variables) below).

### 3. Start backing services (PostgreSQL + Redis)

```bash
make app-run-services
```

### 4. Apply database migrations

```bash
make migrate
```

### 5. Run the dev server

```bash
make run
# Server starts at http://localhost:8080
```

### 6. (Optional) Install pre-commit hooks

```bash
make install-hooks
```

## Environment Variables

Copy `.env.dist` to `.env` and configure the values below.

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `POSTGRES__HOST` | yes | `localhost` | PostgreSQL host |
| `POSTGRES__PORT` | yes | `5432` | PostgreSQL port |
| `POSTGRES__DB` | yes | `kupio` | Database name |
| `POSTGRES__USER` | yes | - | Database user |
| `POSTGRES__PASSWORD` | yes | - | Database password |
| `REDIS__HOST` | yes | `localhost` | Redis host |
| `REDIS__PORT` | yes | `6379` | Redis port |
| `REDIS__PASSWORD` | no | - | Redis password (leave empty if none) |
| `REDIS__DB` | yes | `0` | Redis database index |
| `AUTH__JWT_SECRET` | yes | - | Secret key for signing JWT tokens |
| `AUTH__JWT_ALGORITHM` | no | `HS256` | JWT signing algorithm |
| `AUTH__ACCESS_TTL` | no | `15` | Access token TTL in minutes |
| `AUTH__REFRESH_TTL` | no | `7` | Refresh token TTL in days |
| `AUTH__NOT_VALIDATE_EXP` | no | `false` | Disable token expiry check (testing only) |
| `SERVER__HOST` | no | `localhost` | Server bind host |
| `SERVER__PORT` | no | `8080` | Server port |
| `SERVER__RELOAD` | no | `false` | Enable auto-reload (dev only) |
| `SERVER__DEBUG` | no | `false` | Enable debug mode and Swagger UI |
| `FIREBASE__CREDENTIALS_PATH` | yes | - | Path to Firebase service account JSON file |
| `FIREBASE__PROJECT_ID` | yes | - | Firebase project ID |

> **When running with Docker (`make app-run`):** `SERVER__HOST`, `POSTGRES__HOST`, and `REDIS__HOST` are automatically set to the correct values for the container network - you do not need to change them.

## Firebase Setup

Firebase is used for sending push notifications to mobile devices (FCM).

### 1. Generate a service account key

1. Open the [Firebase Console](https://console.firebase.google.com) and select your project
2. Go to **Project Settings** → **Service accounts**
3. Click **Generate new private key** → **Generate key**
4. A `.json` file will download — this is your credentials file

### 2. Configure the app

Place the downloaded file in the project root (or any path you prefer) and set the following in `.env`:

```env
FIREBASE__CREDENTIALS_PATH=firebase-creds.json
FIREBASE__PROJECT_ID=your-firebase-project-id
```

The path is resolved from the working directory where the server is launched (the project root when using `make run`).

> **Important:** Add the credentials file to `.gitignore` — never commit it to version control.

## Make Commands

```bash
make install           # Install Python dependencies via Poetry
make install-hooks     # Install pre-commit git hooks

make run               # Start dev server locally (requires running services)
make app-run           # Start full stack via Docker (app + db + redis)
make app-run-services  # Start PostgreSQL + Redis only via Docker
make down              # Stop all Docker services
make logs              # Follow app container logs

make migrate           # Apply pending Alembic migrations
make migration message="describe change"  # Autogenerate a new migration

make lint              # Check code style (ruff)
make reformat          # Auto-fix and format code (ruff)

make tests             # Run full test suite (starts services automatically)
```

## Running Tests

```bash
# Run full suite
make tests

# Run a specific test file or case
poetry run pytest tests/auth/test_auth.py -v
poetry run pytest tests/auth/test_auth.py::test_login -v
```

Tests use an in-memory SQLite database - no running PostgreSQL required.

## Project Structure

```
src/
├── app.py                  # FastAPI application factory
├── lifetime.py             # Startup/shutdown lifespan events
├── core/
│   ├── config/             # Pydantic settings (loaded via get_config())
│   ├── database/           # BaseRepository, UnitOfWork, session factory
│   ├── dependencies.py     # FastAPI Depends() providers
│   ├── exceptions.py       # Base domain error hierarchy
│   └── security/           # JWT and password hashing utilities
└── domains/
    ├── auth/               # Login, logout, token refresh
    ├── users/              # User profiles
    ├── categories/         # Product category tree
    └── listings/           # Marketplace listings
```

Each domain follows the pattern: `model.py` → `repository.py` → `service.py` → `router.py`.

## API

All routes are prefixed with `/api`:

| Prefix | Domain |
|--------|--------|
| `/api/auth` | Authentication (login, logout, refresh) |
| `/api/users` | User management |
| `/api/categories` | Category tree |
| `/api/listings` | Listings CRUD |

With `SERVER__DEBUG=true`, interactive docs are available at:
- Swagger UI: `http://localhost:8080/api/docs`
- ReDoc: `http://localhost:8080/api/redoc`
