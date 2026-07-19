# PR Description

## Summary

This PR completes the `userverse` backend reorganization around two goals:

- move API-facing modules into a dedicated `app/api` package
- finish the repository/settings refactor so runtime configuration and database access are consistent

It also updates the API test layout to mirror the new package structure and fixes company API error handling so duplicate-company and company-not-found flows return stable JSON error responses.

## What Changed

- moved API-facing modules into `app/api/`:
  - `app/api/dependencies`
  - `app/api/middleware`
  - `app/api/routers`
  - `app/api/security`
- rewrote runtime imports to use `app.api.*` paths from:
  - `app.main`
  - router modules
  - auth-related services
  - API-layer tests and monkeypatch targets
- removed the old top-level API package locations:
  - `app/dependencies`
  - `app/middleware`
  - `app/routers`
  - `app/security`
- moved API-related tests into `tests/api/`:
  - `tests/api/http`
  - `tests/api/middleware`
  - `tests/api/security`
- added `pythonpath = ["."]` in pytest config so the new test layout resolves the application package reliably
- removed the old `app/database` package after the repository-backed database layer became the canonical implementation
- kept the repository/database refactor centered on `app/repository/database/` and the shared repository base
- kept the settings fix that resolves environment values lazily and extracted generic config helpers into:
  - `app/utils/env.py`
  - `app/utils/parsing.py`
  - `app/utils/project_metadata.py`
- fixed company API behavior:
  - duplicate company creation now returns a `409` `AppError` instead of leaking a DB integrity error
  - business-level company `404` responses now preserve the JSON error contract instead of falling through to the plain-text route-not-found handler

## Why

The codebase had API concerns spread across several top-level packages, while `main-backend` already used an `app/api` boundary. This PR brings `userverse` closer to that structure and makes the API layer easier to navigate.

The recent settings and repository changes also exposed two concrete issues:

- userverse requests depended on config values that could be frozen too early
- company API failures were not consistently mapped to application-level HTTP errors

This PR addresses both structural and behavioral inconsistencies in one pass.

## Risk / Impact

- medium: this touches app startup, auth, router imports, middleware, exception handling, test layout, and package boundaries
- no intentional API contract changes beyond making duplicate-company and company-not-found failures return the expected JSON app-error shape
- test paths changed materially, so downstream tooling that hardcodes old `tests/http`, `tests/security`, or `tests/middleware` paths may need updating

## Testing

Ran focused validation for the moved API packages and the company/error behavior:

```bash
uv run pytest tests/api/http/b_company/test_a_create_company.py \
  tests/api/http/b_company/test_b_get_company.py \
  tests/api/http/test_exceptions.py \
  tests/api/http/test_main.py \
  tests/api/http/test_main_cli.py \
  tests/api/security/test_jwt.py
```

Result:

- `38 passed`

Previously during the move, the following focused suites also passed:

```bash
uv run pytest tests/api/middleware/test_otel.py \
  tests/api/security/test_basic.py \
  tests/api/security/test_jwt.py \
  tests/api/http/test_main.py \
  tests/api/http/test_main_cli.py \
  tests/api/http/a_user/test_a_create_user_api.py \
  tests/api/http/a_user/test_b_user_login_api.py
```

## Follow-ups

- remove temporary lowercase compatibility properties from `Settings` once all callers consistently use the newer settings shape
- decide whether to move more non-HTTP API-adjacent tests under `tests/api/` for consistency
- consider reducing SMTP retry/timeout impact on registration and password-reset request completion
