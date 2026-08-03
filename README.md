[![Release Status](https://github.com/skhendle-verse/Userverse/actions/workflows/release.yml/badge.svg)](https://github.com/skhendle-verse/Userverse/actions/workflows/release.yml)

[![Build Status](https://github.com/skhendle-verse/Userverse/actions/workflows/build-and-test.yml/badge.svg)](https://github.com/skhendle-verse/Userverse/actions/workflows/build-and-test.yml)

[![codecov](https://codecov.io/gh/SoftwareVerse/Userverse/graph/badge.svg?token=8SIX9ONX0A)](https://codecov.io/gh/SoftwareVerse/Userverse)

# Userverse

Userverse is an open-source FastAPI backend for managing users, companies, roles, authentication, password resets, and company-user relationships. It is designed as a reusable identity and organization-management service with API, service, repository, and database boundaries kept separate.

## Directory Overview

```text
.
├── alembic/
│   └── versions/                  # Database migration revisions
├── app/
│   ├── api/
│   │   ├── dependencies/           # Shared FastAPI dependencies
│   │   ├── middleware/             # Logging, profiling, and OpenTelemetry middleware
│   │   ├── routers/
│   │   │   ├── company/            # Company, company-role, and company-user endpoints
│   │   │   └── user/               # User auth, profile, password, and verification endpoints
│   │   └── security/               # Basic Auth, API key, and JWT helpers
│   ├── email/                      # Email rendering, templates, and SMTP sender
│   ├── models/                     # Pydantic request/response models and enums
│   ├── repository/
│   │   └── database/
│   │       └── tables/             # SQLAlchemy table models
│   ├── services/                   # Business logic grouped by domain
│   └── utils/                      # Shared helpers: config, parsing, logging, hashing, errors
├── coverage_reports/               # Generated coverage XML output
├── docs/                           # Project documentation
├── scripts/                        # Test runner and helper scripts
└── tests/
    ├── api/
    │   ├── http/                   # FastAPI integration tests
    │   ├── middleware/             # API middleware tests
    │   └── security/               # Auth and JWT tests
    ├── data/                       # Test fixtures
    ├── database/                   # Database model/repository tests
    ├── jobs/                       # Background/job tests
    └── utils/                      # Utility and lightweight coverage tests
```

## Main Components

### API Layer

Routes live under `app/api/routers`. User routes cover account creation, login, token refresh/revocation, profile updates, email verification, and password reset. Company routes cover company CRUD, role management, and company-user membership.

### Service Layer

Business logic lives in `app/services`. Services coordinate authorization checks, repository calls, JWT generation, password reset flows, and email dispatch.

### Repository and Database Layer

Repository classes live in `app/repository`. SQLAlchemy models and session management live under `app/repository/database`. The canonical tables are `User`, `Company`, `Role`, `CompanyRole`, and `AssociationUserCompany`.

Roles are modeled as a shared global catalog. Company membership in a role is represented by `company_role`, and user assignments point at the shared role record through `association_user_company.role_id`.

### Configuration

Runtime settings are loaded from environment variables and `.env` through `app.configs.Settings`. Important variables include:

```bash
ENVIRONMENT=development
TESTING=false
SERVER_URL=http://localhost:8500
FRONTEND_URL=http://localhost:3000/reset-password
PASSWORD_RESET_EXPIRY_MINUTES=60
DATABASE_URL=sqlite:///./development.db
DB_AUTO_CREATE=false
JWT_SECRET=change-this-secret
JWT_ALGORITHM=HS256
JWT_TIMEOUT=15
JWT_REFRESH_TIMEOUT=60
REQUIRE_EMAIL_VERIFICATION=true
EMAIL_HOST=smtp.example.com
EMAIL_PORT=465
EMAIL_USERNAME=no-reply@example.com
EMAIL_PASSWORD=change-me
EMAIL_SSL=true
EMAIL_TLS=false
CORS_ALLOWED='["http://localhost:3000","http://127.0.0.1:3000","http://localhost:5173","http://127.0.0.1:5173"]'
CORS_BLOCKED='["http://localhost:3000"]'
```

See [docs/configuration.md](docs/configuration.md) for the full configuration guide.

If `REQUIRE_EMAIL_VERIFICATION=true`, users must verify their email before login and JWT-protected API access. Verification resends are handled through an unauthenticated, rate-limited email-only endpoint:

```bash
curl -X POST \
  'http://127.0.0.1:8000/userverse/user/resend-verification' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{"email":"user@example.com"}'
```

Password resets support both `otp` and `magic_link`. Magic-link emails use `FRONTEND_URL`, not `SERVER_URL`, so each deployment must point `FRONTEND_URL` at a frontend route that renders the reset-password form and then calls `PATCH /password-reset/reset-with-token`.

## Running the API

Install dependencies with `uv`:

```bash
uv sync
```

Run the API with the project CLI:

```bash
uv run -m app.main --host 0.0.0.0 --port 8500 --reload
```

Run Uvicorn directly in factory mode:

```bash
uv run uvicorn app.main:create_app --factory --reload --host 0.0.0.0 --port 8500
```

Generate a stronger JWT secret for local or production use:

```bash
openssl rand -base64 64
```

## Running Tests

Run the full CI-style HTTP and coverage suite:

```bash
./scripts/run_http_tests.sh
```

Run selected suites:

```bash
uv run pytest tests/api/http
uv run pytest tests/api/http --http-env-file .env
uv run pytest tests/api/security
uv run pytest tests/database
uv run pytest tests/utils
```

By default, `tests/api/http` uses an isolated temporary SQLite database and test-safe overrides. If you want to seed or validate a real environment-backed database, pass `--http-env-file` with a dotenv file that defines at least `DATABASE_URL`:

```bash
uv run pytest tests/api/http/c_company_roles -q --http-env-file .env
uv run pytest tests/api/http -q --http-env-file /home/sandile/projects/pj-userverse/userverse/.env
```

Use the env-backed mode carefully: it does not create an isolated temporary database, and the HTTP test fixtures may update or seed the target database.

Coverage is generated with `pytest-cov` and written to `coverage_reports/coverage.xml`. The current CI threshold is `95%`.

See [tests/README.md](tests/README.md) and [docs/testing.md](docs/testing.md) for more detail.

## Database Migrations

Apply migrations with Alembic:

```bash
uv run alembic upgrade head
```

If you have an older local SQLite database from before the shared-role catalog change, run migrations before starting the app. Current startup checks reject partial or incompatible schemas instead of silently mixing old `role` layouts with the new `company_role` model.

Create a new migration after changing SQLAlchemy table models:

```bash
uv run alembic revision --autogenerate -m "describe schema change"
```

Review autogenerated migrations before applying them.

## Docker

Build the image:

```bash
docker build --pull --rm -f Dockerfile -t userverse:latest .
```

Run the container with environment variables:

```bash
docker run -d \
  --name userverse \
  --restart unless-stopped \
  -p 8500:8500 \
  -e ENVIRONMENT=production \
  -e DATABASE_URL=postgresql+psycopg2://user:password@db:5432/userverse \
  -e JWT_SECRET=change-this-secret \
  userverse:latest
```
