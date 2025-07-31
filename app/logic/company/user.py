from fastapi import status

# utils
from app.logic.company.repository.company import CompanyRepository
from app.logic.mailer import MailService
from app.models.company.user import CompanyUserAdd, CompanyUserRead
from app.models.generic_pagination import PaginatedResponse
from app.utils.app_error import AppError

# repository
from app.logic.company.repository.user import CompanyUserRepository

# database
from app.database.session_manager import DatabaseSessionManager
from app.database.association_user_company import AssociationUserCompany


from app.models.company.roles import CompanyDefaultRoles


from app.models.user.user import UserQueryParams, UserRead


from app.models.company.response_messages import CompanyResponseMessages


class CompanyUserService:
    COMPANY_REGISTRATION_TEMPLATE = "company_invite.html"
    COMPANY_REGISTRATION_SUBJECT = "Company Invite"

    @classmethod
    def add_user_to_company(
        cls, company_id: int, payload: CompanyUserAdd, added_by: UserRead
    ) -> CompanyUserRead:
        CompanyUserService.check_if_user_is_in_company(
            user_id=added_by.id,
            company_id=company_id,
            role=CompanyDefaultRoles.ADMINISTRATOR.name_value,
        )
        repository = CompanyUserRepository()
        user = repository.add_user_to_company(
            company_id=company_id, payload=payload, added_by=added_by
        )
        company = CompanyRepository().get_company_by_id(company_id=company_id)
        # Send invite email,
        MailService.send_template_email(
            to=user.email,
            subject=cls.COMPANY_REGISTRATION_SUBJECT,
            template_name=cls.COMPANY_REGISTRATION_TEMPLATE,
            context={
                "invitee": user.first_name + " " + user.last_name,
                "company": company.name,
                "role": user.role_name,
            },
        )
        return user

    @staticmethod
    def remove_user_from_company(
        company_id: int,
        user_id: int,
        removed_by: UserRead,
    ) -> CompanyUserRead:
        CompanyUserService.check_if_user_is_in_company(
            user_id=removed_by.id,
            company_id=company_id,
            role=CompanyDefaultRoles.ADMINISTRATOR.name_value,
        )
        repository = CompanyUserRepository()
        return repository.remove_user_from_company(
            company_id=company_id,
            user_id=user_id,
            removed_by=removed_by,
        )

    @staticmethod
    def get_company_user(
        company_id: int,
        params: UserQueryParams,
        user: UserRead,
    ) -> PaginatedResponse[CompanyUserRead]:
        CompanyUserService.check_if_user_is_in_company(
            user_id=user.id,
            company_id=company_id,
            role=CompanyDefaultRoles.ADMINISTRATOR.name_value,
        )
        repository = CompanyUserRepository()
        return repository.get_company_users(
            company_id=company_id,
            params=params,
        )

    @staticmethod
    def check_if_user_is_in_company(
        user_id: str, company_id: str, role: str = None
    ) -> bool:
        """
        Check if the user is linked to the company.
        If a role is provided, check if the user has that role.
        """
        with DatabaseSessionManager().session_object() as session:
            # Check if the user is linked to the company
            linked_company = AssociationUserCompany.is_user_linked_to_company(
                session=session,
                user_id=int(user_id),
                company_id=int(company_id),
                role_name=role,
            )
            if not linked_company:
                raise AppError(
                    status_code=status.HTTP_403_FORBIDDEN,
                    message=CompanyResponseMessages.UNAUTHORIZED_COMPANY_ACCESS.value,
                )

            return linked_company
