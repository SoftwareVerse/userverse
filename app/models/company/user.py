from pydantic import BaseModel, EmailStr, Field
from app.models.company.roles import CompanyDefaultRoles, RoleReadModel
from app.models.user.user import UserReadModel


class CompanyUserReadModel(UserReadModel):
    role: RoleReadModel


class CompanyUserAddModel(BaseModel):
    email: EmailStr = Field(
        default=None,
        json_schema_extra={"example": "user.one@email.com"},
    )
    role: str = Field(
        default=CompanyDefaultRoles.VIEWER.name_value,
        json_schema_extra={"example": "Viewer"},
    )


class CompanyUserRoleUpdateModel(BaseModel):
    role: str = Field(
        ...,
        json_schema_extra={"example": "Administrator"},
    )
