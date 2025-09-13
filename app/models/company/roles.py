from enum import Enum
from typing import Optional
from pydantic import BaseModel
from pydantic import field_validator, Field

from app.models.generic_pagination import PaginationParams


class CompanyDefaultRoles(str, Enum):
    ADMINISTRATOR = "Administrator: Full access to manage users and data"
    VIEWER = "Viewer: Read-only access to company data"

    @property
    def name_value(self) -> str:
        """Returns just the role name (e.g., 'Administrator')."""
        return self.value.split(":")[0].strip()

    @property
    def description(self) -> str:
        """Returns just the role description."""
        return self.value.split(":", 1)[1].strip()


class RoleCreateModel(BaseModel):
    name: str
    description: Optional[str]


class RoleUpdateModel(BaseModel):
    name: Optional[str]
    description: Optional[str]


class RoleDeleteModel(BaseModel):
    replacement_role_name: str
    role_name_to_delete: str

    @field_validator("role_name_to_delete")
    def validate_not_default_role(cls, v: str) -> str:
        default_roles = {r.name_value for r in CompanyDefaultRoles}
        if v in default_roles:
            raise ValueError(f"Cannot delete default system role: '{v}'")
        return v


class RoleReadModel(BaseModel):
    name: Optional[str]
    description: Optional[str]


class RoleQueryParamsModel(PaginationParams):
    name: Optional[str] = Field(None, description="Filter by role name")
    description: Optional[str] = Field(None, description="Filter by role description")
