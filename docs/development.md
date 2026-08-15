# Developer setup

## Prerequisites

Install Git, Docker Engine or Docker Desktop with Compose v2, uv, and OpenSSL. Verify them with:

```bash
git --version
docker --version
docker compose version
uv --version
openssl version
```

## Automated setup

Choose one supported database:

```bash
./scripts/setup_dev.sh postgres
# or
./scripts/setup_dev.sh mysql
```

The script is safe to rerun. It does not overwrite `.env`; when one already exists, confirm its `DATABASE_URL` points to the database profile you selected.

PostgreSQL defaults to port 5432 and MySQL to 3306. Override occupied host ports before setup:

```bash
POSTGRES_PORT=55432 ./scripts/setup_dev.sh postgres
MYSQL_PORT=53306 ./scripts/setup_dev.sh mysql
```

When overriding a port, use the same port in `.env`.

## Manual setup

```bash
cp .env.example .env
uv sync --locked --group dev --group docs
docker compose --profile postgres up --detach --wait postgres
uv run userverse-admin config-check
uv run alembic upgrade head
uv run pre-commit install
make dev
```

For MySQL, select the `mysql` profile and use `mysql+pymysql://userverse:userverse@127.0.0.1:3306/userverse`.

## Database lifecycle

```bash
make db-up DB=postgres
make db-down
```

`make db-down` preserves named database volumes. To deliberately delete local development data, first stop Compose and then explicitly remove the relevant `userverse-dev` volume after confirming its name with `docker volume ls`.

## Daily workflow

```bash
make dev
make test
make check
make migrate
```

Run focused tests while developing:

```bash
uv run pytest tests/database/test_session_manager.py
uv run pytest tests/api/http/a_user
```

Before opening a pull request, run `make check`. Changes affecting Docker, dependencies, entrypoints, or migrations should also run `make docker-test`.

## Optional dependency groups

- `dev`: tests, formatting, linting, pre-commit, and secret detection
- `docs`: MkDocs and Material theme
- `profiling`: Memray and memory-profiler; Yappi remains runtime-required by profiling middleware

Install an optional group with:

```bash
uv sync --locked --group profiling
```
