from fastapi import status
from sqlalchemy.orm import joinedload

from app.models.company.address import CompanyAddressModel
from app.models.company.company import CompanyCreateModel, CompanyQueryParamsModel, CompanyReadModel, CompanyUpdateModel
from app.models.company.response_messages import CompanyResponseMessages
from app.models.company.roles import CompanyDefaultRoles
from app.models.generic_pagination import PaginatedResponse, PaginationMeta, apply_pagination, build_pagination_meta
from app.repository.base import BaseSQLRepository
from app.repository.company_user import CompanyUserRepository
from app.repository.database.tables import AssociationUserCompany, Company, Role
from app.utils.app_error import AppError


class CompanyRepository(BaseSQLRepository[Company]):
    model = Company

    def __init__(self, session):
        super().__init__(session)

    @staticmethod
    def _to_read_model(company: Company) -> CompanyReadModel:
        data = BaseSQLRepository.serialize(company)
        primary_meta_data = data.get("primary_meta_data") or {}
        if "address" in primary_meta_data:
            data["address"] = primary_meta_data["address"]
        return CompanyReadModel(**data)

    def _get_company_record_by_id(self, company_id: int) -> Company | None:
        return self._base_query().filter(Company.id == company_id).one_or_none()

    def _get_company_record_by_email(self, email: str) -> Company | None:
        return self._base_query().filter(Company.email == email).one_or_none()

    def create_company(self, payload: CompanyCreateModel, created_by) -> CompanyReadModel:
        company = self.create(**payload.model_dump(exclude={"address"}))
        if payload.address:
            company = self.update_json_field(
                company,
                column_name="primary_meta_data",
                key="address",
                value=payload.address.model_dump(),
            )

        for role in CompanyDefaultRoles:
            self.db_session.add(
                Role(
                    company_id=company.id,
                    name=role.name_value,
                    description=role.description,
                )
            )
        self.db_session.commit()

        CompanyUserRepository(self.db_session).add_user_to_company(
            company_id=company.id,
            payload=type("Payload", (), {"email": created_by.email, "role": CompanyDefaultRoles.ADMINISTRATOR.name_value})(),
            added_by=created_by,
        )
        company = self._get_company_record_by_id(company.id)
        return self._to_read_model(company)

    def get_company_by_id(self, company_id: str) -> CompanyReadModel:
        company = self._get_company_record_by_id(int(company_id))
        if not company:
            raise AppError(
                status_code=status.HTTP_404_NOT_FOUND,
                message=CompanyResponseMessages.COMPANY_NOT_FOUND.value,
            )
        return self._to_read_model(company)

    def get_company_by_email(self, email: str) -> CompanyReadModel:
        company = self._get_company_record_by_email(email)
        if not company:
            raise AppError(
                status_code=status.HTTP_404_NOT_FOUND,
                message=CompanyResponseMessages.COMPANY_NOT_FOUND.value,
            )
        return self._to_read_model(company)

    def update_company(self, payload: CompanyUpdateModel, company_id: str, user) -> CompanyReadModel:
        company = self._get_company_record_by_id(int(company_id))
        if not company:
            raise AppError(
                status_code=status.HTTP_400_BAD_REQUEST,
                message=CompanyResponseMessages.COMPANY_UPDATE_FAILED.value,
            )

        update_payload = payload.model_dump(exclude={"address"}, exclude_none=True)
        if update_payload:
            company = self.update(company, **update_payload)
        if payload.address:
            company = self.update_json_field(
                company,
                column_name="primary_meta_data",
                key="address",
                value=payload.address.model_dump(),
            )
        return self._to_read_model(company)

    def get_user_companies(self, user_id: int, params: CompanyQueryParamsModel) -> PaginatedResponse[CompanyReadModel]:
        query = (
            self.db_session.query(AssociationUserCompany)
            .join(AssociationUserCompany.company)
            .filter(
                AssociationUserCompany.user_id == user_id,
                AssociationUserCompany._closed_at.is_(None),
                Company._closed_at.is_(None),
            )
        )
        if params.role_name:
            query = query.filter(AssociationUserCompany.role_name.ilike(f"%{params.role_name}%"))
        if params.name:
            query = query.filter(Company.name.ilike(f"%{params.name}%"))
        if params.description:
            query = query.filter(Company.description.ilike(f"%{params.description}%"))
        if params.industry:
            query = query.filter(Company.industry.ilike(f"%{params.industry}%"))
        if params.email:
            query = query.filter(Company.email.ilike(f"%{params.email}%"))

        total = query.count()
        results = apply_pagination(
            query.options(joinedload(AssociationUserCompany.company)),
            page=params.page,
            limit=params.limit,
            order_by=[Company.id.asc()],
        ).all()
        companies = [self._to_read_model(assoc.company) for assoc in results]
        return PaginatedResponse[CompanyReadModel](
            records=companies,
            pagination=PaginationMeta(
                **build_pagination_meta(total_records=total, limit=params.limit, page=params.page)
            ),
        )
