# FAQ

## Which app path should new API code use?

Use the `app/api` package:

- Routers: `app/api/routers`
- Dependencies: `app/api/dependencies`
- Security helpers: `app/api/security`
- Middleware: `app/api/middleware`

The old top-level `app/routers`, `app/security`, and `app/middleware` layout is no longer the current structure.

## Where do SQLAlchemy models live?

Table models live in `app/repository/database/tables`. Session management lives in `app/repository/database/session_manager.py`, and repository classes live in `app/repository`.

## Which test path should I use?

HTTP integration tests are under `tests/api/http`, not `tests/http`.

## How do I run the same command CI runs?

Use:

```bash
./scripts/run_http_tests.sh
```

## Why is SMTP not sending during tests?

When `TESTING=true` or `ENVIRONMENT=testing`, SMTP delivery is skipped so tests remain deterministic and do not depend on external mail servers.

## How is coverage configured?

Coverage is configured in `pyproject.toml` under `[tool.coverage.*]`. CI enforces `95%` coverage and writes XML output to `coverage_reports/coverage.xml`.
