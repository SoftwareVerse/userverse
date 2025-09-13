from typing import Optional
from pydantic import BaseModel, Field


class CompanyAddressModel(BaseModel):
    street: Optional[str] = Field(None, json_schema_extra={"example": "123 Main St"})
    city: Optional[str] = Field(None, json_schema_extra={"example": "Cape Town"})
    state: Optional[str] = Field(None, json_schema_extra={"example": "CT"})
    postal_code: Optional[str] = Field(None, json_schema_extra={"example": "8000"})
    country: Optional[str] = Field(None, json_schema_extra={"example": "South Africa"})
