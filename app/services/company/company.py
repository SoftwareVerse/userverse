from uuid import UUID

from fastapi import status

# utils
from app.utils.app_error import AppError

# service and repository
from app.services.company.user import CompanyUserService
from app.repository.company import CompanyRepository

# database

# models
from app.models.company.company import (
    CompanyCreateModel,
    CompanyUpdateModel,
    CompanyReadModel,
)
from app.models.company.roles import CompanyDefaultRoles


from app.utils.shared_context import SharedContext


from app.models.company.response_messages import CompanyResponseMessages


class CompanyService:
    def __init__(self, context: SharedContext):
        self.context = context
        self.company_repository = CompanyRepository(context.db_session)
        self.company_user_service = CompanyUserService(context)

    def create_company(self, payload: CompanyCreateModel) -> CompanyReadModel:
        """
        Create a new company and store its address in primary_meta_data.
        Also sets up default roles (Administrator, Viewer).
        """
        company = self.company_repository.create_company(payload, self.context.user)
        if not company:
            raise AppError(
                status_code=status.HTTP_400_BAD_REQUEST,
                message=CompanyResponseMessages.COMPANY_CREATION_FAILED.value,
            )
        return company

    def get_company(
        self, company_id: UUID | None = None, email: str | None = None
    ) -> CompanyReadModel:
        """
        Get a company by its ID.
        """
        if not company_id and not email:
            raise AppError(
                status_code=status.HTTP_400_BAD_REQUEST,
                message=CompanyResponseMessages.COMPANY_ID_OR_EMAIL_REQUIRED.value,
            )
        company = None
        if company_id:
            company = self.company_repository.get_company_by_id(company_id)

        if email:
            company = self.company_repository.get_company_by_email(email)

        self.company_user_service.check_if_user_is_in_company(
            user_id=self.context.user.id,
            company_id=company.id,
        )

        return company

    def update_company(
        self, payload: CompanyUpdateModel, company_id: UUID
    ) -> CompanyReadModel:
        """
        Update a company by its ID.
        """
        if not (
            self.company_user_service.company_user_repository.is_user_linked_to_company(
                user_id=self.context.user.id,
                company_id=company_id,
                role=CompanyDefaultRoles.ADMINISTRATOR.name_value,
            )
            or self.company_user_service.company_user_repository.is_user_linked_to_company(
                user_id=self.context.user.id,
                company_id=company_id,
                role=CompanyDefaultRoles.OWNER.name_value,
            )
        ):
            raise AppError(
                status_code=status.HTTP_403_FORBIDDEN,
                message=CompanyResponseMessages.UNAUTHORIZED_COMPANY_ACCESS.value,
            )

        company = self.company_repository.update_company(
            payload, company_id, self.context.user
        )
        if not company:
            raise AppError(
                status_code=status.HTTP_400_BAD_REQUEST,
                message=CompanyResponseMessages.COMPANY_UPDATE_FAILED.value,
            )
        return company

    def delete_company(self, company_id: UUID) -> None:
        self.company_user_service.check_if_user_is_in_company(
            user_id=self.context.user.id,
            company_id=company_id,
            role=CompanyDefaultRoles.OWNER.name_value,
        )
        self.company_repository.delete_company(company_id)
