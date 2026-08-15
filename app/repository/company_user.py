from uuid import UUID

from fastapi import status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.orm.attributes import flag_modified

from app.models.company.response_messages import (
    CompanyResponseMessages,
    CompanyUserResponseMessages,
)
from app.models.company.roles import CompanyDefaultRoles, RoleReadModel
from app.models.permissions import PermissionReadModel
from app.models.company.user import CompanyUserAddModel, CompanyUserReadModel
from app.models.generic_pagination import (
    PaginatedResponse,
    apply_pagination,
    build_pagination_meta,
)
from app.models.user.user import UserQueryParams
from app.repository.base import BaseSQLRepository
from app.repository.company_role import CompanyRoleAssignmentRepository
from app.repository.database.tables import AssociationUserCompany, Role, User
from app.utils.app_error import AppError


class CompanyUserRepository(BaseSQLRepository[AssociationUserCompany]):
    model = AssociationUserCompany

    def __init__(self, session: Session):
        super().__init__(session)

    @staticmethod
    def _to_company_user(
        user: User,
        role: Role,
        permissions: list[PermissionReadModel] | None = None,
    ) -> CompanyUserReadModel:
        metadata = user.primary_meta_data or {}
        return CompanyUserReadModel(
            id=user.id,
            first_name=user.first_name,
            last_name=user.last_name,
            email=user.email,
            phone_number=user.phone_number,
            status=metadata.get("status"),
            is_superuser=user.is_superuser,
            role=RoleReadModel(
                id=str(role.id),
                name=role.name,
                description=role.description,
                permissions=permissions or [],
            ),
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
            query = query.join(AssociationUserCompany.role).filter(
                Role.name == resolved_role_name
            )
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

        role = CompanyRoleAssignmentRepository(
            company_id=company_id, session=self.db_session
        ).ensure_role_name_assigned(payload.role)

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
            role_id=role.id,
            primary_meta_data={"added_by": added_by.model_dump(mode="json")},
            secondary_meta_data={"_legacy_role_name": role.name},
        )
        from app.repository.permission import RolePermissionRepository

        permissions = RolePermissionRepository(
            self.db_session
        ).get_company_role_permissions(company_id, role.id)
        return self._to_company_user(user, role, permissions)

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
            and assoc.role.name == CompanyDefaultRoles.ADMINISTRATOR.name_value
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
        from app.repository.permission import RolePermissionRepository

        permissions = RolePermissionRepository(
            self.db_session
        ).get_company_role_permissions(company_id, assoc.role.id)
        return self._to_company_user(user, assoc.role, permissions)

    def update_user_role(
        self, company_id: UUID, user_id: UUID, role_name: str, updated_by
    ) -> CompanyUserReadModel:
        role = CompanyRoleAssignmentRepository(
            company_id=company_id, session=self.db_session
        ).ensure_role_name_assigned(role_name)

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

        assoc.role_id = role.id
        assoc.primary_meta_data["updated_by"] = updated_by.model_dump(mode="json")
        assoc.secondary_meta_data["_legacy_role_name"] = role.name
        flag_modified(assoc, "primary_meta_data")
        flag_modified(assoc, "secondary_meta_data")
        self.db_session.add(assoc)
        self.db_session.commit()
        self.db_session.refresh(assoc)

        user = self.db_session.query(User).filter(User.id == user_id).one()
        from app.repository.permission import RolePermissionRepository

        permissions = RolePermissionRepository(
            self.db_session
        ).get_company_role_permissions(company_id, role.id)
        return self._to_company_user(user, role, permissions)

    def get_company_users(
        self, company_id: UUID, params: UserQueryParams
    ) -> PaginatedResponse[CompanyUserReadModel]:
        query = (
            self.db_session.query(AssociationUserCompany)
            .join(AssociationUserCompany.user)
            .join(AssociationUserCompany.role)
            .filter(
                AssociationUserCompany.company_id == company_id,
                AssociationUserCompany._closed_at.is_(None),
                User._closed_at.is_(None),
            )
        )

        if params.role_name:
            query = query.filter(Role.name.ilike(f"%{params.role_name}%"))
        if params.first_name:
            query = query.filter(User.first_name.ilike(f"%{params.first_name}%"))
        if params.last_name:
            query = query.filter(User.last_name.ilike(f"%{params.last_name}%"))
        if params.email:
            query = query.filter(User.email.ilike(f"%{params.email}%"))

        total = query.count()
        results = apply_pagination(
            query.options(
                joinedload(AssociationUserCompany.user),
                joinedload(AssociationUserCompany.role),
            ),
            page=params.page,
            limit=params.limit,
            order_by=[
                AssociationUserCompany._created_at.asc(),
                User.id.asc(),
            ],
        ).all()

        from app.repository.permission import RolePermissionRepository

        permission_map = RolePermissionRepository(
            self.db_session
        ).effective_permissions_by_assignments(
            [(company_id, assoc.role_id) for assoc in results]
        )
        users = [
            self._to_company_user(
                assoc.user,
                assoc.role,
                permission_map.get((company_id, assoc.role_id), []),
            )
            for assoc in results
        ]
        return PaginatedResponse[CompanyUserReadModel](
            records=users,
            pagination=build_pagination_meta(
                total_records=total,
                limit=params.limit,
                page=params.page,
            ),
        )
