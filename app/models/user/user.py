import re
from typing import Optional, Literal
from pydantic import BaseModel, EmailStr, field_validator, Field
from app.models.phone_number import validate_phone_number_format


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone_number: Optional[str] = Field(
        None, json_schema_extra={"example": "1236547899"}
    )
    password: Optional[str] = None

    @field_validator("phone_number")
    def validate_phone_number(cls, v: Optional[str]) -> Optional[str]:
        return validate_phone_number_format(v)


class UserCreate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone_number: Optional[str] = Field(
        None, json_schema_extra={"example": "1236547899"}
    )

    @field_validator("phone_number")
    def validate_phone_number(cls, v: Optional[str]) -> Optional[str]:
        return validate_phone_number_format(v)


class UserRead(BaseModel):
    id: int
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: EmailStr
    phone_number: Optional[str] = Field(
        None, json_schema_extra={"example": "1236547899"}
    )


class TokenResponseModel(BaseModel):
    token_type: Literal["bearer"] = Field(
        "bearer",
        description="Type of the token",
    )
    access_token: str = Field(..., description="JWT access token")
    access_token_expiration: str = Field(
        ..., description="Access token expiration time in 'YYYY-MM-DD HH:MM:SS' format"
    )
    refresh_token: str = Field(..., description="JWT refresh token")
    refresh_token_expiration: str = Field(
        ..., description="Refresh token expiration time in 'YYYY-MM-DD HH:MM:SS' format"
    )


class UserQueryParams(BaseModel):
    limit: int = Field(10, ge=1, le=100)
    offset: int = Field(0, ge=0)
    role_name: Optional[str] = Field(None, description="Filter by role name")
    first_name: Optional[str] = Field(None, description="Filter by user first name")
    last_name: Optional[str] = Field(None, description="Filter by user last name")
    email: Optional[str] = Field(None, description="Filter by user email")
