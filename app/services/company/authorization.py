from uuid import UUID

from fastapi import status

from app.models.company.response_messages import CompanyResponseMessages
from app.models.system_permissions import SystemPermission
from app.repository.database.tables import (
    AssociationUserCompany,
    Company,
    CompanyRole,
    GlobalPermission,
    Role,
    RoleGlobalPermission,
)
from app.utils.app_error import AppError
from app.utils.shared_context import SharedContext


class CompanyAuthorizationService:
    def __init__(self, context: SharedContext):
        self.context = context

    def require(
        self,
        company_id: UUID,
        permission: SystemPermission,
    ) -> None:
        if self.context.user.is_superuser:
            return

        authorized = (
            self.context.db_session.query(AssociationUserCompany)
            .join(
                Company,
                Company.id == AssociationUserCompany.company_id,
            )
            .join(
                CompanyRole,
                (CompanyRole.company_id == AssociationUserCompany.company_id)
                & (CompanyRole.role_id == AssociationUserCompany.role_id),
            )
            .join(Role, Role.id == AssociationUserCompany.role_id)
            .join(
                RoleGlobalPermission,
                RoleGlobalPermission.role_id == AssociationUserCompany.role_id,
            )
            .join(
                GlobalPermission,
                GlobalPermission.id == RoleGlobalPermission.global_permission_id,
            )
            .filter(
                AssociationUserCompany.user_id == self.context.user.id,
                AssociationUserCompany.company_id == company_id,
                AssociationUserCompany._closed_at.is_(None),
                Company._closed_at.is_(None),
                CompanyRole._closed_at.is_(None),
                Role._closed_at.is_(None),
                RoleGlobalPermission._closed_at.is_(None),
                GlobalPermission.id == permission.permission_id,
                GlobalPermission.name == permission.value,
                GlobalPermission._closed_at.is_(None),
            )
            .first()
            is not None
        )
        if not authorized:
            raise AppError(
                status_code=status.HTTP_403_FORBIDDEN,
                message=CompanyResponseMessages.UNAUTHORIZED_COMPANY_ACCESS.value,
            )
