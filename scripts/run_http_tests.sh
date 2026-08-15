#!/usr/bin/env bash
set -euo pipefail

echo "scripts/run_http_tests.sh is deprecated; running scripts/run_tests.sh." >&2
exec "$(dirname "$0")/run_tests.sh" "$@"
