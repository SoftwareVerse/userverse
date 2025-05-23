from fastapi import status

# utils
from app.logic.company.user import CompanyUserService
from app.models.generic_pagination import PaginatedResponse, PaginationMeta
from app.utils.app_error import AppError

# repository
from app.logic.company.repository.role import RoleRepository


# models
from app.models.company.roles import CompanyDefaultRoles, RoleDelete, RoleQueryParams
from app.models.company.roles import (
    RoleCreate,
    RoleRead,
    RoleUpdate,
    CompanyDefaultRoles,
)
from app.models.user.user import UserRead
from app.models.company.response_messages import (
    CompanyRoleResponseMessages,
)


class RoleService:

    @staticmethod
    def update_role(
        company_id: int, updated_by: UserRead, name: str, payload: RoleUpdate
    ) -> RoleRead:
        """
        Update the description of a role for a company.
        """
        CompanyUserService.check_if_user_is_in_company(
            user_id=updated_by.id,
            company_id=company_id,
            role=CompanyDefaultRoles.ADMINISTRATOR.name_value,
        )
        role_repository = RoleRepository(company_id=company_id)
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

    @staticmethod
    def create_role(
        payload: RoleCreate, created_by: UserRead, company_id: int
    ) -> RoleRead:
        """
        Create a new company role and store its creator in primary_meta_data.
        """
        CompanyUserService.check_if_user_is_in_company(
            user_id=created_by.id,
            company_id=company_id,
            role=CompanyDefaultRoles.ADMINISTRATOR.name_value,
        )
        role_repository = RoleRepository(company_id=company_id)
        role = role_repository.create_role(payload, created_by)
        if not role:
            raise AppError(
                status_code=status.HTTP_400_BAD_REQUEST,
                message=CompanyRoleResponseMessages.ROLE_CREATION_FAILED.value,
            )
        return role

    @staticmethod
    def delete_role(payload: RoleDelete, deleted_by: UserRead, company_id: int) -> dict:
        CompanyUserService.check_if_user_is_in_company(
            user_id=deleted_by.id,
            company_id=company_id,
            role=CompanyDefaultRoles.ADMINISTRATOR.name_value,
        )
        role_repository = RoleRepository(company_id=company_id)
        return role_repository.delete_role(payload=payload, deleted_by=deleted_by)

    @staticmethod
    def get_company_roles(
        payload: RoleQueryParams, company_id: int, user: UserRead
    ) -> PaginatedResponse[RoleRead]:
        """
        Get company roles with pagination and optional filtering.
        """
        CompanyUserService.check_if_user_is_in_company(
            user_id=user.id,
            company_id=company_id,
            role=CompanyDefaultRoles.ADMINISTRATOR.name_value,
        )
        role_repository = RoleRepository(company_id=company_id)
        result = role_repository.get_roles(payload=payload)

        return PaginatedResponse[RoleRead](
            records=[RoleRead(**role) for role in result["records"]],
            pagination=PaginationMeta(**result["pagination"]),
        )
