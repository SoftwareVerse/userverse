import os
import logging
import traceback
import logging.config
import click
import uvicorn

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST, Counter
from contextlib import asynccontextmanager
from uvicorn.config import Config
from uvicorn.server import Server

# user routers
from app.middleware.logging import LogMiddleware
from app.models.tags import UserverseApiTag
from app.routers.user import user
from app.routers.user import password

# utils
from app.utils.config.loader import ConfigLoader
from app.utils.logging import logger, get_uvicorn_log_config
from app.models.response_messages import ErrorResponseMessagesModel
from app.database.session_manager import DatabaseSessionManager


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Userverse API starting up")
    DatabaseSessionManager()
    yield
    logger.info("Userverse API shutting down")


def create_app() -> FastAPI:
    loader = ConfigLoader()
    configs = loader.get_config()

    cor_origins = configs.get("cor_origins", {})
    cor_origins_allowed = cor_origins.get("allowed", ["*"])
    cor_origins_blocked = cor_origins.get("blocked", [])
    origins = [
        origin for origin in cor_origins_allowed if origin not in cor_origins_blocked
    ]

    app = FastAPI(
        lifespan=lifespan,
        title=configs.get("name"),
        version=configs.get("version"),
        description=configs.get("description"),
        # openapi_tags=UserverseApiTag.list(),
    )

    # setup_otel(app)
    app.add_middleware(LogMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(user.router)
    app.include_router(password.router)

    # Root route
    @app.get("/", tags=["Root"])
    async def root():
        from opentelemetry import trace

        with trace.get_tracer(__name__).start_as_current_span("manual-span"):
            return JSONResponse(
                status_code=200,
                content={
                    "status": "ok",
                    "version": configs.get("version"),
                    "name": configs.get("name"),
                    "description": configs.get("description"),
                    "repository": configs.get("repository"),
                    "documentation": configs.get("documentation"),
                    "message": "Welcome to the Userverse backend API",
                },
            )

    # Prometheus metrics
    @app.get("/metrics")
    def metrics():
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    # Exception tracking
    UNHANDLED_EXCEPTIONS = Counter(
        "unhandled_exceptions_total",
        "Total number of unhandled exceptions",
        ["method", "endpoint"],
    )

    @app.exception_handler(Exception)
    async def app_error_handler(request: Request, exc: Exception):
        UNHANDLED_EXCEPTIONS.labels(
            method=request.method, endpoint=request.url.path
        ).inc()
        logger.error(
            "Unhandled exception",
            extra={
                "extra": {
                    "method": request.method,
                    "url": str(request.url),
                    "error": str(exc),
                    "trace": traceback.format_exc(),
                }
            },
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": {
                    "message": ErrorResponseMessagesModel.GENERIC_ERROR,
                    "error": str(exc),
                }
            },
        )

    return app


@click.command()
@click.option("--port", default=8000, type=int, help="Port to run the server on.")
@click.option("--host", default="0.0.0.0", type=str, help="Host to run the server on.")
@click.option("--env", default="development", help="Environment to run in.")
@click.option("--reload", is_flag=True, help="Enable auto-reload.")
@click.option("--workers", default=1, type=int, help="Number of worker processes.")
@click.option("--verbose", is_flag=True, help="Enable verbose logging.")
def main(
    port: int,
    host: str,
    env: str,
    reload: bool,
    workers: int,
    verbose: bool,
):
    os.environ["ENV"] = env

    if reload and workers > 1:
        os.environ["WATCHFILES_IGNORE"] = "*.pyc;.venv;tests;scripts"
        logger.warning("Reload mode only supports a single worker.")
        workers = 1

    logger.info("🚀 Starting Userverse API at http://%s:%d [env=%s]", host, port, env)

    logging_config = get_uvicorn_log_config(reload=reload, verbose=verbose)
    logging.config.dictConfig(logging_config)

    if reload:
        uvicorn.run(
            "app.main:create_app",
            factory=True,
            host=host,
            port=port,
            reload=True,
            log_config=logging_config,
        )
    else:
        config = Config(
            app="app.main:create_app",
            factory=True,
            host=host,
            port=port,
            workers=workers,
            use_colors=True,
            log_config=logging_config,
        )
        server = Server(config)
        server.run()


if __name__ == "__main__":
    main()
