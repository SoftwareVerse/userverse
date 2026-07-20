from uuid import UUID

from fastapi import status

from app.models.company.response_messages import (
    CompanyRoleResponseMessages,
    CompanyUserResponseMessages,
)
from app.models.company.roles import (
    RoleCreateModel,
    RoleDeleteModel,
    RoleQueryParamsModel,
    RoleReadModel,
    RoleUpdateModel,
)
from app.models.user.user import UserReadModel
from app.repository.base import BaseSQLRepository
from app.repository.database.tables import Role
from app.utils.app_error import AppError


class RoleRepository(BaseSQLRepository[Role]):
    model = Role

    def __init__(self, company_id: UUID, session):
        super().__init__(session)
        self.company_id = company_id

    @staticmethod
    def _to_read_model(role: Role) -> RoleReadModel:
        data = BaseSQLRepository.serialize(role)
        return RoleReadModel(**data)

    def get_roles(self, payload: RoleQueryParamsModel) -> dict:
        try:
            query = self._base_query().filter(
                Role.company_id == self.company_id,
                Role._closed_at.is_(None),
            )
            if payload.name:
                query = query.filter(Role.name.ilike(f"%{payload.name}%"))
            if payload.description:
                query = query.filter(Role.description.ilike(f"%{payload.description}%"))
            return self.paginate(
                query,
                page=payload.page,
                limit=payload.limit,
                order_by=[Role.name.asc()],
            )
        except Exception as exc:
            raise AppError(
                status_code=status.HTTP_400_BAD_REQUEST,
                message=CompanyRoleResponseMessages.ROLE_NOT_FOUND.value,
                error=str(exc),
            ) from exc

    def get_role_record(self, role_name: str) -> Role | None:
        return (
            self._base_query()
            .filter(
                Role.company_id == self.company_id,
                Role.name == role_name,
                Role._closed_at.is_(None),
            )
            .one_or_none()
        )

    def ensure_role_belongs_to_company(self, role_name: str) -> Role:
        role = self.get_role_record(role_name)
        if not role:
            raise AppError(
                status_code=status.HTTP_400_BAD_REQUEST,
                message=CompanyUserResponseMessages.ADD_USER_FAILED.value,
                error=f"Role: {role_name} is not linked to the company",
            )
        return role

    def delete_role(self, payload: RoleDeleteModel, deleted_by: UserReadModel) -> dict:
        try:
            if payload.role_name_to_delete == payload.replacement_role_name:
                raise ValueError("Cannot replace a role with itself.")

            role_to_delete = self.get_role_record(payload.role_name_to_delete)
            if not role_to_delete:
                raise ValueError(f"Role '{payload.role_name_to_delete}' not found.")

            replacement_role = self.get_role_record(payload.replacement_role_name)
            if not replacement_role:
                raise ValueError(
                    f"Replacement role '{payload.replacement_role_name}' not found."
                )

            reassigned_count = 0
            for user_link in role_to_delete.users:
                user_link.role = replacement_role
                reassigned_count += 1

            role_to_delete._closed_at = self._now_sql()
            self.db_session.add(role_to_delete)
            self.db_session.commit()
            self.update_json_field(
                role_to_delete,
                column_name="primary_meta_data",
                key="deleted_by",
                value=deleted_by.model_dump(mode="json"),
            )

            return {
                "message": (
                    f"Role '{payload.role_name_to_delete}' soft deleted and users reassigned "
                    f"to '{payload.replacement_role_name}'."
                ),
                "users_reassigned": reassigned_count,
            }
        except Exception as exc:
            raise AppError(
                status_code=status.HTTP_400_BAD_REQUEST,
                message=CompanyRoleResponseMessages.ROLE_UPDATE_FAILED.value,
                error=str(exc),
            ) from exc

    def update_role(self, name: str, payload: RoleUpdateModel) -> RoleReadModel:
        try:
            role = self.get_role_record(name)
            if not role:
                raise ValueError(
                    f"Role with company_id={self.company_id} and name='{name}' not found."
                )
            if payload.name:
                role.name = payload.name
            if payload.description is not None:
                role.description = payload.description
            self.db_session.commit()
            self.db_session.refresh(role)
            return self._to_read_model(role)
        except Exception as exc:
            raise AppError(
                status_code=status.HTTP_400_BAD_REQUEST,
                message=CompanyRoleResponseMessages.ROLE_UPDATE_FAILED.value,
                error=str(exc),
            ) from exc

    def create_role(
        self, payload: RoleCreateModel, created_by: UserReadModel
    ) -> RoleReadModel:
        try:
            role = self.create(
                name=payload.name,
                description=payload.description,
                company_id=self.company_id,
            )
            role = self.update_json_field(
                role,
                column_name="primary_meta_data",
                key="created_by",
                value=created_by.model_dump(mode="json"),
            )
            return self._to_read_model(role)
        except Exception as exc:
            raise AppError(
                status_code=status.HTTP_400_BAD_REQUEST,
                message=CompanyRoleResponseMessages.ROLE_CREATION_FAILED.value,
                error=str(exc),
            ) from exc
