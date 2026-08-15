[![Build Status](https://github.com/SoftwareVerse/userverse/actions/workflows/build-and-test.yml/badge.svg)](https://github.com/SoftwareVerse/userverse/actions/workflows/build-and-test.yml)
[![Docker Security](https://github.com/SoftwareVerse/userverse/actions/workflows/docker-smoke.yml/badge.svg)](https://github.com/SoftwareVerse/userverse/actions/workflows/docker-smoke.yml)
[![codecov](https://codecov.io/gh/SoftwareVerse/userverse/graph/badge.svg?token=8SIX9ONX0A)](https://codecov.io/gh/SoftwareVerse/userverse)

# Userverse

Userverse is an open-source FastAPI backend for users, companies, authentication, global and company-scoped roles, permissions, and company memberships. PostgreSQL and MySQL are supported deployment databases; SQLite is reserved for isolated development and tests.

## Developer quick start

Requirements: Git, Docker with Compose v2, [uv](https://docs.astral.sh/uv/), and OpenSSL.

```bash
git clone https://github.com/SoftwareVerse/userverse.git
cd userverse
./scripts/setup_dev.sh postgres
make dev
```

Use MySQL instead:

```bash
./scripts/setup_dev.sh mysql
make dev
```

The setup script creates `.env` only when it is missing, generates a local JWT secret, installs locked development and documentation dependencies, starts the selected database, validates configuration, applies migrations, and installs pre-commit hooks. It never overwrites an existing `.env`.

Open <http://127.0.0.1:8500/> for health and <http://127.0.0.1:8500/docs> for OpenAPI documentation.

See [Developer setup](docs/development.md) for prerequisites, manual setup, database profiles, and daily commands.

## Common commands

```bash
make help                         # list every supported command
make dev                          # start the API with reload
make config-check                 # validate .env without showing secrets
make migrate                      # apply migrations
make migration MIGRATION="name"  # create and review a migration
make test                         # run tests quickly
make coverage                     # run the required 100% coverage gate
make lint                         # Black, Ruff, YAML, and diff checks
make check                        # lint and coverage
make docs                         # serve documentation locally
make docker-build                 # build the production image
make docker-test                  # full image, Trivy, DB, and health test
```

## Configuration

Copy the sample manually when not using the setup script:

```bash
cp .env.example .env
openssl rand -hex 32
```

Set the generated value as `JWT__SECRET`, select a PostgreSQL or MySQL `DATABASE_URL`, then run:

```bash
make config-check
make migrate
```

Process environment variables override `.env`. See [Configuration](docs/configuration.md) for every supported field and production validation rule.

## Tests and quality

The repository contains 407 tests and enforces 100% statement coverage for measured application modules:

```bash
make check
```

Pre-commit runs Black, Ruff, YAML validation, secret detection, and Hadolint. Install it manually with `uv run pre-commit install` if setup was not run. See [Testing](docs/testing.md).

## Database migrations

Never rely on automatic table creation in production. Apply the migration chain deliberately:

```bash
make migrate
uv run alembic current
```

For multiple application replicas, run exactly one migration job and start API replicas with `RUN_MIGRATIONS=false`. See [Migration guide](docs/migrations.md) and [Production deployment](docs/production.md).

## Container image

The verified public image is published to:

```bash
docker pull ghcr.io/softwareverse/userverse:latest
```

Use immutable release or commit tags in production. Docker CI builds the real Dockerfile, scans it with Trivy, migrates PostgreSQL and MySQL, starts the API, and verifies `/` plus Docker health before publishing.

## Architecture and administration

- [Global and company RBAC](docs/role-permission-guide.md)
- [Superuser administration](docs/superuser-administration.md)
- [GitHub workflows](docs/github-workflows.md)
- [Troubleshooting](docs/troubleshooting.md)
- [FAQ](docs/faq.md)
