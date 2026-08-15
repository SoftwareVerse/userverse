#!/usr/bin/env bash
set -euo pipefail

export ENVIRONMENT=testing
export TESTING=true
mkdir -p coverage_reports

uv run pytest --cov=app \
  --cov-report=term-missing \
  --cov-report=xml:coverage_reports/coverage.xml \
  --cov-fail-under=100
