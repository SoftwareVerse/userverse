# Production deployment and migrations

This guide deploys Userverse with its production container image. Use PostgreSQL
or MySQL in production; SQLite is intended only for local development and tests.

## 1. Build the image

Build once and give the image an immutable release tag:

```bash
docker build --pull -t registry.example.com/userverse:0.6.16 .
docker push registry.example.com/userverse:0.6.16
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
COR_ORIGINS__ALLOWED=["https://app.example.com"]
COR_ORIGINS__BLOCKED=[]
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
  registry.example.com/userverse:0.6.16
```

If migration fails, the entrypoint exits and the API does not start. Inspect the
failure with `docker logs userverse`.

### Multiple replicas

Do not let every replica race to migrate the same database. Run exactly one
short-lived migration container first. Passing `true` as its command lets the
normal entrypoint migrate and then exit successfully:

```bash
docker run --rm \
  --name userverse-migrate-0-6-16 \
  --env-file .env.production \
  registry.example.com/userverse:0.6.16 \
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
  registry.example.com/userverse:0.6.16
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
  registry.example.com/userverse:0.6.16 \
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
