#!/bin/sh
set -eu

case "${RUN_MIGRATIONS:-true}" in
    1|true|TRUE|yes|YES)
        echo "Applying database migrations..."
        alembic upgrade head
        ;;
    *)
        echo "Skipping database migrations (RUN_MIGRATIONS=${RUN_MIGRATIONS:-false})."
        ;;
esac

exec "$@"
