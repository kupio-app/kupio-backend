project_dir = src tests

# Install dependencies
.PHONY: install
install:
	poetry install

# Install pre-commit hooks
.PHONY: install-hooks
install-hooks:
	poetry run pre-commit install

# Lint code
.PHONY: lint
lint:
	@poetry run ruff format --check --diff $(project_dir)
	@poetry run ruff check $(project_dir)

# Reformat code
.PHONY: reformat
reformat:
	@poetry run ruff check $(project_dir) --fix
	@poetry run ruff format $(project_dir)

# Make database migration
.PHONY: migration
migration:
	@poetry run alembic revision \
	  --autogenerate \
	  --rev-id $(shell python migrations/_get_next_revision_id.py) \
	  --message "$(message)"

# Apply migrations
.PHONY: migrate
migrate:
	poetry run alembic upgrade head

# Run dev server locally (requires running services)
.PHONY: run
run:
	poetry run python -O -m src run

# Start full stack (app + PostgreSQL + Redis) via Docker
.PHONY: app-run
app-run:
	docker-compose up -d --build --remove-orphans

# Start backing services only (PostgreSQL + Redis) - use alongside `make run`
.PHONY: app-run-services
app-run-services:
	docker-compose up redis db -d --remove-orphans

# Stop all Docker services
.PHONY: down
down:
	docker-compose down

# Follow app container logs
.PHONY: logs
logs:
	docker-compose logs -f app

# Run tests (starts services automatically)
.PHONY: tests
tests: app-run-services
	poetry run pytest -vv
