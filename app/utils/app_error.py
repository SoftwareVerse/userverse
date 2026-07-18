from fastapi import status
from fastapi.exceptions import HTTPException
import inspect
import traceback
from typing import Optional


from app.utils.logging import logger


class AppError(HTTPException):
    def __init__(
        self,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        message: Optional[str] = "Request failed, please try again.",
        error: Optional[str] = None,
        log_error: bool = True,
        depth: int = 3,
    ):
        # Capture the caller's details
        caller_details = self.get_caller_details(depth)
        # Prepare the error detail
        details = {"message": message}
        if error is not None:
            details["error"] = error

        # Log the error if needed
        if log_error:
            logger.error(
                f"AppError: {message} | Details: {error} | Location: {caller_details}"
            )
            # self.log_exception()

        super().__init__(status_code, detail=details)

    @staticmethod
    def get_caller_details(depth):
        frame = inspect.currentframe()
        for _ in range(depth):
            frame = frame.f_back if frame else None

        caller_details = {
            "file": frame.f_code.co_filename if frame else "",
            "line": frame.f_lineno if frame else "",
            "function": frame.f_code.co_name if frame else "",
        }
        return caller_details

    def log_exception(self):
        # This method could be extended to integrate with external monitoring tools
        tb = traceback.format_exc()
        logger.error(f"StackTrace: {tb}")
