FROM python:3.12
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /code

COPY ./pyproject.toml /code/pyproject.toml

RUN uv sync

COPY ./app /code/app

COPY ./sample-config.json /code/sample-config.json

EXPOSE 8500

CMD ["uv", "run", "--no-sync", "-m", "app.main", "--port", "8500", "--host", "0.0.0.0", "--env", "production"]