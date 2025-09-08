from dataclasses import dataclass


@dataclass(frozen=True)
class ErrorResponseMessagesModel:
    # League messages
    INVALID_REQUEST_MESSAGE: str = (
        "Invalid request. Please check your input and try again."
    )
    GENERIC_ERROR: str = "An unexpected error occurred. Please try again later."
