from uuid import UUID

from fastapi import status

# utils
from app.services.mailer import MailService
from app.repository.company import CompanyRepository
from app.repository.company_user import CompanyUserRepository
from app.models.company.user import (
    CompanyUserAddModel,
    CompanyUserReadModel,
    CompanyUserRoleUpdateModel,
)
from app.models.generic_pagination import PaginatedResponse
from app.utils.app_error import AppError

from app.models.company.roles import CompanyDefaultRoles
from app.models.system_permissions import SystemPermission
from app.services.company.authorization import CompanyAuthorizationService


from app.models.user.user import UserQueryParams


from app.models.company.response_messages import (
    CompanyUserResponseMessages,
)
from app.utils.shared_context import SharedContext
from app.utils.logging import logger


class CompanyUserService:
    COMPANY_INVITE_TEMPLATE = "company_invite.html"

    def __init__(self, context: SharedContext):
        self.context = context
        self.company_user_repository = CompanyUserRepository(context.db_session)
        self.company_repository = CompanyRepository(context.db_session)
        self.authorization = CompanyAuthorizationService(context)

    def send_company_invite(
        self,
        *,
        invitee_email: str,
        invitee_name: str,
        company_name: str,
        role_name: str,
    ) -> None:
        try:
            MailService.send_template_email(
                to=invitee_email,
                subject=f"{self.context.configs.APP_NAME} Company Invitation",
                template_name=self.COMPANY_INVITE_TEMPLATE,
                context={
                    "invitee": invitee_name,
                    "company": company_name,
                    "role": role_name,
                    "app_name": self.context.configs.APP_NAME,
                },
            )
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "Company invite dispatch failed",
                extra={
                    "extra": {
                        "email": invitee_email,
                        "company": company_name,
                        "role": role_name,
                        "error": str(exc),
                    }
                },
            )

    def add_user_to_company(
        self, company_id: UUID, payload: CompanyUserAddModel
    ) -> CompanyUserReadModel:
        self.authorization.require(
            company_id,
            SystemPermission.COMPANY_MEMBERS_ADD,
        )
        user = self.company_user_repository.add_user_to_company(
            company_id=company_id, payload=payload, added_by=self.context.user
        )
        company = self.company_repository.get_company_by_id(company_id=company_id)
        self.send_company_invite(
            invitee_email=user.email,
            invitee_name=f"{user.first_name or ''} {user.last_name or ''}".strip()
            or user.email,
            company_name=company.name,
            role_name=user.role.name,
        )
        return user

    def update_user_role(
        self,
        company_id: UUID,
        user_id: UUID,
        payload: CompanyUserRoleUpdateModel,
    ) -> CompanyUserReadModel:
        self.authorization.require(
            company_id,
            SystemPermission.COMPANY_MEMBERS_ROLE_UPDATE,
        )
        return self.company_user_repository.update_user_role(
            company_id=company_id,
            user_id=user_id,
            role_name=payload.role,
            updated_by=self.context.user,
        )

    def remove_user_from_company(
        self,
        company_id: UUID,
        user_id: UUID,
    ) -> CompanyUserReadModel:
        self.authorization.require(
            company_id,
            SystemPermission.COMPANY_MEMBERS_REMOVE,
        )
        if self.company_user_repository.is_user_linked_to_company(
            user_id=user_id,
            company_id=company_id,
            role_name=CompanyDefaultRoles.OWNER.name_value,
        ):
            raise AppError(
                status_code=status.HTTP_400_BAD_REQUEST,
                message=CompanyUserResponseMessages.REMOVE_USER_FAILED.value,
                error="Owner cannot be removed from the company.",
            )
        return self.company_user_repository.remove_user_from_company(
            company_id=company_id,
            user_id=user_id,
            removed_by=self.context.user,
        )

    def get_company_users(
        self,
        company_id: UUID,
        params: UserQueryParams,
    ) -> PaginatedResponse[CompanyUserReadModel]:
        self.authorization.require(
            company_id,
            SystemPermission.COMPANY_MEMBERS_READ,
        )
        return self.company_user_repository.get_company_users(
            company_id=company_id,
            params=params,
        )
