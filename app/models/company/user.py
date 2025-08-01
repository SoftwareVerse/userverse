from pydantic import BaseModel, EmailStr, Field
from app.models.company.roles import CompanyDefaultRoles
from app.models.user.user import UserReadModel


class CompanyUserRead(UserRead):
    role_name: str


class CompanyUserAdd(BaseModel):
    email: EmailStr = Field(
        default=None,
        json_schema_extra={"example": "user.one@email.com"},
    )
    role: str = Field(
        default=CompanyDefaultRoles.VIEWER.name_value,
        json_schema_extra={"example": "Viewer"},
    )
