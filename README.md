[![Release Status](https://github.com/skhendle-verse/Userverse/actions/workflows/release.yml/badge.svg)](https://github.com/skhendle-verse/Userverse/actions/workflows/release.yml)

[![Build Status](https://github.com/skhendle-verse/Userverse/actions/workflows/build-and-test.yml/badge.svg)](https://github.com/skhendle-verse/Userverse/actions/workflows/build-and-test.yml)

[![codecov](https://codecov.io/gh/SoftwareVerse/Userverse/graph/badge.svg?token=8SIX9ONX0A)](https://codecov.io/gh/SoftwareVerse/Userverse)

# Userverse

Userverse is an open-source platform designed to make managing users, organizations, and their relationships simple and efficient. It’s built for developers, communities, and organizations who want a free, flexible, and secure way to handle user and organization management without relying on closed or proprietary systems.

## Directory Overview

```bash
├── alembic
│   └── versions
├── app
│   ├── database
│   ├── logic
│   │   └── user
│   │       └── repository
│   ├── middleware
│   ├── models
│   │   └── user
│   ├── routers
│   │   └── user
│   ├── security
│   └── utils
├── coverage_reports
├── docs
│   └── images
├── scripts
│   └── versions
└── tests
    ├── data
    │   ├── database
    │   └── http
    ├── database
    ├── http
    │   └── user
    └── utils
```

### Database
 - Database initialization, connection management, and session handling (engine setup, session factory)
### Logic
 - Services: Core business logic implementation (user registration, authentication flows)
 - Repositories: Data access layer for database operations with clean abstractions
### Middleware
 - Request/response processing components (CORS configuration, logging, error handlers)
### Models
 - Pydantic schema definitions for data validation and API documentation

### Routers
 - API endpoint definitions organized by resource domain (users, auth, etc.)

### Security
 - Authentication mechanisms and authorization controls (JWT, password hashing)
### Utils
 - Shared helper functions and third-party integrations (email, OTP generation)

### Docs
 - Technical documentation assets including diagrams and implementation guides

### Tests
 - Comprehensive test suite mirroring application structure for unit and integration testing


# Running the Userverse API

Userverse uses FastAPI, Uvicorn, and `pydantic-settings`. Copy the sample settings,
replace the JWT secret, then start the development server:

```bash
cp .env.example .env
openssl rand -base64 64
uv sync
uv run python -m app.main --reload --host 0.0.0.0 --port 8500
```

The sample uses SQLite. Shell variables override `.env`; nested settings use two
underscores (for example `JWT__SECRET`) and CORS lists use JSON array syntax. See
the [configuration guide](docs/configuration.md) for all settings.

You can also run Uvicorn directly:

```bash
uv run --no-sync uvicorn app.main:create_app --factory --reload --port 8500
```

## Production

```bash
uv run python -m app.main --env production --host 0.0.0.0 --port 8500 --workers 2
```

For Docker, pass the same settings without copying secrets into the image:

```bash
docker build --pull --rm -f Dockerfile -t userverse:latest .
docker run -d --name userverse --restart unless-stopped -p 8500:8500 \
  --env-file .env userverse:latest
```

The production image runs `alembic upgrade head` before starting the API. Set
`RUN_MIGRATIONS=false` only when migrations are managed as a separate deployment
job. The same `DATABASE_URL` or `DB_*` settings are used by Alembic and the app.
Both PostgreSQL and MySQL drivers are included in the image.

For complete release setup, one-off migration jobs, multi-replica deployments,
health verification, and rollback guidance, see the
[production deployment guide](docs/production.md).
