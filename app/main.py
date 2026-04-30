import logging
import logging.config
import os
from contextlib import asynccontextmanager

import click
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from uvicorn.config import Config
from uvicorn.server import Server

from app.database.session_manager import get_engine
from app.exceptions import register_exception_handlers

# user routers
from app.middleware.logging import LogMiddleware
from app.middleware.profiling import ProfilingMiddleware

# from app.models.tags import UserverseApiTag
from app.routers.user import (
    user_basic_auth_routes,
    user_password_routes,
    user_profile_routes,
    user_verification_routes,
)
from app.routers.company import (
    company,
    users,
    roles,
)

# utils
from app.configs import get_settings
from app.utils.logging import get_uvicorn_log_config, logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Userverse API starting up")
    get_engine()
    yield
    logger.info("Userverse API shutting down")


def create_app() -> FastAPI:
    settings = get_settings()
    cor_origins_allowed = settings.cor_origins.allowed
    cor_origins_blocked = settings.cor_origins.blocked
    origins = [
        origin for origin in cor_origins_allowed if origin not in cor_origins_blocked
    ]

    app = FastAPI(
        lifespan=lifespan,
        root_path="/userverse",
        title=settings.name,
        version=settings.version,
        description=settings.description,
        # openapi_tags=UserverseApiTag.list(),
    )

    # setup_otel(app)
    app.add_middleware(LogMiddleware)
    app.add_middleware(ProfilingMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include user routers
    app.include_router(user_basic_auth_routes.router)
    app.include_router(user_verification_routes.router)
    app.include_router(user_profile_routes.router)
    app.include_router(user_password_routes.router)
    # Include company routers
    app.include_router(company.router)
    app.include_router(users.router)
    app.include_router(roles.router)

    # Root route
    @app.get("/", tags=["Root"])
    async def root():
        from opentelemetry import trace

        with trace.get_tracer(__name__).start_as_current_span("manual-span"):
            return JSONResponse(
                status_code=200,
                content={
                    "status": "ok",
                    "environment": settings.environment,
                    "version": settings.version,
                    "name": settings.name,
                    "description": settings.description,
                    "repository": settings.repository,
                    "documentation": settings.documentation,
                    "message": "Welcome to the Userverse backend API",
                },
            )

    # Prometheus metrics
    @app.get("/metrics")
    def metrics():
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    register_exception_handlers(app)

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
        )
        server = Server(config)
        server.run()


if __name__ == "__main__":
    main()
