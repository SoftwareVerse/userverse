import os
import uuid
from typing import Any, Dict, Optional, Tuple

from fastapi import FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, PlainTextResponse
from prometheus_client import Counter, REGISTRY
from starlette import status

from app.models.response_messages import ErrorResponseMessagesModel
from app.utils.app_error import AppError
from app.utils.logging import logger

DEBUG_ERRORS = os.getenv("DEBUG_ERRORS", "false").lower() == "true"

try:
    UNHANDLED_EXCEPTIONS = Counter(
        "unhandled_exceptions_total",
        "Total number of unhandled exceptions",
        ["method", "endpoint"],
    )
except ValueError:
    # Reuse collector when app is created multiple times in one process.
    UNHANDLED_EXCEPTIONS = REGISTRY._names_to_collectors["unhandled_exceptions_total"]  # type: ignore[attr-defined,index]


def get_correlation_id(request: Request) -> str:
    cid = getattr(request.state, "correlation_id", None)
    if cid:
        return cid
    inbound = request.headers.get("x-correlation-id") or request.headers.get(
        "x-request-id"
    )
    if inbound:
        return inbound
    return str(uuid.uuid4())


def json_error(
    *,
    status_code: int,
    correlation_id: str,
    message: str,
    code: str = "internal_error",
    extra: Optional[Dict[str, Any]] = None,
) -> JSONResponse:
    payload: Dict[str, Any] = {
        "detail": {
            "message": message,
            "code": code,
            "correlation_id": correlation_id,
        }
    }
    if extra:
        payload["detail"]["extra"] = extra
        # Keep legacy fields for compatibility with existing HTTP tests/clients.
        if isinstance(extra, dict):
            if "error" in extra:
                payload["detail"]["error"] = extra["error"]
            if "errors" in extra:
                payload["detail"]["errors"] = extra["errors"]
    return JSONResponse(status_code=status_code, content=payload)


def unwrap_exception(exc: BaseException) -> Tuple[BaseException, list[str]]:
    trail: list[str] = []
    current: BaseException = exc

    while True:
        trail.append(type(current).__name__)

        try:
            if isinstance(current, BaseExceptionGroup):  # type: ignore[name-defined]
                if current.exceptions:
                    current = current.exceptions[0]
                    continue
                break
        except NameError:
            pass

        if getattr(current, "__cause__", None) is not None:
            current = current.__cause__  # type: ignore[assignment]
            continue

        if getattr(current, "__context__", None) is not None:
            current = current.__context__  # type: ignore[assignment]
            continue

        break

    return current, trail


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(404)
    async def not_found_handler(request: Request, exc: Exception):
        logger.info(
            "Endpoint not found",
            extra={
                "path": request.url.path,
                "method": request.method,
                "correlation_id": get_correlation_id(request),
            },
        )
        return PlainTextResponse("Not found", status_code=404)

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        correlation_id = get_correlation_id(request)
        msg = exc.detail if isinstance(exc.detail, str) else "Request failed"
        extra = exc.detail if isinstance(exc.detail, (dict, list)) else None

        log_fn = logger.error if exc.status_code >= 500 else logger.warning
        log_fn(
            "HTTPException",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": exc.status_code,
                "correlation_id": correlation_id,
            },
        )

        return json_error(
            status_code=exc.status_code,
            correlation_id=correlation_id,
            message=msg,
            code="http_error",
            extra={"detail": extra} if extra is not None else None,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ):
        correlation_id = get_correlation_id(request)
        serialized_errors = jsonable_encoder(
            exc.errors(),
            custom_encoder={BaseException: str},
        )
        logger.info(
            "Validation error",
            extra={
                "method": request.method,
                "path": request.url.path,
                "correlation_id": correlation_id,
            },
        )
        return json_error(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            correlation_id=correlation_id,
            message="Validation failed",
            code="validation_error",
            extra={"errors": serialized_errors},
        )

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError):
        correlation_id = get_correlation_id(request)
        detail = exc.detail if isinstance(exc.detail, dict) else {}
        message = detail.get("message", "Request failed")
        error = detail.get("error")

        logger.warning(
            "AppError",
            extra={
                "method": request.method,
                "path": request.url.path,
                "correlation_id": correlation_id,
                "status_code": exc.status_code,
            },
        )
        return json_error(
            status_code=exc.status_code,
            correlation_id=correlation_id,
            message=message,
            code="app_error",
            extra={"error": error} if error is not None else None,
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        correlation_id = get_correlation_id(request)
        root_exc, trail = unwrap_exception(exc)

        UNHANDLED_EXCEPTIONS.labels(
            method=request.method, endpoint=request.url.path
        ).inc()

        logger.exception(
            "Unhandled exception",
            extra={
                "method": request.method,
                "path": request.url.path,
                "correlation_id": correlation_id,
                "root_exception_type": type(root_exc).__name__,
            },
        )

        if not DEBUG_ERRORS:
            return json_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                correlation_id=correlation_id,
                message=ErrorResponseMessagesModel.GENERIC_ERROR,
                code="internal_error",
            )

        return json_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            correlation_id=correlation_id,
            message=str(root_exc) or "Unhandled exception",
            code=type(root_exc).__name__,
            extra={
                "exception_type": type(root_exc).__name__,
                "exception_message": str(root_exc),
                "exception_trail": trail,
            },
        )
