#!/usr/bin/env bash
set -euo pipefail

DATABASE=${1:-postgres}
case "$DATABASE" in
  postgres)
    database_url="postgresql+psycopg2://userverse:userverse@127.0.0.1:${POSTGRES_PORT:-5432}/userverse"
    ;;
  mysql)
    database_url="mysql+pymysql://userverse:userverse@127.0.0.1:${MYSQL_PORT:-3306}/userverse"
    ;;
  *)
    echo "Usage: $0 [postgres|mysql]" >&2
    exit 2
    ;;
esac

for command_name in uv docker openssl; do
  if ! command -v "$command_name" >/dev/null 2>&1; then
    echo "Required command not found: $command_name" >&2
    exit 1
  fi
done
if ! docker compose version >/dev/null 2>&1; then
  echo "Docker Compose v2 is required (docker compose)." >&2
  exit 1
fi

if [ ! -f .env ]; then
  cp .env.example .env
  jwt_secret=$(openssl rand -hex 32)
  sed -i "s|^DATABASE_URL=.*|DATABASE_URL=$database_url|" .env
  sed -i "s|^JWT__SECRET=.*|JWT__SECRET=$jwt_secret|" .env
  echo "Created .env for $DATABASE development."
else
  echo "Keeping existing .env unchanged. Confirm DATABASE_URL targets $DATABASE."
fi

uv sync --locked --group dev --group docs
docker compose --profile "$DATABASE" up --detach --wait "$DATABASE"
uv run userverse-admin config-check
uv run alembic upgrade head
uv run pre-commit install

echo
echo "Development setup is ready."
echo "Start Userverse with: make dev"
echo "Health endpoint: http://127.0.0.1:8500/"
