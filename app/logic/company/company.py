from fastapi import status

# utils
from app.utils.app_error import AppError

# service and repository
from app.logic.company.user import CompanyUserService
from app.logic.company.repository.company import CompanyRepository

# database

# models
from app.models.company.company import (
    CompanyCreate,
    CompanyUpdate,
    CompanyRead,
)
from app.models.company.roles import CompanyDefaultRoles


from app.models.user.user import UserRead


from app.models.company.response_messages import CompanyResponseMessages


class CompanyService:

    @staticmethod
    def create_company(payload: CompanyCreate, created_by: UserRead) -> CompanyRead:
        """
        Create a new company and store its address in primary_meta_data.
        Also sets up default roles (Administrator, Viewer).
        """
        company_repository = CompanyRepository()
        company = company_repository.create_company(payload, created_by)
        if not company:
            raise AppError(
                status_code=status.HTTP_400_BAD_REQUEST,
                message=CompanyResponseMessages.COMPANY_CREATION_FAILED.value,
            )
        return company

    @staticmethod
    def get_company(
        user: UserRead, company_id: str = None, email: str = None
    ) -> CompanyRead:
        """
        Get a company by its ID.
        """
        if not company_id and not email:
            raise AppError(
                status_code=status.HTTP_400_BAD_REQUEST,
                message=CompanyResponseMessages.COMPANY_ID_OR_EMAIL_REQUIRED.value,
            )
        company_repository = CompanyRepository()
        company = None
        if company_id:
            company = company_repository.get_company_by_id(company_id)

        if email:
            company = company_repository.get_company_by_email(email)

        CompanyUserService.check_if_user_is_in_company(
            user_id=user.id,
            company_id=company.id,
        )

        return company

    @staticmethod
    def update_company(
        payload: CompanyUpdate, company_id: str, user: UserRead
    ) -> CompanyRead:
        """
        Update a company by its ID.
        """
        CompanyUserService.check_if_user_is_in_company(
            user_id=user.id,
            company_id=company_id,
            role=CompanyDefaultRoles.ADMINISTRATOR.name_value,
        )

        company_repository = CompanyRepository()
        company = company_repository.update_company(payload, company_id, user)
        if not company:
            raise AppError(
                status_code=status.HTTP_400_BAD_REQUEST,
                message=CompanyResponseMessages.COMPANY_UPDATE_FAILED.value,
            )
        return company
