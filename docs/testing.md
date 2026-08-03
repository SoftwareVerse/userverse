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
uv run pytest tests/api/http --http-env-file .env
uv run pytest tests/api/security
uv run pytest tests/database
uv run pytest tests/utils
```

If `uv` cannot write to its default cache in a sandboxed environment, use:

```bash
uv run --no-cache pytest tests/utils
```

By default, the HTTP suite uses a temporary SQLite database and patches email dispatch so tests do not perform network SMTP calls.

If you need to seed or validate a non-temporary environment, pass `--http-env-file`:

```bash
uv run pytest tests/api/http/c_company_roles -q --http-env-file .env
uv run pytest tests/api/http -q --http-env-file /path/to/.env
```

The env-backed mode loads variables from the specified dotenv file and uses its `DATABASE_URL` instead of the isolated test database. This is intended for explicit local seeding or environment verification, not default development or CI runs.

The env file should define at least:

```bash
DATABASE_URL=sqlite:///./development.db
```

If omitted, the HTTP test harness falls back to:

- `ENV=testing`
- `ENVIRONMENT=testing`
- `TESTING=true`
- `DB_AUTO_CREATE=true`
- `FRONTEND_URL=https://frontend.example.com/reset-password`
- `JWT_SECRET=testing-secret-key-with-at-least-32-bytes`

Use `--http-env-file` carefully: the HTTP fixtures can create, update, and reseed records in the target database.

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
