#!/usr/bin/env bash

set -Eeuo pipefail

REGISTRY="${REGISTRY:-ghcr.io}"
NAMESPACE="${NAMESPACE:-SoftwareVerse}"
IMAGE_NAME="${IMAGE_NAME:-userverse}"
TRIVY_IMAGE="${TRIVY_IMAGE:-aquasec/trivy:0.72.0@sha256:cffe3f5161a47a6823fbd23d985795b3ed72a4c806da4c4df16266c02accdd6f}"
PUSH_IMAGE=true

usage() {
    cat <<'USAGE'
Build, scan, smoke-test, and publish the latest tagged Userverse image.

Usage: scripts/publish_image.sh [--no-push]

Options:
  --no-push  Build and run every check without publishing to GHCR.
  -h, --help Show this help text.

Environment overrides:
  REGISTRY       Registry hostname (default: ghcr.io)
  NAMESPACE      Registry namespace (default: SoftwareVerse; normalized lowercase)
  IMAGE_NAME     Package name (default: userverse; normalized lowercase)
  GHCR_USERNAME  Username used with GHCR_TOKEN
  GHCR_TOKEN     Optional token passed to `docker login --password-stdin`
  TRIVY_IMAGE    Pinned Trivy container reference

Tag and clean-tree checks apply only when pushing. --no-push accepts feature branches.
When pushing, the current commit must be exactly the repository's latest semantic version tag.
The script publishes IMAGE_NAME:<version> and IMAGE_NAME:latest, not a new package
name for every version.
USAGE
}

while (($#)); do
    case "$1" in
        --no-push)
            PUSH_IMAGE=false
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown argument: $1" >&2
            usage >&2
            exit 2
            ;;
    esac
    shift
done

for command_name in docker git; do
    if ! command -v "$command_name" >/dev/null 2>&1; then
        echo "Required command not found: $command_name" >&2
        exit 1
    fi
done

REPOSITORY_ROOT=$(git rev-parse --show-toplevel)
cd "$REPOSITORY_ROOT"

if [[ "$PUSH_IMAGE" == true ]]; then
LATEST_TAG=$(git tag --sort=-v:refname | head -n 1)
HEAD_TAG=$(git describe --tags --exact-match HEAD 2>/dev/null || true)

if [[ -z "$LATEST_TAG" ]]; then
    echo "No Git tags exist. Create a release tag before publishing." >&2
    exit 1
fi

if [[ "$HEAD_TAG" != "$LATEST_TAG" ]]; then
    echo "Refusing to publish an incorrectly labelled image." >&2
    echo "Current commit tag: ${HEAD_TAG:-<untagged>}" >&2
    echo "Latest repository tag: $LATEST_TAG" >&2
    echo "Check out or create the latest release tag first." >&2
    exit 1
fi

if [[ -n "$(git status --porcelain)" ]]; then
    echo "Refusing to publish from a dirty working tree." >&2
    echo "Commit or stash local changes first." >&2
    exit 1
fi

VERSION="${LATEST_TAG#v}"
else
    LATEST_TAG="working tree"
    VERSION="dev-$(git rev-parse --short HEAD)"
fi
NORMALIZED_NAMESPACE=$(printf '%s' "$NAMESPACE" | tr '[:upper:]' '[:lower:]')
NORMALIZED_IMAGE_NAME=$(printf '%s' "$IMAGE_NAME" | tr '[:upper:]' '[:lower:]')
REMOTE_IMAGE="$REGISTRY/$NORMALIZED_NAMESPACE/$NORMALIZED_IMAGE_NAME"
LOCAL_IMAGE="userverse-release:$VERSION"
RUN_ID="${$}"
NETWORK_NAME="userverse-release-$RUN_ID"
POSTGRES_NAME="userverse-postgres-$RUN_ID"
MYSQL_NAME="userverse-mysql-$RUN_ID"
APP_NAME="userverse-api-$RUN_ID"
TRIVY_CACHE=$(mktemp -d /tmp/userverse-trivy.XXXXXX)
TRIVY_DOCKER_GID=$(stat --format=%g /var/run/docker.sock)

cleanup() {
    docker rm --force "$APP_NAME" "$POSTGRES_NAME" "$MYSQL_NAME" >/dev/null 2>&1 || true
    docker network rm "$NETWORK_NAME" >/dev/null 2>&1 || true
    rm -rf "$TRIVY_CACHE"
}
trap cleanup EXIT INT TERM

wait_for_health() {
    local container_name=$1
    local attempts=${2:-60}
    local status

    for ((attempt = 1; attempt <= attempts; attempt++)); do
        status=$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$container_name")
        if [[ "$status" == "healthy" ]]; then
            return 0
        fi
        if [[ "$status" == "exited" || "$status" == "dead" || "$status" == "unhealthy" ]]; then
            docker logs "$container_name" >&2
            return 1
        fi
        sleep 2
    done

    echo "Timed out waiting for $container_name to become healthy." >&2
    docker logs "$container_name" >&2
    return 1
}

echo "Building $LOCAL_IMAGE from $LATEST_TAG..."
docker build \
    --label "org.opencontainers.image.source=https://github.com/$NAMESPACE/$IMAGE_NAME" \
    --label "org.opencontainers.image.revision=$(git rev-parse HEAD)" \
    --tag "$LOCAL_IMAGE" \
    .

echo "Scanning the image with Trivy..."
docker run --rm \
    --volume /var/run/docker.sock:/var/run/docker.sock \
    --user "$(id -u):$(id -g)" \
    --group-add "$TRIVY_DOCKER_GID" \
    --volume "$TRIVY_CACHE:/tmp/trivy-cache" \
    "$TRIVY_IMAGE" image \
    --cache-dir /tmp/trivy-cache \
    --scanners vuln \
    --pkg-types os,library \
    --severity HIGH,CRITICAL \
    --ignore-unfixed \
    --exit-code 1 \
    "$LOCAL_IMAGE"

echo "Starting disposable PostgreSQL and MySQL databases..."
docker network create "$NETWORK_NAME" >/dev/null

docker run --detach \
    --name "$POSTGRES_NAME" \
    --network "$NETWORK_NAME" \
    --env POSTGRES_USER=userverse \
    --env POSTGRES_PASSWORD=userverse \
    --env POSTGRES_DB=userverse \
    --health-cmd "pg_isready -U userverse -d userverse" \
    --health-interval 2s \
    --health-timeout 3s \
    --health-retries 30 \
    postgres:17 >/dev/null

docker run --detach \
    --name "$MYSQL_NAME" \
    --network "$NETWORK_NAME" \
    --env MYSQL_ROOT_PASSWORD=root \
    --env MYSQL_DATABASE=userverse \
    --env MYSQL_USER=userverse \
    --env MYSQL_PASSWORD=userverse \
    --health-cmd "mysqladmin ping -h 127.0.0.1 -uuserverse -puserverse" \
    --health-interval 2s \
    --health-timeout 3s \
    --health-retries 60 \
    mysql:8.4 >/dev/null

wait_for_health "$POSTGRES_NAME"
wait_for_health "$MYSQL_NAME" 90

echo "Verifying migrations on MySQL..."
docker run --rm \
    --network "$NETWORK_NAME" \
    --env "DATABASE_URL=mysql+pymysql://userverse:userverse@$MYSQL_NAME:3306/userverse" \
    --env JWT__SECRET=release-smoke-secret-at-least-32-bytes \
    "$LOCAL_IMAGE" true

echo "Verifying PostgreSQL migrations and API health..."
docker run --detach \
    --name "$APP_NAME" \
    --network "$NETWORK_NAME" \
    --env "DATABASE_URL=postgresql+psycopg2://userverse:userverse@$POSTGRES_NAME:5432/userverse" \
    --env JWT__SECRET=release-smoke-secret-at-least-32-bytes \
    "$LOCAL_IMAGE" >/dev/null
wait_for_health "$APP_NAME"

if [[ "$PUSH_IMAGE" != true ]]; then
    echo "All checks passed. Skipping registry push (--no-push)."
    exit 0
fi

if [[ -n "${GHCR_TOKEN:-}" ]]; then
    if [[ -z "${GHCR_USERNAME:-}" ]]; then
        echo "GHCR_USERNAME is required when GHCR_TOKEN is set." >&2
        exit 1
    fi
    printf '%s' "$GHCR_TOKEN" | docker login "$REGISTRY" --username "$GHCR_USERNAME" --password-stdin
fi

VERSION_IMAGE="$REMOTE_IMAGE:$VERSION"
LATEST_IMAGE="$REMOTE_IMAGE:latest"

echo "Publishing $VERSION_IMAGE and $LATEST_IMAGE..."
docker tag "$LOCAL_IMAGE" "$VERSION_IMAGE"
docker tag "$LOCAL_IMAGE" "$LATEST_IMAGE"
docker push "$VERSION_IMAGE"
docker push "$LATEST_IMAGE"

echo "Published successfully:"
echo "  $VERSION_IMAGE"
echo "  $LATEST_IMAGE"
