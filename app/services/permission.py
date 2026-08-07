from uuid import UUID

from fastapi import status

from app.models.company.roles import RoleReadModel
from app.models.generic_pagination import PaginatedResponse
from app.models.permission_response_messages import PermissionResponseMessages
from app.models.permissions import (
    PermissionCreateModel,
    PermissionQueryParamsModel,
    PermissionReadModel,
    PermissionUpdateModel,
)
from app.models.system_permissions import SystemPermission
from app.repository.permission import (
    CompanyPermissionRepository,
    GlobalPermissionRepository,
    PlatformRoleRepository,
    RolePermissionRepository,
)
from app.utils.app_error import AppError
from app.utils.shared_context import SharedContext
from app.services.company.authorization import CompanyAuthorizationService


class PermissionService:
    def __init__(self, context: SharedContext):
        self.context = context
        self.company_authorization = CompanyAuthorizationService(context)

    def _ensure_superuser(self) -> None:
        if not self.context.user.is_superuser:
            raise AppError(
                status_code=status.HTTP_403_FORBIDDEN,
                message=PermissionResponseMessages.MANAGEMENT_FORBIDDEN.value,
            )

    def _ensure_company_permission(
        self,
        company_id: UUID,
        permission: SystemPermission,
    ) -> None:
        repository = CompanyPermissionRepository(
            company_id,
            self.context.db_session,
        )
        repository.ensure_company()
        self.company_authorization.require(company_id, permission)

    def create_global_permission(
        self,
        payload: PermissionCreateModel,
    ) -> PermissionReadModel:
        self._ensure_superuser()
        return GlobalPermissionRepository(self.context.db_session).create_permission(
            payload, self.context.user
        )

    def get_global_permissions(
        self,
        payload: PermissionQueryParamsModel,
    ) -> PaginatedResponse[PermissionReadModel]:
        self._ensure_superuser()
        return GlobalPermissionRepository(self.context.db_session).get_permissions(
            payload
        )

    def update_global_permission(
        self,
        permission_id: UUID,
        payload: PermissionUpdateModel,
    ) -> PermissionReadModel:
        self._ensure_superuser()
        return GlobalPermissionRepository(self.context.db_session).update_permission(
            permission_id,
            payload,
        )

    def delete_global_permission(self, permission_id: UUID) -> dict[str, str]:
        self._ensure_superuser()
        return GlobalPermissionRepository(self.context.db_session).delete_permission(
            permission_id
        )

    def create_company_permission(
        self,
        company_id: UUID,
        payload: PermissionCreateModel,
    ) -> PermissionReadModel:
        self._ensure_company_permission(
            company_id,
            SystemPermission.COMPANY_PERMISSIONS_CREATE,
        )
        return CompanyPermissionRepository(
            company_id,
            self.context.db_session,
        ).create_permission(payload, self.context.user)

    def get_company_permissions(
        self,
        company_id: UUID,
        payload: PermissionQueryParamsModel,
    ) -> PaginatedResponse[PermissionReadModel]:
        self._ensure_company_permission(
            company_id,
            SystemPermission.COMPANY_PERMISSIONS_READ,
        )
        return CompanyPermissionRepository(
            company_id,
            self.context.db_session,
        ).get_permissions(payload)

    def update_company_permission(
        self,
        company_id: UUID,
        permission_id: UUID,
        payload: PermissionUpdateModel,
    ) -> PermissionReadModel:
        self._ensure_company_permission(
            company_id,
            SystemPermission.COMPANY_PERMISSIONS_UPDATE,
        )
        return CompanyPermissionRepository(
            company_id,
            self.context.db_session,
        ).update_permission(permission_id, payload)

    def delete_company_permission(
        self,
        company_id: UUID,
        permission_id: UUID,
    ) -> dict[str, str]:
        self._ensure_company_permission(
            company_id,
            SystemPermission.COMPANY_PERMISSIONS_DELETE,
        )
        return CompanyPermissionRepository(
            company_id,
            self.context.db_session,
        ).delete_permission(permission_id)

    def get_global_role_permissions(
        self,
        role_id: UUID,
    ) -> list[PermissionReadModel]:
        self._ensure_superuser()
        return RolePermissionRepository(
            self.context.db_session
        ).get_global_role_permissions(role_id)

    def assign_global_permission(
        self,
        role_id: UUID,
        permission_id: UUID,
    ) -> RoleReadModel:
        self._ensure_superuser()
        return RolePermissionRepository(
            self.context.db_session
        ).assign_global_permission(role_id, permission_id)

    def remove_global_permission(
        self,
        role_id: UUID,
        permission_id: UUID,
    ) -> RoleReadModel:
        self._ensure_superuser()
        return RolePermissionRepository(
            self.context.db_session
        ).remove_global_permission(role_id, permission_id)

    def get_company_role_permissions(
        self,
        company_id: UUID,
        role_id: UUID,
    ) -> list[PermissionReadModel]:
        self._ensure_company_permission(
            company_id,
            SystemPermission.COMPANY_PERMISSIONS_READ,
        )
        return RolePermissionRepository(
            self.context.db_session
        ).get_company_role_permissions(company_id, role_id)

    def assign_company_permission(
        self,
        company_id: UUID,
        role_id: UUID,
        permission_id: UUID,
    ) -> RoleReadModel:
        self._ensure_company_permission(
            company_id,
            SystemPermission.COMPANY_PERMISSIONS_ASSIGN,
        )
        return RolePermissionRepository(
            self.context.db_session
        ).assign_company_permission(company_id, role_id, permission_id)

    def remove_company_permission(
        self,
        company_id: UUID,
        role_id: UUID,
        permission_id: UUID,
    ) -> RoleReadModel:
        self._ensure_company_permission(
            company_id,
            SystemPermission.COMPANY_PERMISSIONS_UNASSIGN,
        )
        return RolePermissionRepository(
            self.context.db_session
        ).remove_company_permission(company_id, role_id, permission_id)

    def get_platform_roles(self, user_id: UUID) -> list[RoleReadModel]:
        self._ensure_superuser()
        return PlatformRoleRepository(self.context.db_session).get_roles(user_id)

    def assign_platform_role(
        self,
        user_id: UUID,
        role_id: UUID,
    ) -> list[RoleReadModel]:
        self._ensure_superuser()
        return PlatformRoleRepository(self.context.db_session).assign_role(
            user_id,
            role_id,
        )

    def remove_platform_role(
        self,
        user_id: UUID,
        role_id: UUID,
    ) -> list[RoleReadModel]:
        self._ensure_superuser()
        return PlatformRoleRepository(self.context.db_session).remove_role(
            user_id,
            role_id,
        )

    def get_my_platform_permissions(self) -> list[PermissionReadModel]:
        return PlatformRoleRepository(
            self.context.db_session
        ).get_effective_permissions(self.context.user.id)
