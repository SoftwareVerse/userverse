from fastapi import status

# utils
from app.logic.company.user import CompanyUserService
from app.models.generic_pagination import PaginatedResponse, PaginationMeta
from app.utils.app_error import AppError

# repository
from app.repository.company_role import RoleRepository

# models
from app.models.company.roles import (
    CompanyDefaultRoles,
    RoleDeleteModel,
    RoleQueryParamsModel,
    RoleCreateModel,
    RoleReadModel,
    RoleUpdateModel,
)
from app.models.company.response_messages import (
    CompanyRoleResponseMessages,
)
from app.utils.shared_context import SharedContext


class RoleService:
    def __init__(self, context: SharedContext):
        self.context = context

    def update_role(
        self, company_id: int, name: str, payload: RoleUpdateModel
    ) -> RoleReadModel:
        """
        Update the description or name of a role for a company.
        """
        CompanyUserService(self.context).check_if_user_is_in_company(
            user_id=self.context.user.id,
            company_id=company_id,
            role=CompanyDefaultRoles.ADMINISTRATOR.name_value,
        )
        role_repository = RoleRepository(company_id=company_id, session=self.context.db_session)
        role = role_repository.update_role(
            name=name,
            payload=payload,
        )
        if not role:
            raise AppError(
                status_code=status.HTTP_400_BAD_REQUEST,
                message=CompanyRoleResponseMessages.ROLE_UPDATE_FAILED.value,
            )
        return role

    def create_role(self, payload: RoleCreateModel, company_id: int) -> RoleReadModel:
        """
        Create a new company role and store its creator in primary_meta_data.
        """
        CompanyUserService(self.context).check_if_user_is_in_company(
            user_id=self.context.user.id,
            company_id=company_id,
            role=CompanyDefaultRoles.ADMINISTRATOR.name_value,
        )
        role_repository = RoleRepository(company_id=company_id, session=self.context.db_session)
        role = role_repository.create_role(payload, self.context.user)
        if not role:
            raise AppError(
                status_code=status.HTTP_400_BAD_REQUEST,
                message=CompanyRoleResponseMessages.ROLE_CREATION_FAILED.value,
            )
        return role

    def delete_role(self, payload: RoleDeleteModel, company_id: int) -> dict:
        CompanyUserService(self.context).check_if_user_is_in_company(
            user_id=self.context.user.id,
            company_id=company_id,
            role=CompanyDefaultRoles.ADMINISTRATOR.name_value,
        )
        role_repository = RoleRepository(company_id=company_id, session=self.context.db_session)
        return role_repository.delete_role(payload=payload, deleted_by=self.context.user)

    def get_company_roles(
        self, payload: RoleQueryParamsModel, company_id: int
    ) -> PaginatedResponse[RoleReadModel]:
        """
        Get company roles with pagination and optional filtering.
        """
        CompanyUserService(self.context).check_if_user_is_in_company(
            user_id=self.context.user.id,
            company_id=company_id,
            role=CompanyDefaultRoles.ADMINISTRATOR.name_value,
        )
        role_repository = RoleRepository(company_id=company_id, session=self.context.db_session)
        result = role_repository.get_roles(payload=payload)

        return PaginatedResponse[RoleReadModel](
            records=[RoleReadModel(**role) for role in result["records"]],
            pagination=PaginationMeta(**result["pagination"]),
        )
