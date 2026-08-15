# Production deployment and migrations

This guide deploys Userverse with its production container image. Use PostgreSQL
or MySQL in production; SQLite is intended only for local development and tests.

## 1. Build the image

Build once and give the image an immutable release tag:

```bash
IMAGE=ghcr.io/softwareverse/userverse:sha-0123456789abcdef
docker build --pull -t "$IMAGE" .
docker push "$IMAGE"
```

Use the same image tag for the migration job and API deployment. Do not use
`latest` when you need repeatable deployments or rollbacks.

## 2. Supply production settings

Store secrets in your platform's secret manager when possible. For a plain Docker
host, create a protected file such as `.env.production`:

```dotenv
ENV=production
SERVER_URL=https://users.example.com
DATABASE_URL=postgresql+psycopg2://userverse:replace-me@database:5432/userverse
JWT__SECRET=replace-with-at-least-32-random-bytes
CORS_ALLOWED=["https://app.example.com"]
CORS_BLOCKED=[]
```

For MySQL, use either supported driver:

```dotenv
DATABASE_URL=mysql+mysqldb://userverse:replace-me@database:3306/userverse
# Alternatively: mysql+pymysql://userverse:replace-me@database:3306/userverse
```

Percent-encode reserved characters in URL usernames and passwords. The database
and credentials must exist before migrations run. The database account needs
permission to create and alter the application's tables.

Protect a local settings file:

```bash
chmod 600 .env.production
```

Never copy this file into the image or commit it to source control.

## 3. Choose a migration strategy

### One API container

The image runs `alembic upgrade head` automatically before starting the API. A
single-container deployment can therefore use:

```bash
docker run -d \
  --name userverse \
  --restart unless-stopped \
  --env-file .env.production \
  -p 8500:8500 \
  "$IMAGE"
```

If migration fails, the entrypoint exits and the API does not start. Inspect the
failure with `docker logs userverse`.

### Multiple replicas

Do not let every replica race to migrate the same database. Run exactly one
short-lived migration container first. Passing `true` as its command lets the
normal entrypoint migrate and then exit successfully:

```bash
docker run --rm \
  --name userverse-migrate \
  --env-file .env.production \
  "$IMAGE" \
  true
```

Only after that command succeeds, start all API replicas with migrations disabled:

```bash
docker run -d \
  --name userverse-api-1 \
  --restart unless-stopped \
  --env-file .env.production \
  -e RUN_MIGRATIONS=false \
  -p 8500:8500 \
  "$IMAGE"
```

Apply the same pattern on Kubernetes, ECS, Nomad, or another orchestrator:

1. Run the release image as a one-off Job with command `true`.
2. Wait for the Job to complete successfully.
3. Roll out API replicas with `RUN_MIGRATIONS=false`.
4. Stop the rollout if the migration Job fails.

## 4. Verify the deployment

The image includes a Docker health check against `/`. Check it with:

```bash
docker inspect \
  --format '{{.State.Health.Status}}' \
  userverse

curl --fail https://users.example.com/
```

A successful root response contains `"status":"ok"`. Confirm the database revision
when troubleshooting or auditing a release:

```bash
docker run --rm \
  --entrypoint alembic \
  --env-file .env.production \
  "$IMAGE" \
  current
```

The expected current revision is the migration head shipped in that image.

## 5. Deployment order and rollback

Use this order for every release:

1. Back up the production database according to your database provider's process.
2. Build and publish an immutable image tag.
3. Run the one-off migration job.
4. Verify that Alembic reports the expected head revision.
5. Deploy the API with `RUN_MIGRATIONS=false`.
6. Verify the health endpoint and application logs.

Rolling the application image back does not automatically downgrade the database.
Alembic downgrades can destroy or transform data and must be planned and tested
separately. Prefer backward-compatible migrations that allow the previous and new
application versions to operate during a rolling deployment.

## Operational notes

- Terminate TLS at a trusted reverse proxy or load balancer.
- Do not expose the database publicly.
- Rotate database and JWT secrets through the deployment platform.
- Send container logs to centralized storage.
- Configure CPU, memory, restart, and replica limits in the orchestrator.
- Monitor both container health and the database connection pool.

## Container vulnerability scanning

The Docker CI workflow scans the built production image with Trivy before running
migrations or starting the API. It performs two image scans:

1. A SARIF scan uploads findings to the repository's **Security → Code scanning**
   view for supported GitHub repositories.
2. A policy scan fails the workflow when a fix is available for a `HIGH` or
   `CRITICAL` operating-system or Python dependency vulnerability.

Unfixed findings remain visible to Trivy but do not block deployment. Review them
regularly and rebuild images often so updated base-image packages are included.
The workflow pins both the Trivy action and Trivy binary versions; update those
pins deliberately after reviewing upstream releases and security notices.

## Public GitHub Container Registry image

After security scanning, database migration checks, and the health smoke test pass,
the workflow publishes the verified image to:

```text
ghcr.io/softwareverse/userverse
```

A push to `main` publishes `latest` and an immutable `sha-<full-commit-sha>` tag.
A Git tag such as `v0.6.17` additionally publishes `0.6.17` and `0.6`. Pull
requests, scheduled scans, and manual scans never publish images.

Pull a public image without authentication:

```bash
docker pull ghcr.io/softwareverse/userverse:latest
```

The first package version may initially be private. An organization package admin
must open the package on GitHub, choose **Package settings → Change visibility**,
and select **Public**. Confirm the package is linked to the repository; the image's
`org.opencontainers.image.source` label establishes that link during first publish.
Changing visibility is a one-time GitHub organization setting and cannot be safely
assumed by the build workflow.

### Publishing from a trusted workstation

Maintainers can run the same release checks locally with:

```bash
scripts/publish_image.sh --no-push
scripts/publish_image.sh
```

The script requires the current commit to be the latest Git tag and the working
tree to be clean. It builds the tagged image, blocks on fixable high/critical Trivy
findings, tests migrations against disposable PostgreSQL and MySQL containers,
checks API health, and then pushes both `<version>` and `latest` tags. It never uses
a production database and removes its disposable containers and network on exit.

Authenticate first with `docker login ghcr.io`, or provide `GHCR_USERNAME` and a
`GHCR_TOKEN` with `write:packages`. Use `--no-push` to exercise the entire release
process without changing the registry.
