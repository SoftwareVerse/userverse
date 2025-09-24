[![Release Status](https://github.com/skhendle-verse/Userverse/actions/workflows/release.yml/badge.svg)](https://github.com/skhendle-verse/Userverse/actions/workflows/release.yml)

[![Build Status](https://github.com/skhendle-verse/Userverse/actions/workflows/build-and-test.yml/badge.svg)](https://github.com/skhendle-verse/Userverse/actions/workflows/build-and-test.yml)

[![codecov](https://codecov.io/gh/SoftwareVerse/Userverse/graph/badge.svg?token=8SIX9ONX0A)](https://codecov.io/gh/SoftwareVerse/Userverse)

# Userverse

Userverse is an open-source platform designed to make managing users, organizations, and their relationships simple and efficient. It’s built for developers, communities, and organizations who want a free, flexible, and secure way to handle user and organization management without relying on closed or proprietary systems.

## Directory Overview

```bash
├── alembic
│   └── versions
├── app
│   ├── database
│   ├── logic
│   │   └── user
│   │       └── repository
│   ├── middleware
│   ├── models
│   │   └── user
│   ├── routers
│   │   └── user
│   ├── security
│   └── utils
├── coverage_reports
├── docs
│   └── images
├── scripts
│   └── versions
└── tests
    ├── data
    │   ├── database
    │   └── http
    ├── database
    ├── http
    │   └── user
    └── utils
```

### Database
 - Database initialization, connection management, and session handling (engine setup, session factory)
### Logic
 - Services: Core business logic implementation (user registration, authentication flows)
 - Repositories: Data access layer for database operations with clean abstractions
### Middleware
 - Request/response processing components (CORS configuration, logging, error handlers)
### Models
 - Pydantic schema definitions for data validation and API documentation

### Routers
 - API endpoint definitions organized by resource domain (users, auth, etc.)

### Security
 - Authentication mechanisms and authorization controls (JWT, password hashing)
### Utils
 - Shared helper functions and third-party integrations (email, OTP generation)

### Docs
 - Technical documentation assets including diagrams and implementation guides

### Tests
 - Comprehensive test suite mirroring application structure for unit and integration testing

# 📘 Running the Userverse API

This project uses **FastAPI**, **Uvicorn**, and a dynamic configuration system with support for both CLI and hot-reload development.

---

## 🚀 Development Mode with Auto-Reload

Use `uvicorn` in **factory mode** to support reload and dynamic config loading via environment variables:

```bash
# Set environment variables and run the app
export ENV=development 
export JSON_CONFIG_PATH=/userverse/local_config.json 
# run with python - NOTE: I prefer this since all my logs are json
-  python -m app.main --reload --host 0.0.0.0 --port 8500

# run with uv
uv run --no-sync uvicorn app.main:create_app \
  --factory \
  --reload \
  --host 0.0.0.0 \
  --port 8500

# run with uvicorn
- uvicorn app.main:create_app --factory --reload --host 0.0.0.0 --port 8500

```

✅ This supports live code reload and is ideal for development workflows.

---

## ⚙️ Production or CLI Mode (No Reload)

Use the built-in CLI to run the app with full control over config, port, and worker count:

```bash


uv run -m app.main --port 8500 \
  --env production \
  --json_config_path sample-config.json \
  --host 0.0.0.0 \
  --port 8504 \
  --workers 4
```

✅ This mode supports scaling with Uvicorn workers and does not enable reload.

---

-  docker build --pull --rm -f 'Dockerfile' -t 'userverse:latest' '.'

docker run -d \
  --name userverse \
  --restart unless-stopped \
  -p 8500:8500 \
  -e JSON_CONFIG_PATH=/code/sample-config.json \
  userverse:latest