from fastapi import status

# utils
from app.models.company.user import CompanyUserAdd, CompanyUserRead
from app.models.generic_pagination import PaginatedResponse, PaginationMeta
from app.utils.app_error import AppError

# database
from app.database.session_manager import DatabaseSessionManager
from app.database.user import User
from app.database.role import Role
from app.database.association_user_company import AssociationUserCompany
from sqlalchemy.orm import joinedload

# models
from app.models.user.user import UserQueryParams


class CompanyUserRepository:
    def __init__(self):
        self.db_manager = DatabaseSessionManager()

    def add_user_to_company(
        self, company_id: int, payload: CompanyUserAdd, added_by
    ) -> CompanyUserRead:
        with self.db_manager.session_object() as session:
            user = User.get_user_by_email(session=session, email=payload.email)
            user_id = user.get("id")

            role = Role.role_belongs_to_company(
                session=session, company_id=company_id, role_name=payload.role
            )
            if not role:
                raise AppError(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    message=f"Role: {payload.role} is not linked to company",
                )

            assoc = AssociationUserCompany.link_user(
                session=session,
                company_id=company_id,
                user_id=user_id,
                role_name=role.get("name"),
                added_by=added_by,
            )

            return CompanyUserRead(**user, role_name=assoc.role_name)

    def remove_user_from_company(
        self, company_id: int, user_id: int, removed_by
    ) -> CompanyUserRead:
        with self.db_manager.session_object() as session:
            assoc = AssociationUserCompany.unlink_user(
                session=session,
                company_id=company_id,
                user_id=user_id,
                removed_by=removed_by,
            )

            user = User.get_by_id(session=session, record_id=user_id)
            return CompanyUserRead(**user, role_name=assoc.role_name)

    def get_company_users(
        self, company_id: int, params: UserQueryParams
    ) -> PaginatedResponse[CompanyUserRead]:
        with self.db_manager.session_object() as session:
            query = (
                session.query(AssociationUserCompany)
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

            results = (
                query.options(joinedload(AssociationUserCompany.user))
                .offset(params.offset)
                .limit(params.limit)
                .all()
            )

            users = [
                CompanyUserRead(**User.to_dict(assoc.user), role_name=assoc.role_name)
                for assoc in results
            ]

            return PaginatedResponse[CompanyUserRead](
                records=users,
                pagination=PaginationMeta(
                    total_records=total,
                    limit=params.limit,
                    offset=params.offset,
                    current_page=params.offset // params.limit + 1,
                    total_pages=(total + params.limit - 1) // params.limit,
                ),
            )
