# Configuration

Userverse configuration is loaded by `app.configs.Settings`, a `pydantic-settings` model. Values can come from process environment variables or a local `.env` file. The app no longer uses a JSON config loader or `[tool.userverse.config]` entries in `pyproject.toml` for runtime configuration.

## Core Settings

| Variable | Default | Purpose |
| --- | --- | --- |
| `ENVIRONMENT` or `ENV` | `development` | Runtime environment name. Normalized to lowercase. |
| `TESTING` | `false` | Enables test-safe behavior such as relaxed DB initialization and skipped SMTP delivery. |
| `SERVER_URL` | `http://localhost:8500` | Public base URL of the backend API service. |
| `FRONTEND_URL` | unset | Frontend reset-password route used for password reset magic links, for example `https://app.example.com/reset-password`. |
| `PASSWORD_RESET_EXPIRY_MINUTES` | `60` | Shared expiry time in minutes for both OTP and magic-link password resets. |
| `APP_NAME` | project metadata | API title. |
| `APP_DESCRIPTION` | project metadata | API description. |
| `APP_VERSION` | project metadata | API version. |
| `REPOSITORY` | project metadata | Repository URL surfaced by the root endpoint. |
| `DOCUMENTATION` | project metadata | Documentation URL surfaced by the root endpoint. |
| `REQUIRE_EMAIL_VERIFICATION` | `true` | Controls whether users must verify email before login and protected API access. |

## Database Settings

Prefer `DATABASE_URL` when the full connection string is known:

```bash
DATABASE_URL=sqlite:///./development.db
```

The app can also build a URL from parts:

```bash
DB_TYPE=postgresql
DB_USER=userverse
DB_PASSWORD=change-me
DB_NAME=userverse
DB_HOST=localhost
DB_PORT=5432
```

Supported `DB_TYPE` values are:

| `DB_TYPE` | Generated URL |
| --- | --- |
| `sqlite` | `sqlite:///{DB_NAME}` or `sqlite:///{ENVIRONMENT}.db` |
| `postgres` / `postgresql` | `postgresql+psycopg2://user:password@host:port/name` |
| `mysql` | `mysql://user:password@host:port/name` |

Additional database controls:

```bash
DB_AUTO_CREATE=false
DB_ECHO=false
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=1800
REQUIRE_EMAIL_VERIFICATION=true
```

For production databases, prefer Alembic migrations over automatic table creation. `DB_AUTO_CREATE` should generally be enabled only for local development or disposable test databases.

`DB_AUTO_CREATE` only creates a completely missing schema. It does not repair old or partially migrated schemas. If the database contains an incompatible older layout, startup now fails fast and you must run:

```bash
uv run alembic upgrade head
```

This matters in particular for older local SQLite databases created before roles were normalized into a shared global `role` catalog plus `company_role` links.

### Shared role catalog

Roles are shared by name across companies. The current model is:

- `role`: global role records such as `Owner`, `Administrator`, and `Viewer`
- `company_role`: which companies currently use each role
- `association_user_company.role_id`: the role assigned to a specific user inside a company

If you are upgrading an older database where roles were stored per company, apply Alembic migrations before using the app or env-backed HTTP test mode.

## JWT Settings

```bash
JWT_SECRET=change-this-secret
JWT_ALGORITHM=HS256
JWT_TIMEOUT=15
JWT_REFRESH_TIMEOUT=60
```

`JWT_TIMEOUT` and `JWT_REFRESH_TIMEOUT` are measured in minutes.

## Verification Settings

```bash
REQUIRE_EMAIL_VERIFICATION=true
```

When `REQUIRE_EMAIL_VERIFICATION=true`:

- New users are created with `Awaiting Verification` status.
- Unverified users cannot log in.
- JWT-protected routes reject unverified users.

When `REQUIRE_EMAIL_VERIFICATION=false`:

- New users are created as `Active`.
- Unverified users are not blocked from login or protected routes.
- Verification resend requests still return success, but no email is sent.

## Email Settings

Email rendering lives in `app/email`, and SMTP delivery is handled by `app.email.sender`.

```bash
EMAIL_HOST=smtp.example.com
EMAIL_PORT=465
EMAIL_USERNAME=no-reply@example.com
EMAIL_PASSWORD=change-me
EMAIL_SSL=true
EMAIL_TLS=false
```

In test mode (`TESTING=true` or `ENVIRONMENT=testing`), SMTP delivery is skipped.

## Password Reset Integration

Userverse supports two password reset methods through the same request endpoint:

- `otp`: sends a one-time code and keeps the existing Basic Auth completion flow.
- `magic_link`: sends a reset link to the frontend application, which must render a new-password form.

Magic links require `FRONTEND_URL` to be configured. `SERVER_URL` is the backend API origin and is not used for password reset links.

Example:

```bash
SERVER_URL=https://api.example.com
FRONTEND_URL=https://app.example.com/reset-password
PASSWORD_RESET_EXPIRY_MINUTES=60
```

Both OTP and magic-link password resets use the same `PASSWORD_RESET_EXPIRY_MINUTES` setting.

### OTP flow

Request a reset:

```bash
curl -X PATCH \
  'http://127.0.0.1:8000/password-reset/request' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{"email":"user@example.com","method":"otp"}'
```

Complete the reset with Basic Auth and the OTP:

```bash
curl -X PATCH \
  'http://127.0.0.1:8000/password-reset/validate-otp?one_time_pin=123456' \
  -H 'Authorization: Basic <base64(email:new-password)>'
```

### Magic link flow

Request a reset:

```bash
curl -X PATCH \
  'http://127.0.0.1:8000/password-reset/request' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{"email":"user@example.com","method":"magic_link"}'
```

The email contains a link in this shape:

```text
https://app.example.com/reset-password?token=<reset-token>
```

Frontend requirements:

- Expose a reset-password page at the configured `FRONTEND_URL`.
- Read the `token` query parameter.
- Render a form that collects the new password.
- Submit the new password and token to `PATCH /password-reset/reset-with-token`.
- Handle invalid or expired token errors by prompting the user to request a new reset email.

Magic-link completion request:

```bash
curl -X PATCH \
  'http://127.0.0.1:8000/password-reset/reset-with-token' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{"token":"<reset-token>","new_password":"NewPassword123!"}'
```

## CORS Settings

`CORS_ALLOWED` and `CORS_BLOCKED` accept JSON arrays or comma-separated values:

```bash
CORS_ALLOWED='["https://app.example.com", "https://admin.example.com"]'
CORS_BLOCKED='["http://localhost:3000"]'
```

The application computes allowed origins by removing blocked origins from the allowed list. If `CORS_ALLOWED` includes `"*"`, the app disables credentialed CORS responses automatically.

## Local `.env` Example

```bash
ENVIRONMENT=development
TESTING=false
SERVER_URL=http://localhost:8500
DATABASE_URL=sqlite:///./development.db
DB_AUTO_CREATE=false
JWT_SECRET=replace-with-a-long-secret
JWT_ALGORITHM=HS256
JWT_TIMEOUT=15
JWT_REFRESH_TIMEOUT=60
REQUIRE_EMAIL_VERIFICATION=true
CORS_ALLOWED='["http://localhost:3000","http://127.0.0.1:3000","http://localhost:5173","http://127.0.0.1:5173"]'
CORS_BLOCKED='["http://localhost:3000"]'
```

## Verification Resend Endpoint

The verification resend endpoint is unauthenticated and accepts only an email address:

```bash
curl -X POST \
  'http://127.0.0.1:8000/userverse/user/resend-verification' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{"email":"user@example.com"}'
```

Behavior:

- Returns success for unknown emails to avoid account enumeration.
- Returns success for already verified users without sending a new email.
- Enforces resend rate limits and returns `429` when exceeded.

## Migrations

SQLAlchemy table models live in `app/repository/database/tables`. Alembic reads metadata from `app.repository.database.Base`.

Apply migrations:

```bash
uv run alembic upgrade head
```

The current branch includes a role-catalog normalization migration for older databases. Apply migrations before reusing an existing `development.db` or any long-lived local SQLite file.

Create a migration:

```bash
uv run alembic revision --autogenerate -m "describe schema change"
```

Review autogenerated migrations before applying them to shared environments.
