# Configuration

Userverse loads configuration from process environment variables and `.env` using `pydantic-settings`. Process variables take precedence. Runtime configuration does not come from TOML or JSON files.

Validate configuration without connecting to the database or displaying secrets:

```bash
make config-check
# equivalent:
uv run userverse-admin config-check
```

## Core settings

| Variable | Default | Purpose |
| --- | --- | --- |
| `ENVIRONMENT` or `ENV` | `development` | Normalized runtime name. |
| `TESTING` | `false` | Enables test-safe behavior and suppresses SMTP delivery. |
| `SERVER_URL` | `http://localhost:8500` | Public backend origin. |
| `FRONTEND_URL` | unset | Frontend password-reset page used in magic links. |
| `PASSWORD_RESET_EXPIRY_MINUTES` | `60` | OTP and magic-link expiry. |
| `REQUIRE_EMAIL_VERIFICATION` | `false` | Require verified accounts for login and protected routes. |
| `ENABLE_PROFILING` | `false` | Enable optional profiling behavior. |

Project name, description, version, repository, and documentation default from `pyproject.toml` and can be overridden with `APP_NAME`, `APP_DESCRIPTION`, `APP_VERSION`, `REPOSITORY`, and `DOCUMENTATION`.

## Database

Use one SQLAlchemy URL:

```dotenv
DATABASE_URL=postgresql+psycopg2://userverse:password@db:5432/userverse
# or
DATABASE_URL=mysql+pymysql://userverse:password@db:3306/userverse
# mysql+mysqldb is also supported by the image
```

Percent-encode reserved characters in usernames and passwords. Production configuration validation accepts PostgreSQL and MySQL. SQLite is limited to development and tests.

A URL can alternatively be assembled from `DB_TYPE`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`, `DB_HOST`, and `DB_PORT`. `DATABASE_URL` takes precedence. Supported `DB_TYPE` values are `postgresql`, `postgres`, `mysql`, and development-only `sqlite`.

| Variable | Default | Purpose |
| --- | --- | --- |
| `DB_AUTO_CREATE` | `false` | Create a completely absent development schema; never repairs or migrates one. |
| `DB_ECHO` | `false` | Log SQL statements. |
| `DB_POOL_SIZE` | `5` | Persistent pool connections. |
| `DB_MAX_OVERFLOW` | `10` | Temporary connections above pool size. |
| `DB_POOL_TIMEOUT` | `30` | Pool wait timeout in seconds. |
| `DB_POOL_RECYCLE` | `1800` | Recycle age in seconds. |

Use Alembic for every shared or production schema:

```bash
make migrate
```

## JWT

```dotenv
JWT__SECRET=replace-with-at-least-32-random-bytes
JWT__ALGORITHM=HS256
JWT__TIMEOUT=15
JWT__REFRESH_TIMEOUT=60
```

Flat aliases such as `JWT_SECRET` are accepted. Outside development and testing, the built-in placeholder secret is rejected. Store production secrets in the deployment platform's secret manager.

## Email

```dotenv
EMAIL__HOST=smtp.example.com
EMAIL__PORT=587
EMAIL__USERNAME=no-reply@example.com
EMAIL__PASSWORD=replace-me
EMAIL__EMAIL_TLS=true
EMAIL__EMAIL_SSL=false
```

Flat `EMAIL_*` aliases are accepted. Do not enable SSL and TLS simultaneously. SMTP delivery is skipped when `TESTING=true` or the environment is `testing`.

## CORS

Values accept JSON arrays or comma-separated strings:

```dotenv
CORS_ALLOWED=["https://app.example.com","https://admin.example.com"]
CORS_BLOCKED=[]
```

Legacy `COR_ORIGINS__ALLOWED` and `COR_ORIGINS__BLOCKED` aliases remain supported. Blocked origins are removed from the allowed set. Credentialed CORS is disabled when the allowed list contains `*`.

## Password reset and email verification

Set `FRONTEND_URL` to the frontend route that reads the magic-link `token` query parameter and submits it with a new password to `PATCH /password-reset/reset-with-token`. `SERVER_URL` remains the backend origin.

When `REQUIRE_EMAIL_VERIFICATION=true`, new accounts cannot log in until verified. Verification resend is unauthenticated, accepts an email JSON body, is rate-limited, and returns a non-enumerating response for unknown or already verified accounts.

## Production example

```dotenv
ENVIRONMENT=production
SERVER_URL=https://users.example.com
FRONTEND_URL=https://app.example.com/reset-password
DATABASE_URL=postgresql+psycopg2://userverse:encoded-password@database:5432/userverse
JWT__SECRET=replace-with-at-least-32-random-bytes
CORS_ALLOWED=["https://app.example.com"]
CORS_BLOCKED=[]
DB_AUTO_CREATE=false
```

Run `make config-check` before deploying and follow [Production deployment](production.md).
