from enum import Enum

from pydantic import BaseModel, EmailStr, Field


class PasswordResetMethod(str, Enum):
    OTP = "otp"
    MAGIC_LINK = "magic_link"


class PasswordResetRequest(BaseModel):
    email: EmailStr
    method: PasswordResetMethod = PasswordResetMethod.OTP


class OTPValidationRequest(BaseModel):
    otp: str


class MagicLinkPasswordResetConfirmRequest(BaseModel):
    token: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=1)
