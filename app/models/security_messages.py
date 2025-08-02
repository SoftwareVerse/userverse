from enum import Enum


class SecurityResponseMessages(str, Enum):
    INVALID_CREDENTIALS_MESSAGE = "Invalid credentials"
    INVALID_REQUEST_MESSAGE = "Invalid request"
    # error types
    MISSING_AUTHORIZATION_HEADER = (
        "Missing authorization header, {'Authorization': 'Bearer TOKEN'}"
    )
    INVALID_AUTHORIZATION_HEADER = "Invalid authorization header"
    INVALID_AUTHORIZATION_TYPE = "Invalid authorization type"
    INVALID_TOKEN = "Invalid token"
    INVALID_TOKEN_TYPE = "Invalid token type"
    MISSING_USER_DATA = "Missing user data in token"
    EXPIRED_TOKEN = "Token has expired"
    ERROR_DECODING = "Error decoding token"
    INVALID_REQUEST = "Invalid request"
