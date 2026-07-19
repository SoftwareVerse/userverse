# Testing

Userverse uses `pytest` and `pytest-cov`.

Run the CI-style test command:

```bash
./scripts/run_http_tests.sh
```

The script sets:

```bash
ENVIRONMENT=testing
TESTING=true
```

It then runs:

```bash
pytest -v --cov=app \
  --cov-report=term-missing \
  --cov-report=xml:coverage_reports/coverage.xml \
  --cov-fail-under=95
```

For local development, prefer focused runs:

```bash
uv run pytest tests/api/http/a_user
uv run pytest tests/api/http/b_company
uv run pytest tests/api/security
uv run pytest tests/database
uv run pytest tests/utils
```

If `uv` cannot write to its default cache in a sandboxed environment, use:

```bash
uv run --no-cache pytest tests/utils
```

The HTTP suite uses a test SQLite database and patches email dispatch so tests do not perform network SMTP calls.
