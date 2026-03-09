# Lint code
.PHONY: lint
lint:
	@poetry run ruff format --check --diff $(project_dir)
	@poetry run ruff $(project_dir)

# Reformat code
.PHONY: reformat
reformat:
	@poetry run ruff check $(project_dir) --fix
	@poetry run ruff format $(project_dir)


# Make database migration
.PHONY: migration
migration:
	poetry run alembic revision \
	  --autogenerate \
	  --rev-id $(shell python migrations/_get_next_revision_id.py) \
	  --message $(message)

.PHONY: migrate
migrate:
	poetry run alembic upgrade head

# App run
.PHONY: run
run:
    poetry run python -O -m src run

# App run
.PHONY: app-run
app-run:
	docker-compose stop
	docker-compose -f docker-compose.test.yaml up -d --build --remove-orphans

.PHONY: app-run-services
app-run-services:
	docker-compose stop
	docker-compose -f docker-compose.test.yaml up redis db -d --build --remove-orphans


.PHONY: tests
tests: app-run-services
	poetry run pytest -vv
