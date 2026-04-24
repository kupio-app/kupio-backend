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
| `STRIPE__SECRET_KEY` | yes | - | Stripe secret key (`sk_test_...` for dev) |
| `STRIPE__WEBHOOK_SECRET` | yes | - | Stripe webhook signing secret (`whsec_...`) |
| `STRIPE__SUCCESS_URL` | yes | - | Redirect URL after successful payment |
| `STRIPE__CANCEL_URL` | yes | - | Redirect URL after cancelled payment |

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
make db-reset          # Drop and recreate public schema, then apply all migrations

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

## Testing Stripe Locally

Stripe webhooks require a publicly accessible URL. In development, use the **Stripe CLI** to forward events to your local server.

### 1. Install Stripe CLI

```bash
# macOS
brew install stripe/stripe-cli/stripe

# Windows and others
Check the official installation guide: https://stripe.com/docs/stripe-cli#install
```

### 2. Authenticate

```bash
stripe login
```

This opens a browser to authorize the CLI against your Stripe account.

### 3. Forward webhooks to your local server

```bash
stripe listen --forward-to localhost:8080/api/payments/webhooks/stripe
```

The CLI prints a webhook signing secret on startup:

```
> Ready! Your webhook signing secret is whsec_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

Copy that value and set it in `.env`:

```env
STRIPE__WEBHOOK_SECRET=whsec_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

Restart the dev server after updating `.env`. Keep the `stripe listen` process running in a separate terminal - it must stay alive to receive forwarded events.

### 4. Set your Stripe test secret key

In the [Stripe Dashboard](https://dashboard.stripe.com/test/apikeys), copy the **Secret key** from the test environment (`sk_test_...`) and set:

```env
STRIPE__SECRET_KEY=sk_test_...
STRIPE__SUCCESS_URL=http://localhost:3000/payment/success
STRIPE__CANCEL_URL=http://localhost:3000/payment/cancel
```

### 5. Test the full checkout flow

**Step 1** - Create a checkout session via the API:

```bash
curl -X POST http://localhost:8080/api/payments/checkout \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"amount": 1000}'
```

The response contains a `checkout_url`. Open it in the browser and complete the payment using Stripe's test card:

| Field | Value |
|-------|-------|
| Card number | `4242 4242 4242 4242` |
| Expiry | any future date |
| CVC | any 3 digits |

After completing the payment, Stripe sends a `checkout.session.completed` event to the CLI, which forwards it to your server. The user's balance is updated automatically.

### 6. Trigger events manually (without UI)

```bash
# Simulate a completed payment
stripe trigger checkout.session.completed

# Simulate an expired session
stripe trigger checkout.session.expired
```

> **Note:** Manually triggered events use Stripe-generated test data and will not match sessions created via your API. Use them only to verify webhook handler logic in isolation.

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
    ├── filter_definitions/ # Per-category custom filter schemas
    ├── listings/           # Marketplace listings
    ├── images/             # Image upload and storage (S3)
    ├── favourites/         # User favourites
    ├── promotions/         # Promotion packets and listing promotions
    ├── payments/           # Stripe checkout, webhooks, balance transactions
    └── chat/               # Conversations, messages, WebSocket real-time layer
```

Each domain follows the pattern: `model.py` → `repository.py` → `service.py` → `router.py`.

## API

All routes are prefixed with `/api`:

| Prefix | Domain |
|--------|--------|
| `/api/auth` | Authentication (login, logout, refresh) |
| `/api/users` | User management |
| `/api/categories` | Category tree |
| `/api/categories/{id}/filters` | Per-category filter definitions |
| `/api/listings` | Listings CRUD |
| `/api/listings/favourites` | User favourites |
| `/api/listings/promotions` | Listing promotions |
| `/api/promotions/packets` | Promotion packets |
| `/api/payments` | Stripe checkout, balance transactions, webhooks |
| `/api/chat` | Conversations, messages, unread counts, WebSocket |

With `SERVER__DEBUG=true`, interactive docs are available at:
- Swagger UI: `http://localhost:8080/api/docs`
- ReDoc: `http://localhost:8080/api/redoc`

## Chat

The chat system uses REST for conversation and message management and WebSockets for real-time delivery.

**Key REST endpoints:**

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/chat/conversations` | Start or retrieve a conversation for a listing |
| `GET` | `/api/chat/conversations` | List conversations (role: `buyer` or `seller`) |
| `GET` | `/api/chat/conversations/unread-count` | Total unread message count across all conversations |
| `GET` | `/api/chat/conversations/{id}` | Get a single conversation with unread count |
| `GET` | `/api/chat/conversations/{id}/messages` | Paginated message history (also marks as read) |
| `POST` | `/api/chat/conversations/{id}/messages` | Send a message |
| `DELETE` | `/api/chat/conversations/{id}/messages/{msg_id}` | Soft-delete a message |
| `WS` | `/api/chat/conversations/{id}/ws` | Real-time WebSocket connection |

Every `ConversationResponse` includes an `unread_count` field. Messages are marked as read when the user connects via WebSocket or fetches message history via REST; a `messages_read` event is broadcast to the conversation channel so the other participant can update their UI in real time.

See [`docs/chat-websocket.md`](docs/chat-websocket.md) for the full WebSocket protocol reference.
