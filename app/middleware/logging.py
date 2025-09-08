import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from app.utils.logging import logger


class LogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        try:
            response = await call_next(request)
        except Exception as exc:
            process_time = (time.time() - start_time) * 1000
            logger.error(
                "Request failed",
                extra={
                    "extra": {
                        "method": request.method,
                        "url": str(request.url),
                        "client": request.client.host if request.client else None,
                        "user_agent": request.headers.get("user-agent"),
                        "duration_ms": round(process_time, 2),
                        "status_code": 500,
                        "error": str(exc),
                    }
                },
            )
            raise

        process_time = (time.time() - start_time) * 1000
        logger.info(
            "Request handled",
            extra={
                "extra": {
                    "method": request.method,
                    "url": str(request.url),
                    "client": request.client.host if request.client else None,
                    "user_agent": request.headers.get("user-agent"),
                    "status_code": response.status_code,
                    "duration_ms": round(process_time, 2),
                }
            },
        )
        return response
