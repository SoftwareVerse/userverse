from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.generic_pagination import PaginationParams


class PermissionScope(str, Enum):
    GLOBAL = "global"
    COMPANY = "company"


class PermissionCreateModel(BaseModel):
    name: str = Field(..., min_length=1, max_length=256)
    description: Optional[str] = Field(default=None, max_length=256)

    @field_validator("name")
    @classmethod
    def trim_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Permission name cannot be blank.")
        return value


class PermissionUpdateModel(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=256)
    description: Optional[str] = Field(default=None, max_length=256)

    @field_validator("name")
    @classmethod
    def trim_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("Permission name cannot be blank.")
        return value

    @model_validator(mode="after")
    def require_update(self):
        if not self.model_fields_set.intersection({"name", "description"}):
            raise ValueError("At least one permission field must be provided.")
        if "name" in self.model_fields_set and self.name is None:
            raise ValueError("Permission name cannot be null.")
        return self


class PermissionReadModel(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    scope: PermissionScope
    company_id: Optional[UUID] = None


class PermissionQueryParamsModel(PaginationParams):
    name: Optional[str] = Field(None, description="Filter by permission name")
    description: Optional[str] = Field(
        None,
        description="Filter by permission description",
    )
