import time
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from app.utils.logging import logger  # your existing logger

class LogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        # Reuse incoming request id if present, otherwise create one
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())

        # Basic request context
        ctx = {
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "query": request.url.query,
            "client": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
        }

        try:
            response: Response = await call_next(request)
        except Exception as exc:
            duration_ms = round((time.time() - start_time) * 1000.0, 2)
            logger.exception(
                "Request failed",
                extra={
                    **ctx,
                    "status_code": 500,
                    "duration_ms": duration_ms,
                    "error": str(exc),
                },
            )
            # Re-raise to let your global handlers/ASGI server respond
            raise

        # Success path
        duration_ms = round((time.time() - start_time) * 1000.0, 2)
        logger.info(
            "Request handled",
            extra={
                **ctx,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )

        # Return useful response headers for correlation/latency
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time-ms"] = str(duration_ms)
        return response
