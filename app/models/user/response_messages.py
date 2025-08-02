from enum import Enum


class UserResponseMessages(str, Enum):
    # user creation
    USER_CREATED = "User created successfully"
    USER_CREATION_FAILED = "User creation failed"
    USER_ALREADY_EXISTS = "User already exists"
    # user get
    USER_NOT_FOUND = "User not found"
    USER_FOUND = "User found"
    # user update
    USER_UPDATED = "User updated successfully"
    USER_UPDATE_FAILED = "User update failed"
    USER_ACCOUNT_STATUS_UPDATED = "User status updated successfully"
    USER_ACCOUNT_STATUS_UPDATE_FAILED = "User status update failed"
    # user delete
    USER_DELETED = "User deleted successfully"
    USER_DELETION_FAILED = "User deletion failed"
    # user login
    USER_LOGGED_IN = "User logged in successfully"
    USER_LOGGED_OUT = "User logged out successfully"
    INVALID_CREDENTIALS = "Invalid credentials"
    # user password
    PASSWORD_RESET = "Password reset successfully"
    EMAIL_VERIFIED = "Email verified successfully"
    PASSWORD_RESET_FAILED = "Password reset failed"
    EMAIL_VERIFICATION_FAILED = "Email verification failed"
    ACCOUNT_LOCKED = "Account is locked"
    INVALID_REQUEST_MESSAGE = "Invalid request"


class PasswordResetResponseMessages(str, Enum):
    OTP_SENT = "OTP sent to email"
    OTP_VERIFIED = "OTP verified successfully"
    OTP_VERIFICATION_FAILED = "OTP verification failed"
    PASSWORD_CHANGED = "Password changed successfully"
    PASSWORD_CHANGE_FAILED = "Password change failed"
    ERROR = "Invalid OTP, does not match or expired"
