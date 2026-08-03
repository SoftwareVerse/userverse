from uuid import UUID

from fastapi import status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.company.response_messages import (
    CompanyRoleResponseMessages,
    CompanyUserResponseMessages,
)
from app.models.company.roles import (
    RoleAssignCompaniesModel,
    RoleCreateModel,
    RoleDeleteModel,
    RoleQueryParamsModel,
    RoleReadModel,
    RoleUpdateModel,
)
from app.models.user.user import UserReadModel
from app.repository.base import BaseSQLRepository
from app.repository.database.tables import AssociationUserCompany, CompanyRole, Role
from app.utils.app_error import AppError


class RoleRepository(BaseSQLRepository[Role]):
    model = Role

    @staticmethod
    def _to_read_model(role: Role) -> RoleReadModel:
        data = BaseSQLRepository.serialize(role)
        data["id"] = str(role.id)
        return RoleReadModel(**data)

    def get_roles(self, payload: RoleQueryParamsModel) -> dict:
        try:
            query = self._base_query().filter(Role._closed_at.is_(None))
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

    def get_role_record(self, role_id: UUID) -> Role | None:
        return (
            self._base_query()
            .filter(Role.id == role_id, Role._closed_at.is_(None))
            .one_or_none()
        )

    def get_role_by_name(self, role_name: str) -> Role | None:
        return (
            self._base_query()
            .filter(Role.name == role_name, Role._closed_at.is_(None))
            .one_or_none()
        )

    def ensure_role_exists(self, role_id: UUID) -> Role:
        role = self.get_role_record(role_id)
        if not role:
            raise AppError(
                status_code=status.HTTP_404_NOT_FOUND,
                message=CompanyRoleResponseMessages.ROLE_NOT_FOUND.value,
            )
        return role

    def ensure_role_by_name(self, role_name: str) -> Role:
        role = self.get_role_by_name(role_name)
        if not role:
            raise AppError(
                status_code=status.HTTP_400_BAD_REQUEST,
                message=CompanyUserResponseMessages.ADD_USER_FAILED.value,
                error=f"Role: {role_name} is not linked to the company",
            )
        return role

    def create_role(
        self, payload: RoleCreateModel, created_by: UserReadModel
    ) -> RoleReadModel:
        try:
            role = self.create(
                name=payload.name,
                description=payload.description,
            )
            role = self.update_json_field(
                role,
                column_name="primary_meta_data",
                key="created_by",
                value=created_by.model_dump(mode="json"),
            )
            return self._to_read_model(role)
        except IntegrityError as exc:
            self.db_session.rollback()
            raise AppError(
                status_code=status.HTTP_409_CONFLICT,
                message=CompanyRoleResponseMessages.ROLE_ALREADY_EXISTS.value,
                error=str(exc),
            ) from exc
        except Exception as exc:
            raise AppError(
                status_code=status.HTTP_400_BAD_REQUEST,
                message=CompanyRoleResponseMessages.ROLE_CREATION_FAILED.value,
                error=str(exc),
            ) from exc

    def update_role(self, role_id: UUID, payload: RoleUpdateModel) -> RoleReadModel:
        try:
            role = self.get_role_record(role_id)
            if not role:
                raise ValueError(f"Role with id='{role_id}' not found.")
            if payload.name:
                role.name = payload.name
            if payload.description is not None:
                role.description = payload.description
            self.db_session.commit()
            self.db_session.refresh(role)
            return self._to_read_model(role)
        except Exception as exc:
            self.db_session.rollback()
            raise AppError(
                status_code=status.HTTP_400_BAD_REQUEST,
                message=CompanyRoleResponseMessages.ROLE_UPDATE_FAILED.value,
                error=str(exc),
            ) from exc

    def delete_role(self, role_id: UUID, deleted_by: UserReadModel) -> dict:
        try:
            role = self.get_role_record(role_id)
            if not role:
                raise ValueError(f"Role with id='{role_id}' not found.")
            if (
                self.db_session.query(AssociationUserCompany)
                .filter(
                    AssociationUserCompany.role_id == role_id,
                    AssociationUserCompany._closed_at.is_(None),
                )
                .count()
            ):
                raise ValueError(
                    "Cannot delete a role that is still assigned to active company users."
                )

            role._closed_at = self._now_sql()
            self.db_session.add(role)
            self.db_session.commit()
            self.update_json_field(
                role,
                column_name="primary_meta_data",
                key="deleted_by",
                value=deleted_by.model_dump(mode="json"),
            )
            return {"message": f"Role '{role.name}' deleted successfully."}
        except Exception as exc:
            self.db_session.rollback()
            raise AppError(
                status_code=status.HTTP_400_BAD_REQUEST,
                message=CompanyRoleResponseMessages.ROLE_DELETION_FAILED.value,
                error=str(exc),
            ) from exc


class CompanyRoleAssignmentRepository(BaseSQLRepository[CompanyRole]):
    model = CompanyRole

    def __init__(self, company_id: UUID, session: Session):
        super().__init__(session)
        self.company_id = company_id

    def get_company_roles(self, payload: RoleQueryParamsModel) -> dict:
        try:
            query = (
                self.db_session.query(Role)
                .join(CompanyRole, CompanyRole.role_id == Role.id)
                .filter(
                    CompanyRole.company_id == self.company_id,
                    CompanyRole._closed_at.is_(None),
                    Role._closed_at.is_(None),
                )
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
            records = []
            for role in result["records"]:
                role["id"] = str(role["id"])
                records.append(role)
            result["records"] = records
            return result
        except Exception as exc:
            raise AppError(
                status_code=status.HTTP_400_BAD_REQUEST,
                message=CompanyRoleResponseMessages.ROLE_NOT_FOUND.value,
                error=str(exc),
            ) from exc

    def get_assignment(self, role_id: UUID) -> CompanyRole | None:
        return (
            self._base_query()
            .filter(
                CompanyRole.company_id == self.company_id,
                CompanyRole.role_id == role_id,
                CompanyRole._closed_at.is_(None),
            )
            .one_or_none()
        )

    def ensure_role_assigned(self, role_id: UUID) -> CompanyRole:
        assignment = self.get_assignment(role_id)
        if not assignment:
            raise AppError(
                status_code=status.HTTP_400_BAD_REQUEST,
                message=CompanyUserResponseMessages.ADD_USER_FAILED.value,
                error="Role is not linked to the company",
            )
        return assignment

    def ensure_role_name_assigned(self, role_name: str) -> Role:
        role = (
            self.db_session.query(Role)
            .join(CompanyRole, CompanyRole.role_id == Role.id)
            .filter(
                CompanyRole.company_id == self.company_id,
                CompanyRole._closed_at.is_(None),
                Role.name == role_name,
                Role._closed_at.is_(None),
            )
            .one_or_none()
        )
        if not role:
            raise AppError(
                status_code=status.HTTP_400_BAD_REQUEST,
                message=CompanyUserResponseMessages.ADD_USER_FAILED.value,
                error=f"Role: {role_name} is not linked to the company",
            )
        return role

    def get_role_name_assigned(self, role_name: str) -> Role | None:
        return (
            self.db_session.query(Role)
            .join(CompanyRole, CompanyRole.role_id == Role.id)
            .filter(
                CompanyRole.company_id == self.company_id,
                CompanyRole._closed_at.is_(None),
                Role.name == role_name,
                Role._closed_at.is_(None),
            )
            .one_or_none()
        )

    def update_company_role(self, name: str, payload: RoleUpdateModel) -> RoleReadModel:
        try:
            role = self.get_role_name_assigned(name)
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
            return RoleRepository._to_read_model(role)
        except Exception as exc:
            self.db_session.rollback()
            raise AppError(
                status_code=status.HTTP_400_BAD_REQUEST,
                message=CompanyRoleResponseMessages.ROLE_UPDATE_FAILED.value,
                error=str(exc),
            ) from exc

    def assign_role(self, role: Role, assigned_by: UserReadModel) -> RoleReadModel:
        existing = self.get_assignment(role.id)
        if existing:
            raise AppError(
                status_code=status.HTTP_400_BAD_REQUEST,
                message=CompanyRoleResponseMessages.ROLE_CREATION_FAILED.value,
                error="Role is already assigned to the company",
            )

        assignment = self.create(company_id=self.company_id, role_id=role.id)
        self.update_json_field(
            assignment,
            column_name="primary_meta_data",
            key="assigned_by",
            value=assigned_by.model_dump(mode="json"),
        )
        return RoleRepository._to_read_model(role)

    def assign_role_to_companies(
        self,
        role: Role,
        payload: RoleAssignCompaniesModel,
        assigned_by: UserReadModel,
    ) -> dict:
        assigned_companies: list[str] = []
        for company_id in payload.company_ids:
            company_uuid = UUID(company_id)
            repository = CompanyRoleAssignmentRepository(company_uuid, self.db_session)
            if repository.get_assignment(role.id):
                continue
            assignment = repository.create(company_id=company_uuid, role_id=role.id)
            repository.update_json_field(
                assignment,
                column_name="primary_meta_data",
                key="assigned_by",
                value=assigned_by.model_dump(mode="json"),
            )
            assigned_companies.append(company_id)
        return {"role_id": str(role.id), "company_ids": assigned_companies}

    def unassign_role(self, role_id: UUID) -> dict:
        assignment = self.get_assignment(role_id)
        if not assignment:
            raise AppError(
                status_code=status.HTTP_404_NOT_FOUND,
                message=CompanyRoleResponseMessages.ROLE_NOT_FOUND.value,
                error="Role assignment not found.",
            )
        if (
            self.db_session.query(AssociationUserCompany)
            .filter(
                AssociationUserCompany.company_id == self.company_id,
                AssociationUserCompany.role_id == role_id,
                AssociationUserCompany._closed_at.is_(None),
            )
            .count()
        ):
            raise AppError(
                status_code=status.HTTP_400_BAD_REQUEST,
                message=CompanyRoleResponseMessages.ROLE_DELETION_FAILED.value,
                error="Cannot unassign a role that is still assigned to active company users.",
            )
        assignment._closed_at = self._now_sql()
        self.db_session.add(assignment)
        self.db_session.commit()
        return {"message": "Role unassigned successfully."}

    def reassign_and_delete_role(
        self, payload: RoleDeleteModel, deleted_by: UserReadModel
    ) -> dict:
        if payload.role_name_to_delete == payload.replacement_role_name:
            raise AppError(
                status_code=status.HTTP_400_BAD_REQUEST,
                message=CompanyRoleResponseMessages.ROLE_UPDATE_FAILED.value,
                error="Cannot replace a role with itself.",
            )

        role_to_delete = self.get_role_name_assigned(payload.role_name_to_delete)
        if not role_to_delete:
            raise AppError(
                status_code=status.HTTP_400_BAD_REQUEST,
                message=CompanyRoleResponseMessages.ROLE_UPDATE_FAILED.value,
                error=f"Role '{payload.role_name_to_delete}' not found.",
            )
        replacement_role = self.get_role_name_assigned(payload.replacement_role_name)
        if not replacement_role:
            raise AppError(
                status_code=status.HTTP_400_BAD_REQUEST,
                message=CompanyRoleResponseMessages.ROLE_UPDATE_FAILED.value,
                error=f"Replacement role '{payload.replacement_role_name}' not found.",
            )

        reassigned_count = 0
        active_links = (
            self.db_session.query(AssociationUserCompany)
            .filter(
                AssociationUserCompany.company_id == self.company_id,
                AssociationUserCompany.role_id == role_to_delete.id,
                AssociationUserCompany._closed_at.is_(None),
            )
            .all()
        )
        for user_link in active_links:
            user_link.role_id = replacement_role.id
            reassigned_count += 1

        assignment = self.get_assignment(role_to_delete.id)
        if not assignment:
            raise AppError(
                status_code=status.HTTP_400_BAD_REQUEST,
                message=CompanyRoleResponseMessages.ROLE_UPDATE_FAILED.value,
                error=f"Role '{payload.role_name_to_delete}' not found.",
            )
        assignment._closed_at = self._now_sql()
        self.db_session.add(assignment)
        self.db_session.commit()
        self.update_json_field(
            assignment,
            column_name="primary_meta_data",
            key="deleted_by",
            value=deleted_by.model_dump(mode="json"),
        )

        return {
            "message": (
                f"Role '{payload.role_name_to_delete}' unassigned and users reassigned "
                f"to '{payload.replacement_role_name}'."
            ),
            "users_reassigned": reassigned_count,
        }
