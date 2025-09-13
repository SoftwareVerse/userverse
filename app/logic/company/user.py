from fastapi import status

# utils
from app.repository.company import CompanyRepository
from app.repository.company_user import CompanyUserRepository
from app.models.company.user import CompanyUserAddModel, CompanyUserReadModel
from app.models.generic_pagination import PaginatedResponse
from app.utils.app_error import AppError

# database
from app.database.association_user_company import AssociationUserCompany


from app.models.company.roles import CompanyDefaultRoles


from app.models.user.user import UserQueryParams


from app.models.company.response_messages import CompanyResponseMessages
from app.utils.shared_context import SharedContext


class CompanyUserService:
    def __init__(self, context: SharedContext):
        self.context = context
        self.company_user_repository = CompanyUserRepository(context.db_session)
        self.company_repository = CompanyRepository(context.db_session)

    def add_user_to_company(
        self, company_id: int, payload: CompanyUserAddModel
    ) -> CompanyUserReadModel:
        self.check_if_user_is_in_company(
            user_id=self.context.user.id,
            company_id=company_id,
            role=CompanyDefaultRoles.ADMINISTRATOR.name_value,
        )
        user = self.company_user_repository.add_user_to_company(
            company_id=company_id, payload=payload, added_by=self.context.user
        )
        company = self.company_repository.get_company_by_id(company_id=company_id)
        # Send invite email,
        # MailService.send_template_email(
        #     to=user.email,
        #     subject=cls.COMPANY_REGISTRATION_SUBJECT,
        #     template_name=cls.COMPANY_REGISTRATION_TEMPLATE,
        #     context={
        #         "invitee": user.first_name + " " + user.last_name,
        #         "company": company.name,
        #         "role": user.role_name,
        #     },
        # )
        return user

    def remove_user_from_company(
        self,
        company_id: int,
        user_id: int,
    ) -> CompanyUserReadModel:
        self.check_if_user_is_in_company(
            user_id=self.context.user.id,
            company_id=company_id,
            role=CompanyDefaultRoles.ADMINISTRATOR.name_value,
        )
        return self.company_user_repository.remove_user_from_company(
            company_id=company_id,
            user_id=user_id,
            removed_by=self.context.user,
        )

    def get_company_user(
        self,
        company_id: int,
        params: UserQueryParams,
    ) -> PaginatedResponse[CompanyUserReadModel]:
        self.check_if_user_is_in_company(
            user_id=self.context.user.id,
            company_id=company_id,
        )
        return self.company_user_repository.get_company_users(
            company_id=company_id,
            params=params,
        )

    def check_if_user_is_in_company(
        self, user_id: str, company_id: str, role: str = None
    ) -> bool:
        """
        Check if the user is linked to the company.
        If a role is provided, check if the user has that role.
        """
        with self.context.db_session as session:
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
