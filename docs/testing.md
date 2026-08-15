# Testing and quality checks

Run the same fast checks used by Python CI:

```bash
make check
```

`make lint` runs Black, Ruff, yamllint, and `git diff --check`. `make coverage` runs all tests with statement coverage and writes `coverage_reports/coverage.xml`. The measured application threshold is 100%.

For a faster local loop:

```bash
make test
uv run pytest tests/api/http/a_user
uv run pytest tests/database/test_session_manager.py
```

The default suite uses isolated temporary SQLite databases for fast tests. Production-database compatibility is separately exercised by the Docker smoke workflow against PostgreSQL 17 and MySQL 8.4.

## Environment-backed HTTP tests

To deliberately validate a configured database:

```bash
uv run pytest tests/api/http --http-env-file .env
```

This mode may create, update, or seed records in the target database. Never point it at production. Without `--http-env-file`, test-safe settings and temporary storage are used.

## Container verification

Changes to dependencies, Dockerfiles, entrypoints, or migrations should run:

```bash
make docker-test
```

This uses disposable PostgreSQL and MySQL containers, scans the built production image with Trivy, applies migrations, starts the API, and checks `/` and Docker health. It does not push when invoked through the Make target.

## Pre-commit

`./scripts/setup_dev.sh` installs hooks automatically. Manual installation:

```bash
uv sync --locked --group dev
uv run pre-commit install
uv run pre-commit run --all-files
```

Hooks run Black, Ruff, yamllint, detect-secrets, and Hadolint. Review secret scanner findings; never add real credentials to the baseline.
