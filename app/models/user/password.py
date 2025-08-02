from pydantic import BaseModel, EmailStr


class PasswordResetRequest(BaseModel):
    email: EmailStr


class OTPValidationRequest(BaseModel):
    otp: str
