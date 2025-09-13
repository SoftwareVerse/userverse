from fastapi import status

# utils
from app.utils.app_error import AppError

# database
from sqlalchemy.orm import Session, joinedload
from app.database.company import Company
from app.database.role import Role
from app.database.association_user_company import AssociationUserCompany

# models
from app.models.company.address import CompanyAddressModel
from app.models.company.company import (
    CompanyQueryParamsModel,
    CompanyReadModel,
    CompanyCreateModel,
    CompanyUpdateModel,
)
from app.models.company.roles import CompanyDefaultRoles
from app.models.company.response_messages import CompanyResponseMessages
from app.models.generic_pagination import PaginatedResponse, PaginationMeta


class CompanyRepository:
    def __init__(self, session: Session):
        self.session = session

    def create_company(
        self, payload: CompanyCreateModel, created_by
    ) -> CompanyReadModel:
        session = self.session
        company = self._create_company_record(session, payload)
        company_id = company["id"]

        if payload.address:
            self._add_company_address(session, company_id, payload.address)

        self._create_default_roles(session, company_id)

        AssociationUserCompany.link_user(
            session,
            user_id=created_by.id,
            company_id=company_id,
            role_name=CompanyDefaultRoles.ADMINISTRATOR.name_value,
            added_by=created_by,
        )

        registered_company = self._get_registered_company(session, company_id)
        return CompanyReadModel(**registered_company)

    def get_company_by_id(self, company_id: str) -> CompanyReadModel:
        session = self.session
        company = self._get_registered_company(session, company_id)

        if not company:
            raise AppError(
                status_code=status.HTTP_404_NOT_FOUND,
                message=CompanyResponseMessages.COMPANY_NOT_FOUND.value,
            )

        return CompanyReadModel(**company)

    def get_company_by_email(self, email: str) -> CompanyReadModel:
        session = self.session
        company = Company.get_company_by_email(session, email)

        if not company:
            raise AppError(
                status_code=status.HTTP_404_NOT_FOUND,
                message=CompanyResponseMessages.COMPANY_NOT_FOUND.value,
            )

        return CompanyReadModel(**self._get_registered_company(session, company["id"]))

    def update_company(
        self, payload: CompanyUpdateModel, company_id: str, user
    ) -> CompanyReadModel:
        session = self.session
        company = Company.update(session, company_id, **payload.model_dump())

        if payload.address:
            self._add_company_address(session, company_id, payload.address)

        if not company:
            raise AppError(
                status_code=status.HTTP_400_BAD_REQUEST,
                message=CompanyResponseMessages.COMPANY_UPDATE_FAILED.value,
            )

        return CompanyReadModel(**self._get_registered_company(session, company["id"]))

    def get_user_companies(
        self, user_id: int, params: CompanyQueryParamsModel
    ) -> PaginatedResponse[CompanyReadModel]:
        session = self.session
        query = (
            session.query(AssociationUserCompany)
            .join(AssociationUserCompany.company)
            .filter(
                AssociationUserCompany.user_id == user_id,
                AssociationUserCompany._closed_at.is_(None),
                Company._closed_at.is_(None),
            )
        )

        if params.role_name:
            query = query.filter(
                AssociationUserCompany.role_name.ilike(f"%{params.role_name}%")
            )
        if params.name:
            query = query.filter(Company.name.ilike(f"%{params.name}%"))
        if params.description:
            query = query.filter(Company.description.ilike(f"%{params.description}%"))
        if params.industry:
            query = query.filter(Company.industry.ilike(f"%{params.industry}%"))
        if params.email:
            query = query.filter(Company.email.ilike(f"%{params.email}%"))

        total = query.count()

        results = (
            query.options(joinedload(AssociationUserCompany.company))
            .offset(params.offset)
            .limit(params.limit)
            .all()
        )

        companies = []
        for assoc in results:
            registered_company = Company.to_dict(assoc.company)
            if "primary_meta_data" in registered_company:
                primary_meta_data = registered_company.get("primary_meta_data")
                if "address" in primary_meta_data:
                    address = primary_meta_data.get("address")
                    registered_company["address"] = address

            companies.append(CompanyReadModel(**registered_company))

        return PaginatedResponse[CompanyReadModel](
            records=companies,
            pagination=PaginationMeta(
                total_records=total,
                limit=params.limit,
                current_page=(params.offset // params.limit) + 1,
                total_pages=(total + params.limit - 1) // params.limit,
            ),
        )

    def _create_company_record(self, session, payload: CompanyCreateModel) -> dict:
        company = Company.create(session, **payload.model_dump(exclude={"address"}))

        if not company:
            raise AppError(
                status_code=status.HTTP_400_BAD_REQUEST,
                message=CompanyResponseMessages.COMPANY_CREATION_FAILED.value,
            )

        return company

    def _add_company_address(
        self, session, company_id: str, address: CompanyAddressModel
    ) -> None:
        Company.update_json_field(
            session,
            record_id=company_id,
            column_name="primary_meta_data",
            key="address",
            value=address.model_dump(),
        )

    def _create_default_roles(self, session, company_id: str) -> None:
        for role in CompanyDefaultRoles:
            Role.create(
                session,
                company_id=company_id,
                name=role.name_value,
                description=role.description,
            )

    def _get_registered_company(self, session, company_id: str) -> dict:
        registered_company = Company.get_by_id(session, company_id)

        if "primary_meta_data" in registered_company:
            primary_meta_data = registered_company.get("primary_meta_data")
            if "address" in primary_meta_data:
                address = primary_meta_data.get("address")
                registered_company["address"] = address

        return registered_company
