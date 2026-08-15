# Application configuration

Userverse reads application settings from environment variables and a `.env` file
in the current working directory. Environment variables take priority over `.env`.
Start with the tracked template:

```bash
cp .env.example .env
```

Keep `.env` out of version control. It is already ignored.

## Configuration sources

Settings are handled by `pydantic-settings` in `app/configs.py`, in this order:

1. Process environment variables (shell, container, or hosting platform)
2. Values in `.env`
3. Defaults in the settings models

`pyproject.toml` supplies default API metadata from `[project]`; it is not used for
application secrets. The old `sample-config.json`, `JSON_CONFIG_PATH`, and
`ConfigLoader` interfaces are not part of the current configuration system.

## Variables

| Variable | Purpose | Default |
| --- | --- | --- |
| `ENV` | Runtime environment | `development` |
| `SERVER_URL` | Base server URL | `http://localhost:8500` |
| `APP_NAME`, `APP_DESCRIPTION`, `APP_VERSION` | API metadata overrides | `pyproject.toml` metadata |
| `REPOSITORY`, `DOCUMENTATION` | Project URL overrides | `pyproject.toml` URLs |
| `DATABASE_URL` | Complete SQLAlchemy URL | unset |
| `DB_TYPE` | `sqlite`, `postgresql`, or `mysql` | unset |
| `DB_USER`, `DB_PASSWORD`, `DB_NAME`, `DB_HOST`, `DB_PORT` | Split database connection fields | port `5432` |
| `COR_ORIGINS__ALLOWED` | Allowed origins (JSON array) | `["*"]` |
| `COR_ORIGINS__BLOCKED` | Blocked origins (JSON array) | localhost:3000 |
| `JWT__SECRET` | Token-signing secret | development placeholder |
| `JWT__ALGORITHM` | JWT algorithm | `HS256` |
| `JWT__TIMEOUT`, `JWT__REFRESH_TIMEOUT` | Token lifetimes in minutes | `15`, `60` |
| `EMAIL__HOST`, `EMAIL__PORT` | SMTP server | unset |
| `EMAIL__USERNAME`, `EMAIL__PASSWORD` | SMTP credentials | unset |
| `EMAIL__EMAIL_TLS`, `EMAIL__EMAIL_SSL` | SMTP transport flags | unset |

`DATABASE_URL` takes precedence over `DB_*`. If neither provides a complete
connection, Userverse uses `sqlite:///<ENV>.db`. Nested values use `__`. Complex
values such as lists must be JSON:

```dotenv
COR_ORIGINS__ALLOWED=["https://app.example.com","https://admin.example.com"]
EMAIL__EMAIL_TLS=true
JWT__TIMEOUT=30
```

A production PostgreSQL configuration can use one URL:

```dotenv
ENV=production
DATABASE_URL=postgresql+psycopg2://userverse:replace-me@db:5432/userverse
JWT__SECRET=replace-with-a-long-random-secret
COR_ORIGINS__ALLOWED=["https://app.example.com"]
```

Run commands from the repository root so `.env` is discovered:

```bash
uv run python -m app.main --reload --port 8500
uv run alembic upgrade head
```

Alembic resolves the database through the same `DATABASE_URL` or `DB_*` settings
as the application. See the [production deployment guide](production.md) for the
recommended migration workflow.

## Container migrations

The container entrypoint applies `alembic upgrade head` before starting the API,
using the same `DATABASE_URL` or `DB_*` settings as the application. Startup stops
if a migration fails. In platforms where several replicas may start concurrently,
run one dedicated migration job and set `RUN_MIGRATIONS=false` on the API replicas.

Both PostgreSQL (`postgresql+psycopg2://...`) and MySQL
(`mysql+mysqldb://...` or `mysql+pymysql://...`) drivers are installed. SQLite is
kept as a development/testing fallback and is not part of the production container
workflow.
