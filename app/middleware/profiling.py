import os
import time
import threading
import yappi
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.types import ASGIApp
from app.utils.logging import logger

class ProfilingMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.profile_dir = "profiles"
        if not os.path.exists(self.profile_dir):
            os.makedirs(self.profile_dir)

    async def dispatch(self, request: Request, call_next):
        # Check if profiling is enabled via environment variable or header
        should_profile = os.getenv("ENABLE_PROFILING", "false").lower() == "true" or \
                         request.headers.get("X-Profile", "false").lower() == "true"

        if not should_profile:
            return await call_next(request)

        # Start profiling
        yappi.set_clock_type("wall")
        yappi.start()
        try:
            return await call_next(request)
        finally:
            yappi.stop()
            # Save stats to a file with a unique name
            timestamp = time.time()
            ident = threading.get_ident()
            filename = os.path.join(self.profile_dir, f"profile_{timestamp}_{ident}.prof")
            stats = yappi.get_func_stats()
            stats.save(filename, type="pstat")
            # Clear stats to free memory - crucial for preventing memory leaks
            yappi.clear_stats()
            logger.info(f"Profile saved to {filename}")
