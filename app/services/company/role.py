from uuid import UUID

from fastapi import status

from app.models.company.response_messages import CompanyRoleResponseMessages
from app.models.company.roles import (
    CompanyDefaultRoles,
    RoleAssignCompaniesModel,
    RoleCreateModel,
    RoleDeleteModel,
    RoleQueryParamsModel,
    RoleReadModel,
    RoleUpdateModel,
)
from app.models.generic_pagination import PaginatedResponse
from app.repository.company_role import (
    CompanyRoleAssignmentRepository,
    RoleRepository,
)
from app.services.company.user import CompanyUserService
from app.utils.app_error import AppError
from app.utils.shared_context import SharedContext


class RoleService:
    def __init__(self, context: SharedContext):
        self.context = context

    def _ensure_company_manager(self, company_id: UUID) -> None:
        company_user_service = CompanyUserService(self.context)
        if not (
            company_user_service.company_user_repository.is_user_linked_to_company(
                user_id=self.context.user.id,
                company_id=company_id,
                role_name=CompanyDefaultRoles.ADMINISTRATOR.name_value,
            )
            or company_user_service.company_user_repository.is_user_linked_to_company(
                user_id=self.context.user.id,
                company_id=company_id,
                role_name=CompanyDefaultRoles.OWNER.name_value,
            )
        ):
            raise AppError(
                status_code=status.HTTP_403_FORBIDDEN,
                message="Access denied. You are not authorized to access this company.",
            )

    def create_role(self, payload: RoleCreateModel) -> RoleReadModel:
        role = RoleRepository(self.context.db_session).create_role(
            payload, self.context.user
        )
        if not role:
            raise AppError(
                status_code=status.HTTP_400_BAD_REQUEST,
                message=CompanyRoleResponseMessages.ROLE_CREATION_FAILED.value,
            )
        return role

    def get_roles(
        self, payload: RoleQueryParamsModel
    ) -> PaginatedResponse[RoleReadModel]:
        result = RoleRepository(self.context.db_session).get_roles(payload=payload)
        records = []
        for role in result["records"]:
            role["id"] = str(role["id"])
            records.append(RoleReadModel(**role))
        return PaginatedResponse[RoleReadModel](
            records=records,
            pagination=result["pagination"],
        )

    def update_role(self, role_id: UUID, payload: RoleUpdateModel) -> RoleReadModel:
        role = RoleRepository(self.context.db_session).update_role(role_id, payload)
        if not role:
            raise AppError(
                status_code=status.HTTP_400_BAD_REQUEST,
                message=CompanyRoleResponseMessages.ROLE_UPDATE_FAILED.value,
            )
        return role

    def update_company_role(
        self, company_id: UUID, name: str, payload: RoleUpdateModel
    ) -> RoleReadModel:
        self._ensure_company_manager(company_id)
        role = CompanyRoleAssignmentRepository(
            company_id=company_id,
            session=self.context.db_session,
        ).update_company_role(name, payload)
        if not role:
            raise AppError(
                status_code=status.HTTP_400_BAD_REQUEST,
                message=CompanyRoleResponseMessages.ROLE_UPDATE_FAILED.value,
            )
        return role

    def delete_global_role(self, role_id: UUID) -> dict:
        return RoleRepository(self.context.db_session).delete_role(
            role_id, self.context.user
        )

    def assign_role_to_company(self, company_id: UUID, role_id: UUID) -> RoleReadModel:
        self._ensure_company_manager(company_id)
        role = RoleRepository(self.context.db_session).ensure_role_exists(role_id)
        return CompanyRoleAssignmentRepository(
            company_id=company_id,
            session=self.context.db_session,
        ).assign_role(role, self.context.user)

    def assign_role_to_companies(
        self, role_id: UUID, payload: RoleAssignCompaniesModel
    ) -> dict:
        role = RoleRepository(self.context.db_session).ensure_role_exists(role_id)
        for company_id in payload.company_ids:
            self._ensure_company_manager(UUID(company_id))
        if not payload.company_ids:
            return {"role_id": str(role.id), "company_ids": []}
        return CompanyRoleAssignmentRepository(
            company_id=UUID(payload.company_ids[0]),
            session=self.context.db_session,
        ).assign_role_to_companies(role, payload, self.context.user)

    def create_role_for_company(
        self, payload: RoleCreateModel, company_id: UUID
    ) -> RoleReadModel:
        self._ensure_company_manager(company_id)
        repository = RoleRepository(self.context.db_session)
        existing_role = repository.get_role_by_name(payload.name)
        if existing_role is not None:
            role = RoleReadModel(
                id=str(existing_role.id),
                name=existing_role.name,
                description=existing_role.description,
            )
        else:
            role = self.create_role(payload)
        self.assign_role_to_company(company_id, UUID(role.id))
        return role

    def unassign_role(self, company_id: UUID, role_id: UUID) -> dict:
        self._ensure_company_manager(company_id)
        return CompanyRoleAssignmentRepository(
            company_id=company_id,
            session=self.context.db_session,
        ).unassign_role(role_id)

    def delete_role(self, payload: RoleDeleteModel, company_id: UUID) -> dict:
        self._ensure_company_manager(company_id)
        return CompanyRoleAssignmentRepository(
            company_id=company_id,
            session=self.context.db_session,
        ).reassign_and_delete_role(payload, self.context.user)

    def get_company_roles(
        self, payload: RoleQueryParamsModel, company_id: UUID
    ) -> PaginatedResponse[RoleReadModel]:
        self._ensure_company_manager(company_id)
        result = CompanyRoleAssignmentRepository(
            company_id=company_id,
            session=self.context.db_session,
        ).get_company_roles(payload=payload)
        records = []
        for role in result["records"]:
            role["id"] = str(role["id"])
            records.append(RoleReadModel(**role))
        return PaginatedResponse[RoleReadModel](
            records=records,
            pagination=result["pagination"],
        )
