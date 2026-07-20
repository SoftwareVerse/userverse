from uuid import UUID

from fastapi import status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.orm.attributes import flag_modified

from app.models.company.response_messages import (
    CompanyResponseMessages,
    CompanyUserResponseMessages,
)
from app.models.company.roles import CompanyDefaultRoles
from app.models.company.user import CompanyUserAddModel, CompanyUserReadModel
from app.models.generic_pagination import (
    PaginatedResponse,
    apply_pagination,
    build_pagination_meta,
)
from app.models.user.user import UserQueryParams
from app.repository.base import BaseSQLRepository
from app.repository.database.tables import AssociationUserCompany, Role, User
from app.utils.app_error import AppError


class CompanyUserRepository(BaseSQLRepository[AssociationUserCompany]):
    model = AssociationUserCompany

    def __init__(self, session: Session):
        super().__init__(session)

    @staticmethod
    def _to_company_user(user: User, role_name: str) -> CompanyUserReadModel:
        metadata = user.primary_meta_data or {}
        return CompanyUserReadModel(
            id=user.id,
            first_name=user.first_name,
            last_name=user.last_name,
            email=user.email,
            phone_number=user.phone_number,
            status=metadata.get("status"),
            is_superuser=user.is_superuser,
            role_name=role_name,
        )

    def is_user_linked_to_company(
        self,
        user_id: UUID,
        company_id: UUID,
        role_name: str | None = None,
        role: str | None = None,
    ) -> bool:
        resolved_role_name = role_name if role_name is not None else role
        query = self._base_query().filter_by(
            user_id=user_id,
            company_id=company_id,
            _closed_at=None,
        )
        if resolved_role_name:
            query = query.filter_by(role_name=resolved_role_name)
        return self.db_session.query(query.exists()).scalar()

    def ensure_user_linked_to_company(
        self, user_id: UUID, company_id: UUID, role_name: str | None = None
    ) -> bool:
        linked_company = self.is_user_linked_to_company(user_id, company_id, role_name)
        if not linked_company:
            raise AppError(
                status_code=status.HTTP_403_FORBIDDEN,
                message=CompanyResponseMessages.UNAUTHORIZED_COMPANY_ACCESS.value,
            )
        return linked_company

    def add_user_to_company(
        self, company_id: UUID, payload: CompanyUserAddModel, added_by
    ) -> CompanyUserReadModel:
        user = self.db_session.query(User).filter(User.email == payload.email).first()
        if not user:
            raise AppError(
                status_code=status.HTTP_404_NOT_FOUND,
                message=CompanyUserResponseMessages.ADD_USER_FAILED.value,
                error=CompanyResponseMessages.UNAUTHORIZED_COMPANY_ACCESS.value,
            )

        role = (
            self.db_session.query(Role)
            .filter(
                Role.company_id == company_id,
                Role.name == payload.role,
                Role._closed_at.is_(None),
            )
            .one_or_none()
        )
        if not role:
            raise AppError(
                status_code=status.HTTP_400_BAD_REQUEST,
                message=CompanyUserResponseMessages.ADD_USER_FAILED.value,
                error=f"Role: {payload.role} is not linked to the company",
            )

        existing = (
            self._base_query()
            .filter_by(user_id=user.id, company_id=company_id, _closed_at=None)
            .first()
        )
        if existing:
            raise AppError(
                status_code=status.HTTP_400_BAD_REQUEST,
                message=CompanyUserResponseMessages.ADD_EXISTING_USER_FAILED.value,
            )

        assoc = self.create(
            user_id=user.id,
            company_id=company_id,
            role_name=role.name,
            primary_meta_data={"added_by": added_by.model_dump(mode="json")},
        )
        return self._to_company_user(user, assoc.role_name)

    def remove_user_from_company(
        self, company_id: UUID, user_id: UUID, removed_by
    ) -> CompanyUserReadModel:
        assoc = (
            self._base_query()
            .filter_by(user_id=user_id, company_id=company_id, _closed_at=None)
            .first()
        )
        if not assoc:
            raise AppError(
                status_code=status.HTTP_403_FORBIDDEN,
                message=CompanyUserResponseMessages.USER_ALREADY_REMOVED.value,
            )

        if (
            assoc.user_id == removed_by.id
            and assoc.role_name == CompanyDefaultRoles.ADMINISTRATOR.name_value
        ):
            raise AppError(
                status_code=status.HTTP_400_BAD_REQUEST,
                message=CompanyUserResponseMessages.SUPER_ADMIN_REMOVE_FORBIDDEN.value,
            )

        assoc.primary_meta_data["removed_by"] = removed_by.model_dump(mode="json")
        flag_modified(assoc, "primary_meta_data")
        assoc._closed_at = self._now_sql()
        self.db_session.add(assoc)
        self.db_session.commit()
        self.db_session.refresh(assoc)

        user = self.db_session.query(User).filter(User.id == user_id).one()
        return self._to_company_user(user, assoc.role_name)

    def update_user_role(
        self, company_id: UUID, user_id: UUID, role_name: str, updated_by
    ) -> CompanyUserReadModel:
        role = (
            self.db_session.query(Role)
            .filter(
                Role.company_id == company_id,
                Role.name == role_name,
                Role._closed_at.is_(None),
            )
            .one_or_none()
        )
        if not role:
            raise AppError(
                status_code=status.HTTP_400_BAD_REQUEST,
                message=CompanyUserResponseMessages.UPDATE_USER_ROLE_FAILED.value,
                error=f"Role: {role_name} is not linked to the company",
            )

        assoc = (
            self._base_query()
            .filter_by(user_id=user_id, company_id=company_id, _closed_at=None)
            .first()
        )
        if not assoc:
            raise AppError(
                status_code=status.HTTP_404_NOT_FOUND,
                message=CompanyUserResponseMessages.UPDATE_USER_ROLE_FAILED.value,
                error=CompanyResponseMessages.COMPANY_NOT_FOUND.value,
            )

        assoc.role_name = role.name
        assoc.primary_meta_data["updated_by"] = updated_by.model_dump(mode="json")
        flag_modified(assoc, "primary_meta_data")
        self.db_session.add(assoc)
        self.db_session.commit()
        self.db_session.refresh(assoc)

        user = self.db_session.query(User).filter(User.id == user_id).one()
        return self._to_company_user(user, assoc.role_name)

    def get_company_users(
        self, company_id: UUID, params: UserQueryParams
    ) -> PaginatedResponse[CompanyUserReadModel]:
        query = (
            self.db_session.query(AssociationUserCompany)
            .join(AssociationUserCompany.user)
            .filter(
                AssociationUserCompany.company_id == company_id,
                AssociationUserCompany._closed_at.is_(None),
                User._closed_at.is_(None),
            )
        )

        if params.role_name:
            query = query.filter(
                AssociationUserCompany.role_name.ilike(f"%{params.role_name}%")
            )
        if params.first_name:
            query = query.filter(User.first_name.ilike(f"%{params.first_name}%"))
        if params.last_name:
            query = query.filter(User.last_name.ilike(f"%{params.last_name}%"))
        if params.email:
            query = query.filter(User.email.ilike(f"%{params.email}%"))

        total = query.count()
        results = apply_pagination(
            query.options(joinedload(AssociationUserCompany.user)),
            page=params.page,
            limit=params.limit,
            order_by=[
                AssociationUserCompany._created_at.asc(),
                User.id.asc(),
            ],
        ).all()

        users = [
            self._to_company_user(assoc.user, assoc.role_name) for assoc in results
        ]
        return PaginatedResponse[CompanyUserReadModel](
            records=users,
            pagination=build_pagination_meta(
                total_records=total,
                limit=params.limit,
                page=params.page,
            ),
        )
