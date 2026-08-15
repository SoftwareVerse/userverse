# Troubleshooting

## A database port is already in use

Identify the owner with `docker ps` or your operating system's socket tools. Either stop the conflicting local service or use `POSTGRES_PORT`/`MYSQL_PORT` and update `.env` to match.

## Docker permission denied

Confirm Docker is running. On Linux, configure Docker access according to Docker's official post-installation guidance, then start a new login session. Avoid running the whole setup script with `sudo`, because that can create root-owned project files.

## Docker Compose is missing

Userverse requires Compose v2, invoked as `docker compose`. Install or enable the Compose plugin; the legacy `docker-compose` command is not used.

## Configuration validation fails

Run:

```bash
make config-check
```

The command validates `.env` without connecting to external services or printing passwords. Production requires an explicit secure JWT secret and a PostgreSQL or MySQL URL. `EMAIL_SSL` and `EMAIL_TLS` cannot both be true.

## The database is not ready

Check service health and logs:

```bash
docker compose ps
docker compose logs postgres
docker compose logs mysql
```

Then rerun `make migrate`. Compose profiles include health checks and the setup script waits for readiness.

## `uv.lock` is stale or invalid

First confirm that `pyproject.toml` and `uv.lock` came from the same commit:

```bash
uv lock --check
```

If dependency declarations intentionally changed, regenerate with `uv lock`, review the diff, run `make check`, build the image, and run the database smoke tests. Do not hand-merge conflicting lockfile sections.

## Migration revision mismatch

Inspect state with:

```bash
uv run alembic current
uv run alembic heads
uv run alembic history --verbose
```

Do not stamp a production database merely to silence a mismatch. Determine whether migrations or schema changes are actually missing and restore from backup if a failed non-transactional migration left MySQL partially upgraded.

## The container is unhealthy

```bash
docker inspect --format '{{.State.Health.Status}}' userverse
docker logs userverse
curl --fail http://127.0.0.1:8500/
```

Migration failure prevents application startup. Verify database reachability, credentials, and the current Alembic revision first.

## GHCR authentication fails

For local publishing, authenticate with a token that has `write:packages`:

```bash
echo "$GHCR_TOKEN" | docker login ghcr.io -u "$GHCR_USERNAME" --password-stdin
```

Confirm the image namespace is lowercase and that your organization permits package publication. Pulling a truly public image does not require authentication.
