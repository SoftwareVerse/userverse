#!/usr/bin/env bash
set -euo pipefail

docker run --rm -i hadolint/hadolint:v2.14.0-debian hadolint --ignore DL3008 - < Dockerfile
