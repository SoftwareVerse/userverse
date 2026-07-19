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
REQUIRE_EMAIL_VERIFICATION=true
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

If you want to exercise the non-verification flow locally, run tests or manual API checks with:

```bash
REQUIRE_EMAIL_VERIFICATION=false
```

The resend-verification endpoint is now unauthenticated and rate-limited, so local manual checks should use a JSON body rather than a bearer token:

```bash
curl -X POST \
  'http://127.0.0.1:8000/userverse/user/resend-verification' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{"email":"user@example.com"}'
```
