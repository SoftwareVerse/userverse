#!/bin/bash

set -e  # Exit on error (but we'll handle test collection issues manually)
set -o pipefail

echo "========================================="
echo "Starting HTTP Integration Test Suite"
echo "========================================="

# Export environment variable for test mode
export ENVIRONMENT=testing
export TESTING=true
echo "Test runtime configured with ENVIRONMENT=testing and TESTING=true"

# Optional: Clean up old test DB if exists
if [ -f "test_environment.db" ]; then
    echo "Removing old test_environment.db..."
    rm test_environment.db
fi

# Optional: Setup coverage report directory
COVERAGE_DIR="coverage_reports"
mkdir -p "$COVERAGE_DIR"

echo "-----------------------------------------"
echo "Generating Coverage Report Summary:"
uv run pytest -v --cov=app \
    --cov-report=term-missing \
    --cov-report=xml:"$COVERAGE_DIR/coverage.xml" \
    --cov-fail-under=95


echo "========================================="
echo "HTTP integration tests completed!"
echo "Coverage report saved to: $COVERAGE_DIR/coverage.xml"
echo "========================================="
