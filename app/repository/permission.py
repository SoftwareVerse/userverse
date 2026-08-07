from __future__ import annotations

from collections import defaultdict
from uuid import UUID

from fastapi import status
from sqlalchemy import tuple_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.company.roles import RoleReadModel
from app.models.generic_pagination import PaginatedResponse
from app.models.permission_response_messages import (
    PermissionResponseMessages,
    PlatformRoleResponseMessages,
)
from app.models.permissions import (
    PermissionCreateModel,
    PermissionQueryParamsModel,
    PermissionReadModel,
    PermissionScope,
    PermissionUpdateModel,
)
from app.models.user.account_status import UserAccountStatus
from app.repository.base import BaseSQLRepository
from app.repository.database.tables import (
    Company,
    CompanyPermission,
    CompanyRole,
    CompanyRolePermission,
    GlobalPermission,
    Role,
    RoleGlobalPermission,
    User,
    UserRole,
)
from app.utils.app_error import AppError


def _global_permission_model(permission: GlobalPermission) -> PermissionReadModel:
    return PermissionReadModel(
        id=permission.id,
        name=permission.name,
        description=permission.description,
        scope=PermissionScope.GLOBAL,
        company_id=None,
    )


def _company_permission_model(permission: CompanyPermission) -> PermissionReadModel:
    return PermissionReadModel(
        id=permission.id,
        name=permission.name,
        description=permission.description,
        scope=PermissionScope.COMPANY,
        company_id=permission.company_id,
    )


def _permission_sort_key(permission: PermissionReadModel) -> tuple[str, str, str]:
    return (permission.scope.value, permission.name, str(permission.id))


class GlobalPermissionRepository(BaseSQLRepository[GlobalPermission]):
    model = GlobalPermission

    def get_record(self, permission_id: UUID) -> GlobalPermission | None:
        return (
            self._base_query()
            .filter(
                GlobalPermission.id == permission_id,
                GlobalPermission._closed_at.is_(None),
            )
            .one_or_none()
        )

    def ensure_record(self, permission_id: UUID) -> GlobalPermission:
        permission = self.get_record(permission_id)
        if permission is None:
            raise AppError(
                status_code=status.HTTP_404_NOT_FOUND,
                message=PermissionResponseMessages.NOT_FOUND.value,
            )
        return permission

    def create_permission(
        self,
        payload: PermissionCreateModel,
        created_by,
    ) -> PermissionReadModel:
        permission = GlobalPermission(
            name=payload.name,
            description=payload.description,
            primary_meta_data={"created_by": created_by.model_dump(mode="json")},
        )
        try:
            self.db_session.add(permission)
            self.db_session.commit()
            self.db_session.refresh(permission)
        except IntegrityError as exc:
            self.db_session.rollback()
            raise AppError(
                status_code=status.HTTP_409_CONFLICT,
                message=PermissionResponseMessages.ALREADY_EXISTS.value,
            ) from exc
        return _global_permission_model(permission)

    def get_permissions(
        self,
        payload: PermissionQueryParamsModel,
    ) -> PaginatedResponse[PermissionReadModel]:
        query = self._base_query().filter(GlobalPermission._closed_at.is_(None))
        if payload.name:
            query = query.filter(GlobalPermission.name.ilike(f"%{payload.name}%"))
        if payload.description:
            query = query.filter(
                GlobalPermission.description.ilike(f"%{payload.description}%")
            )
        total = query.count()
        records = (
            query.order_by(GlobalPermission.name.asc(), GlobalPermission.id.asc())
            .offset((payload.page - 1) * payload.limit)
            .limit(payload.limit)
            .all()
        )
        from app.models.generic_pagination import build_pagination_meta

        return PaginatedResponse[PermissionReadModel](
            records=[_global_permission_model(record) for record in records],
            pagination=build_pagination_meta(
                total_records=total,
                limit=payload.limit,
                page=payload.page,
            ),
        )

    def update_permission(
        self,
        permission_id: UUID,
        payload: PermissionUpdateModel,
    ) -> PermissionReadModel:
        permission = self.ensure_record(permission_id)
        if "name" in payload.model_fields_set:
            permission.name = payload.name
        if "description" in payload.model_fields_set:
            permission.description = payload.description
        try:
            self.db_session.add(permission)
            self.db_session.commit()
            self.db_session.refresh(permission)
        except IntegrityError as exc:
            self.db_session.rollback()
            raise AppError(
                status_code=status.HTTP_409_CONFLICT,
                message=PermissionResponseMessages.ALREADY_EXISTS.value,
            ) from exc
        return _global_permission_model(permission)

    def delete_permission(self, permission_id: UUID) -> dict[str, str]:
        permission = self.ensure_record(permission_id)
        self.db_session.query(RoleGlobalPermission).filter(
            RoleGlobalPermission.global_permission_id == permission_id
        ).delete(synchronize_session=False)
        self.db_session.delete(permission)
        self.db_session.commit()
        return {"message": f"Permission '{permission.name}' deleted successfully."}


class CompanyPermissionRepository(BaseSQLRepository[CompanyPermission]):
    model = CompanyPermission

    def __init__(self, company_id: UUID, session: Session):
        super().__init__(session)
        self.company_id = company_id

    def ensure_company(self) -> Company:
        company = (
            self.db_session.query(Company)
            .filter(
                Company.id == self.company_id,
                Company._closed_at.is_(None),
            )
            .one_or_none()
        )
        if company is None:
            raise AppError(
                status_code=status.HTTP_404_NOT_FOUND,
                message="Company not found.",
            )
        return company

    def get_record(self, permission_id: UUID) -> CompanyPermission | None:
        return (
            self._base_query()
            .filter(
                CompanyPermission.company_id == self.company_id,
                CompanyPermission.id == permission_id,
                CompanyPermission._closed_at.is_(None),
            )
            .one_or_none()
        )

    def ensure_record(self, permission_id: UUID) -> CompanyPermission:
        permission = self.get_record(permission_id)
        if permission is None:
            raise AppError(
                status_code=status.HTTP_404_NOT_FOUND,
                message=PermissionResponseMessages.NOT_FOUND.value,
            )
        return permission

    def create_permission(
        self,
        payload: PermissionCreateModel,
        created_by,
    ) -> PermissionReadModel:
        self.ensure_company()
        permission = CompanyPermission(
            company_id=self.company_id,
            name=payload.name,
            description=payload.description,
            primary_meta_data={"created_by": created_by.model_dump(mode="json")},
        )
        try:
            self.db_session.add(permission)
            self.db_session.commit()
            self.db_session.refresh(permission)
        except IntegrityError as exc:
            self.db_session.rollback()
            raise AppError(
                status_code=status.HTTP_409_CONFLICT,
                message=PermissionResponseMessages.ALREADY_EXISTS.value,
            ) from exc
        return _company_permission_model(permission)

    def get_permissions(
        self,
        payload: PermissionQueryParamsModel,
    ) -> PaginatedResponse[PermissionReadModel]:
        self.ensure_company()
        query = self._base_query().filter(
            CompanyPermission.company_id == self.company_id,
            CompanyPermission._closed_at.is_(None),
        )
        if payload.name:
            query = query.filter(CompanyPermission.name.ilike(f"%{payload.name}%"))
        if payload.description:
            query = query.filter(
                CompanyPermission.description.ilike(f"%{payload.description}%")
            )
        total = query.count()
        records = (
            query.order_by(CompanyPermission.name.asc(), CompanyPermission.id.asc())
            .offset((payload.page - 1) * payload.limit)
            .limit(payload.limit)
            .all()
        )
        from app.models.generic_pagination import build_pagination_meta

        return PaginatedResponse[PermissionReadModel](
            records=[_company_permission_model(record) for record in records],
            pagination=build_pagination_meta(
                total_records=total,
                limit=payload.limit,
                page=payload.page,
            ),
        )

    def update_permission(
        self,
        permission_id: UUID,
        payload: PermissionUpdateModel,
    ) -> PermissionReadModel:
        permission = self.ensure_record(permission_id)
        if "name" in payload.model_fields_set:
            permission.name = payload.name
        if "description" in payload.model_fields_set:
            permission.description = payload.description
        try:
            self.db_session.add(permission)
            self.db_session.commit()
            self.db_session.refresh(permission)
        except IntegrityError as exc:
            self.db_session.rollback()
            raise AppError(
                status_code=status.HTTP_409_CONFLICT,
                message=PermissionResponseMessages.ALREADY_EXISTS.value,
            ) from exc
        return _company_permission_model(permission)

    def delete_permission(self, permission_id: UUID) -> dict[str, str]:
        permission = self.ensure_record(permission_id)
        self.db_session.query(CompanyRolePermission).filter(
            CompanyRolePermission.company_id == self.company_id,
            CompanyRolePermission.company_permission_id == permission_id,
        ).delete(synchronize_session=False)
        self.db_session.delete(permission)
        self.db_session.commit()
        return {"message": f"Permission '{permission.name}' deleted successfully."}


class RolePermissionRepository:
    def __init__(self, session: Session):
        self.db_session = session

    def _ensure_role(self, role_id: UUID) -> Role:
        role = (
            self.db_session.query(Role)
            .filter(Role.id == role_id, Role._closed_at.is_(None))
            .one_or_none()
        )
        if role is None:
            raise AppError(
                status_code=status.HTTP_404_NOT_FOUND,
                message="No role found with the given identifier.",
            )
        return role

    def _ensure_company_role(self, company_id: UUID, role_id: UUID) -> CompanyRole:
        assignment = (
            self.db_session.query(CompanyRole)
            .filter(
                CompanyRole.company_id == company_id,
                CompanyRole.role_id == role_id,
                CompanyRole._closed_at.is_(None),
            )
            .one_or_none()
        )
        if assignment is None:
            raise AppError(
                status_code=status.HTTP_404_NOT_FOUND,
                message="Role is not linked to the company.",
            )
        return assignment

    def global_permissions_by_role_ids(
        self,
        role_ids: list[UUID] | set[UUID],
    ) -> dict[UUID, list[PermissionReadModel]]:
        result: dict[UUID, list[PermissionReadModel]] = defaultdict(list)
        if not role_ids:
            return result
        rows = (
            self.db_session.query(RoleGlobalPermission, GlobalPermission)
            .join(
                GlobalPermission,
                GlobalPermission.id == RoleGlobalPermission.global_permission_id,
            )
            .filter(
                RoleGlobalPermission.role_id.in_(role_ids),
                RoleGlobalPermission._closed_at.is_(None),
                GlobalPermission._closed_at.is_(None),
            )
            .all()
        )
        for link, permission in rows:
            result[link.role_id].append(_global_permission_model(permission))
        for permissions in result.values():
            permissions.sort(key=_permission_sort_key)
        return result

    def effective_permissions_by_assignments(
        self,
        assignments: list[tuple[UUID, UUID]],
    ) -> dict[tuple[UUID, UUID], list[PermissionReadModel]]:
        pairs = list(dict.fromkeys(assignments))
        result: dict[tuple[UUID, UUID], list[PermissionReadModel]] = {}
        if not pairs:
            return result
        global_map = self.global_permissions_by_role_ids(
            {role_id for _, role_id in pairs}
        )
        for company_id, role_id in pairs:
            result[(company_id, role_id)] = list(global_map.get(role_id, []))

        rows = (
            self.db_session.query(CompanyRolePermission, CompanyPermission)
            .join(
                CompanyPermission,
                tuple_(
                    CompanyPermission.company_id,
                    CompanyPermission.id,
                )
                == tuple_(
                    CompanyRolePermission.company_id,
                    CompanyRolePermission.company_permission_id,
                ),
            )
            .filter(
                tuple_(
                    CompanyRolePermission.company_id,
                    CompanyRolePermission.role_id,
                ).in_(pairs),
                CompanyRolePermission._closed_at.is_(None),
                CompanyPermission._closed_at.is_(None),
            )
            .all()
        )
        for link, permission in rows:
            result[(link.company_id, link.role_id)].append(
                _company_permission_model(permission)
            )
        for permissions in result.values():
            permissions.sort(key=_permission_sort_key)
        return result

    def get_global_role_permissions(self, role_id: UUID) -> list[PermissionReadModel]:
        self._ensure_role(role_id)
        return self.global_permissions_by_role_ids([role_id]).get(role_id, [])

    def get_company_role_permissions(
        self,
        company_id: UUID,
        role_id: UUID,
    ) -> list[PermissionReadModel]:
        self._ensure_company_role(company_id, role_id)
        return self.effective_permissions_by_assignments([(company_id, role_id)]).get(
            (company_id, role_id),
            [],
        )

    def global_role_read(self, role: Role) -> RoleReadModel:
        return RoleReadModel(
            id=str(role.id),
            name=role.name,
            description=role.description,
            permissions=self.global_permissions_by_role_ids([role.id]).get(role.id, []),
        )

    def company_role_read(self, company_id: UUID, role: Role) -> RoleReadModel:
        permissions = self.effective_permissions_by_assignments(
            [(company_id, role.id)]
        ).get((company_id, role.id), [])
        return RoleReadModel(
            id=str(role.id),
            name=role.name,
            description=role.description,
            permissions=permissions,
        )

    def assign_global_permission(
        self,
        role_id: UUID,
        permission_id: UUID,
    ) -> RoleReadModel:
        role = self._ensure_role(role_id)
        permission = GlobalPermissionRepository(self.db_session).ensure_record(
            permission_id
        )
        existing = (
            self.db_session.query(RoleGlobalPermission)
            .filter_by(role_id=role_id, global_permission_id=permission.id)
            .one_or_none()
        )
        if existing is not None:
            raise AppError(
                status_code=status.HTTP_409_CONFLICT,
                message=PermissionResponseMessages.ALREADY_ASSIGNED.value,
            )
        self.db_session.add(
            RoleGlobalPermission(
                role_id=role_id,
                global_permission_id=permission.id,
            )
        )
        self.db_session.commit()
        return self.global_role_read(role)

    def remove_global_permission(
        self,
        role_id: UUID,
        permission_id: UUID,
    ) -> RoleReadModel:
        role = self._ensure_role(role_id)
        GlobalPermissionRepository(self.db_session).ensure_record(permission_id)
        link = (
            self.db_session.query(RoleGlobalPermission)
            .filter_by(role_id=role_id, global_permission_id=permission_id)
            .one_or_none()
        )
        if link is None:
            raise AppError(
                status_code=status.HTTP_404_NOT_FOUND,
                message=PermissionResponseMessages.ASSIGNMENT_NOT_FOUND.value,
            )
        self.db_session.delete(link)
        self.db_session.commit()
        return self.global_role_read(role)

    def assign_company_permission(
        self,
        company_id: UUID,
        role_id: UUID,
        permission_id: UUID,
    ) -> RoleReadModel:
        self._ensure_company_role(company_id, role_id)
        role = self._ensure_role(role_id)
        permission = CompanyPermissionRepository(
            company_id,
            self.db_session,
        ).ensure_record(permission_id)
        existing = (
            self.db_session.query(CompanyRolePermission)
            .filter_by(
                company_id=company_id,
                role_id=role_id,
                company_permission_id=permission.id,
            )
            .one_or_none()
        )
        if existing is not None:
            raise AppError(
                status_code=status.HTTP_409_CONFLICT,
                message=PermissionResponseMessages.ALREADY_ASSIGNED.value,
            )
        self.db_session.add(
            CompanyRolePermission(
                company_id=company_id,
                role_id=role_id,
                company_permission_id=permission.id,
            )
        )
        try:
            self.db_session.commit()
        except IntegrityError as exc:
            self.db_session.rollback()
            raise AppError(
                status_code=status.HTTP_404_NOT_FOUND,
                message=PermissionResponseMessages.NOT_FOUND.value,
            ) from exc
        return self.company_role_read(company_id, role)

    def remove_company_permission(
        self,
        company_id: UUID,
        role_id: UUID,
        permission_id: UUID,
    ) -> RoleReadModel:
        self._ensure_company_role(company_id, role_id)
        role = self._ensure_role(role_id)
        CompanyPermissionRepository(company_id, self.db_session).ensure_record(
            permission_id
        )
        link = (
            self.db_session.query(CompanyRolePermission)
            .filter_by(
                company_id=company_id,
                role_id=role_id,
                company_permission_id=permission_id,
            )
            .one_or_none()
        )
        if link is None:
            raise AppError(
                status_code=status.HTTP_404_NOT_FOUND,
                message=PermissionResponseMessages.ASSIGNMENT_NOT_FOUND.value,
            )
        self.db_session.delete(link)
        self.db_session.commit()
        return self.company_role_read(company_id, role)


class PlatformRoleRepository:
    def __init__(self, session: Session):
        self.db_session = session

    def _ensure_active_user(self, user_id: UUID) -> User:
        user = (
            self.db_session.query(User)
            .filter(User.id == user_id, User._closed_at.is_(None))
            .one_or_none()
        )
        status_value = (user.primary_meta_data or {}).get("status") if user else None
        if user is None or status_value != UserAccountStatus.ACTIVE.name_value:
            raise AppError(
                status_code=status.HTTP_404_NOT_FOUND,
                message="No active user found with the given identifier.",
            )
        return user

    def get_roles(self, user_id: UUID) -> list[RoleReadModel]:
        self._ensure_active_user(user_id)
        roles = (
            self.db_session.query(Role)
            .join(UserRole, UserRole.role_id == Role.id)
            .filter(
                UserRole.user_id == user_id,
                UserRole._closed_at.is_(None),
                Role._closed_at.is_(None),
            )
            .order_by(Role.name.asc(), Role.id.asc())
            .all()
        )
        permission_map = RolePermissionRepository(
            self.db_session
        ).global_permissions_by_role_ids({role.id for role in roles})
        return [
            RoleReadModel(
                id=str(role.id),
                name=role.name,
                description=role.description,
                permissions=permission_map.get(role.id, []),
            )
            for role in roles
        ]

    def assign_role(self, user_id: UUID, role_id: UUID) -> list[RoleReadModel]:
        self._ensure_active_user(user_id)
        RolePermissionRepository(self.db_session)._ensure_role(role_id)
        existing = (
            self.db_session.query(UserRole)
            .filter_by(user_id=user_id, role_id=role_id)
            .one_or_none()
        )
        if existing is not None:
            raise AppError(
                status_code=status.HTTP_409_CONFLICT,
                message=PlatformRoleResponseMessages.ALREADY_ASSIGNED.value,
            )
        self.db_session.add(UserRole(user_id=user_id, role_id=role_id))
        self.db_session.commit()
        return self.get_roles(user_id)

    def remove_role(self, user_id: UUID, role_id: UUID) -> list[RoleReadModel]:
        self._ensure_active_user(user_id)
        link = (
            self.db_session.query(UserRole)
            .filter_by(user_id=user_id, role_id=role_id)
            .one_or_none()
        )
        if link is None:
            raise AppError(
                status_code=status.HTTP_404_NOT_FOUND,
                message=PlatformRoleResponseMessages.ASSIGNMENT_NOT_FOUND.value,
            )
        self.db_session.delete(link)
        self.db_session.commit()
        return self.get_roles(user_id)

    def get_effective_permissions(self, user_id: UUID) -> list[PermissionReadModel]:
        roles = self.get_roles(user_id)
        permissions: dict[tuple[PermissionScope, UUID], PermissionReadModel] = {}
        for role in roles:
            for permission in role.permissions:
                permissions[(permission.scope, permission.id)] = permission
        return sorted(permissions.values(), key=_permission_sort_key)
