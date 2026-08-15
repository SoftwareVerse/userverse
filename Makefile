SHELL := /bin/bash
.DEFAULT_GOAL := help
DB ?= postgres
MIGRATION ?= describe-change

.PHONY: help setup dev db-up db-down config-check migrate migration test coverage format lint lint-docker check docs docker-build docker-test

help: ## Show available commands
	@awk 'BEGIN {FS = ":.*## "; printf "Usage: make <target>\n\n"} /^[a-zA-Z_-]+:.*## / {printf "  %-16s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

setup: ## Install dependencies and configure development (DB=postgres|mysql)
	./scripts/setup_dev.sh $(DB)

dev: ## Run the API with auto-reload
	uv run uvicorn app.main:create_app --factory --reload --host 0.0.0.0 --port 8500

db-up: ## Start the selected development database
	docker compose --profile $(DB) up --detach --wait $(DB)

db-down: ## Stop development databases without deleting data
	docker compose down

config-check: ## Validate configuration without printing secrets
	uv run userverse-admin config-check

migrate: ## Apply all database migrations
	uv run alembic upgrade head

migration: ## Generate a migration; use MIGRATION="description"
	uv run alembic revision --autogenerate -m "$(MIGRATION)"

test: ## Run all tests without coverage
	uv run pytest

coverage: ## Run tests with the required 100% coverage gate
	./scripts/run_tests.sh

format: ## Format Python code
	uv run black app tests alembic
	uv run ruff check --select E7,E9 --fix app tests alembic

lint: ## Run local static checks
	uv run black --check app tests alembic
	uv run ruff check --select E7,E9 app tests alembic
	uv run yamllint -c .yamllint.yml .github compose.yml mkdocs.yml
	git diff --check

lint-docker: ## Lint the Dockerfile with Hadolint
	./scripts/lint_dockerfile.sh

check: lint coverage ## Run the same fast checks used by CI

docs: ## Serve project documentation locally
	uv run --group docs mkdocs serve

docker-build: ## Build the production image
	docker build --tag userverse:dev .

docker-test: ## Run the full local image security and database smoke test
	./scripts/publish_image.sh --no-push
