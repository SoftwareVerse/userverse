# syntax=docker/dockerfile:1

FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:0.10.2 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0

WORKDIR /code

RUN apt-get update \
    && apt-get install --yes --no-install-recommends build-essential default-libmysqlclient-dev pkg-config \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-install-project

FROM python:3.12-slim AS runtime

ENV PATH="/code/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    RUN_MIGRATIONS=true

WORKDIR /code

RUN apt-get update \
    && apt-get install --yes --no-install-recommends libmariadb3 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --system --uid 10001 --create-home userverse

COPY --from=builder /code/.venv /code/.venv
COPY --chown=userverse:userverse pyproject.toml ./pyproject.toml
COPY --chown=userverse:userverse app ./app
COPY --chown=userverse:userverse alembic ./alembic
COPY --chown=userverse:userverse alembic.ini ./alembic.ini
COPY --chown=userverse:userverse docker-entrypoint.sh ./docker-entrypoint.sh

USER userverse

EXPOSE 8500

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8500/', timeout=3)"]

ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["python", "-m", "app.main", "--port", "8500", "--host", "0.0.0.0", "--env", "production"]
