from uuid import UUID

from fastapi import status

from app.models.company.response_messages import CompanyRoleResponseMessages
from app.models.company.roles import (
    RoleAssignCompaniesModel,
    RoleCreateModel,
    RoleDeleteModel,
    RoleQueryParamsModel,
    RoleReadModel,
    RoleUpdateModel,
)
from app.models.system_permissions import SystemPermission
from app.models.generic_pagination import PaginatedResponse
from app.repository.company_role import (
    CompanyRoleAssignmentRepository,
    RoleRepository,
)
from app.services.company.authorization import CompanyAuthorizationService
from app.utils.app_error import AppError
from app.utils.shared_context import SharedContext


class RoleService:
    def __init__(self, context: SharedContext):
        self.context = context
        self.authorization = CompanyAuthorizationService(context)

    def _ensure_superuser(self) -> None:
        if not self.context.user.is_superuser:
            raise AppError(
                status_code=status.HTTP_403_FORBIDDEN,
                message=CompanyRoleResponseMessages.ROLE_MANAGEMENT_FORBIDDEN.value,
            )

    def _ensure_company_permission(
        self,
        company_id: UUID,
        permission: SystemPermission,
    ) -> None:
        self.authorization.require(company_id, permission)

    def create_role(
        self, payload: RoleCreateModel, company_id: UUID | None = None
    ) -> RoleReadModel:
        self._ensure_superuser()
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

    def update_role(self, *args, **kwargs) -> RoleReadModel:
        self._ensure_superuser()
        if len(args) == 3 and not kwargs:
            company_id, name, payload = args
            role = RoleRepository(
                self.context.db_session,
                company_id=company_id,
            ).update_role(name, payload)
        else:
            role_id = kwargs.get("role_id", args[0] if args else None)
            payload = kwargs.get("payload", args[1] if len(args) > 1 else None)
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
        self._ensure_superuser()
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
        self._ensure_superuser()
        return RoleRepository(self.context.db_session).delete_role(
            role_id, self.context.user
        )

    def assign_role_to_company(self, company_id: UUID, role_id: UUID) -> RoleReadModel:
        self._ensure_company_permission(
            company_id,
            SystemPermission.COMPANY_ROLES_ASSIGN,
        )
        role = RoleRepository(self.context.db_session).ensure_role_exists(role_id)
        return CompanyRoleAssignmentRepository(
            company_id=company_id,
            session=self.context.db_session,
        ).assign_role(role, self.context.user)

    def assign_role_to_companies(
        self, role_id: UUID, payload: RoleAssignCompaniesModel
    ) -> dict:
        self._ensure_superuser()
        role = RoleRepository(self.context.db_session).ensure_role_exists(role_id)
        if not payload.company_ids:
            return {"role_id": str(role.id), "company_ids": []}
        return CompanyRoleAssignmentRepository(
            company_id=UUID(payload.company_ids[0]),
            session=self.context.db_session,
        ).assign_role_to_companies(role, payload, self.context.user)

    def create_role_for_company(
        self, payload: RoleCreateModel, company_id: UUID
    ) -> RoleReadModel:
        self._ensure_superuser()
        repository = RoleRepository(self.context.db_session)
        role_record = repository.get_role_by_name(payload.name)
        if role_record is None:
            created_role = repository.create_role(payload, self.context.user)
            role_record = repository.ensure_role_exists(UUID(created_role.id))
        return CompanyRoleAssignmentRepository(
            company_id=company_id,
            session=self.context.db_session,
        ).assign_role(role_record, self.context.user)

    def unassign_role(self, company_id: UUID, role_id: UUID) -> dict:
        self._ensure_company_permission(
            company_id,
            SystemPermission.COMPANY_ROLES_UNASSIGN,
        )
        return CompanyRoleAssignmentRepository(
            company_id=company_id,
            session=self.context.db_session,
        ).unassign_role(role_id)

    def delete_role(self, payload: RoleDeleteModel, company_id: UUID) -> dict:
        self._ensure_superuser()
        return CompanyRoleAssignmentRepository(
            company_id=company_id,
            session=self.context.db_session,
        ).reassign_and_delete_role(payload, self.context.user)

    def get_company_roles(
        self, payload: RoleQueryParamsModel, company_id: UUID
    ) -> PaginatedResponse[RoleReadModel]:
        self._ensure_company_permission(
            company_id,
            SystemPermission.COMPANY_ROLES_READ,
        )
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
