from typing import Optional
from app.models.company.address import CompanyAddress
from pydantic import BaseModel, EmailStr, field_validator, Field
from app.models.phone_number import validate_phone_number_format


class CompanyRead(BaseModel):
    id: int
    name: Optional[str] = None
    description: Optional[str] = None
    industry: Optional[str] = None
    phone_number: Optional[str] = Field(
        None, json_schema_extra={"example": "1236547899"}
    )
    email: EmailStr
    address: Optional[CompanyAddress] = None


class CompanyUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    industry: Optional[str] = None
    phone_number: Optional[str] = Field(
        None, json_schema_extra={"example": "1236547899"}
    )
    address: Optional[CompanyAddress] = None

    @field_validator("phone_number")
    def validate_phone_number(cls, v: Optional[str]) -> Optional[str]:
        return validate_phone_number_format(v)


class CompanyCreate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    industry: Optional[str] = None
    phone_number: Optional[str] = Field(
        None, json_schema_extra={"example": "1236547899"}
    )
    email: EmailStr
    address: Optional[CompanyAddress] = None

    @field_validator("phone_number")
    def validate_phone_number(cls, v: Optional[str]) -> Optional[str]:
        return validate_phone_number_format(v)


class CompanyQueryParams(BaseModel):
    limit: int = Field(10, ge=1, le=100)
    offset: int = Field(0, ge=0)
    role_name: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    industry: Optional[str] = None
    email: Optional[str] = None
