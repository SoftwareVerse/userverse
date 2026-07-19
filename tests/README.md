# Userverse Testing

The test suite covers API integration behavior, database/repository behavior, security helpers, middleware, email utilities, and shared utilities.

## Test Runtime

The CI runner uses:

```bash
ENVIRONMENT=testing
TESTING=true
```

The `scripts/run_http_tests.sh` script sets these values and runs pytest with coverage:

```bash
./scripts/run_http_tests.sh
```

Coverage output is written to `coverage_reports/coverage.xml`, and CI enforces a `95%` coverage threshold.

## Directory Structure

```text
tests/
├── api/
│   ├── http/
│   │   ├── a_user/
│   │   ├── b_company/
│   │   ├── c_company_roles/
│   │   ├── d_company_users/
│   │   ├── conftest.py
│   │   ├── test_exceptions.py
│   │   ├── test_main.py
│   │   ├── test_main_cli.py
│   │   ├── test_pagination_regressions.py
│   │   └── test_profiling.py
│   ├── middleware/
│   └── security/
├── data/
│   ├── database/
│   └── http/
├── database/
├── jobs/
└── utils/
    └── email/
```

## Running Focused Suites

API HTTP tests:

```bash
uv run pytest tests/api/http
```

User API tests:

```bash
uv run pytest tests/api/http/a_user
```

Company API tests:

```bash
uv run pytest tests/api/http/b_company
uv run pytest tests/api/http/c_company_roles
uv run pytest tests/api/http/d_company_users
```

Security and middleware tests:

```bash
uv run pytest tests/api/security
uv run pytest tests/api/middleware
```

Database and repository tests:

```bash
uv run pytest tests/database
```

Utility tests:

```bash
uv run pytest tests/utils
```

## Notes

- HTTP integration tests use FastAPI `TestClient` and a test SQLite database.
- Email delivery is patched/skipped in test mode so tests do not contact SMTP servers.
- Pagination tests seed their dedicated data directly to keep setup fast and stable.
- Coverage intentionally omits infrastructure adapters such as SMTP delivery and request/profiling/OTel middleware wrappers.
