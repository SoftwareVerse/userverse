from typing import Optional
from app.models.company.address import CompanyAddressModel
from pydantic import BaseModel, EmailStr, field_validator, Field
from app.models.phone_number import validate_phone_number_format
from app.models.generic_pagination import PaginationParams


class CompanyReadModel(BaseModel):
    id: int
    name: Optional[str] = None
    description: Optional[str] = None
    industry: Optional[str] = None
    phone_number: Optional[str] = Field(
        None, json_schema_extra={"example": "1236547899"}
    )
    email: EmailStr
    address: Optional[CompanyAddressModel] = None


class CompanyUpdateModel(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    industry: Optional[str] = None
    phone_number: Optional[str] = Field(
        None, json_schema_extra={"example": "1236547899"}
    )
    address: Optional[CompanyAddressModel] = None

    @field_validator("phone_number")
    def validate_phone_number(cls, v: Optional[str]) -> Optional[str]:
        return validate_phone_number_format(v)


class CompanyCreateModel(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    industry: Optional[str] = None
    phone_number: Optional[str] = Field(
        None, json_schema_extra={"example": "1236547899"}
    )
    email: EmailStr
    address: Optional[CompanyAddressModel] = None

    @field_validator("phone_number")
    def validate_phone_number(cls, v: Optional[str]) -> Optional[str]:
        return validate_phone_number_format(v)


class CompanyQueryParamsModel(PaginationParams):
    role_name: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    industry: Optional[str] = None
    email: Optional[str] = None
