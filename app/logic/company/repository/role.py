from fastapi import status

# utils
from app.utils.app_error import AppError

# database
from app.database.session_manager import DatabaseSessionManager
from app.database.company import Company
from app.database.role import Role
from app.database.association_user_company import AssociationUserCompany

# models
from app.models.company.roles import (
    RoleCreate,
    RoleQueryParams,
    RoleRead,
    RoleUpdate,
    RoleDelete,
)
from app.models.user.user import UserRead
from app.models.company.response_messages import (
    CompanyResponseMessages,
    CompanyRoleResponseMessages,
)


class RoleRepository:

    def __init__(self, company_id: int):
        self.company_id = company_id
        self.db_manager = DatabaseSessionManager()

    def get_roles(
        self,
        payload: RoleQueryParams,
    ) -> dict:
        """
        Get paginated roles for the company with optional filtering.
        Excludes soft-deleted roles (_closed_at is not null).
        """
        with self.db_manager.session_object() as session:
            try:
                filters = {
                    "company_id": Role.company_id == self.company_id,
                    "_closed_at": Role._closed_at.is_(None),
                }
                if payload.name:
                    filters["name"] = Role.name.ilike(f"%{payload.name}%")
                if payload.description:
                    filters["description"] = Role.description.ilike(
                        f"%{payload.description}%"
                    )

                return Role.get_all(
                    session=session,
                    filters=filters,
                    limit=payload.limit,
                    offset=payload.offset,
                )
            except Exception as e:
                raise AppError(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    message=CompanyRoleResponseMessages.ROLE_NOT_FOUND.value,
                    error=str(e),
                )

    def delete_role(self, payload: RoleDelete, deleted_by: UserRead) -> dict:
        """
        Delete role from a company
        """
        with self.db_manager.session_object() as session:
            try:
                updated = Role.delete_role_and_reassign_users(
                    session=session,
                    company_id=self.company_id,
                    name_to_delete=payload.role_name_to_delete,
                    replacement_name=payload.replacement_role_name,
                    deleted_by=deleted_by,
                )
                return updated
            except Exception as e:
                raise AppError(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    message=CompanyRoleResponseMessages.ROLE_UPDATE_FAILED.value,
                    error=str(e),
                )

    def update_role(self, name: str, payload: RoleUpdate) -> RoleRead:
        """
        Update the description of a role for this company.
        """
        with self.db_manager.session_object() as session:
            try:
                updated = Role.update_role(
                    session,
                    company_id=self.company_id,
                    name=name,
                    new_description=payload.description,
                    new_name=payload.name,
                )
                return RoleRead(**updated)
            except Exception as e:
                raise AppError(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    message=CompanyRoleResponseMessages.ROLE_UPDATE_FAILED.value,
                    error=str(e),
                )

    def create_role(
        self,
        payload: RoleCreate,
        created_by: UserRead,
    ) -> RoleRead:
        """
        Create a new role for a company.

        Args:
            payload: The role data to be created
            created_by: The user who is creating the role
            company_id: The ID of the company

        Returns:
            RoleRead: The created role data

        Raises:
            AppError: If role creation fails
        """
        with self.db_manager.session_object() as session:
            # 1. Create the role
            role = self._create_role_record(session, payload, created_by)

            # 2. Get the registered role with complete data
            registered_role = self._get_registered_role(session, role["name"])

            return RoleRead(**registered_role)

    def _create_role_record(
        self, session, payload: RoleCreate, created_by: UserRead
    ) -> dict:
        """
        Create a new role record in the database.

        Args:
            session: The database session
            payload: The role data to be created
            created_by: The user who is creating the role
            company_id: The ID of the company

        Returns:
            dict: The created role data
        """
        try:
            new_role = Role(
                name=payload.name,
                description=payload.description,
                company_id=self.company_id,
            )
            session.add(new_role)
            session.commit()
            new_role.update_json_field(
                session=session,
                company_id=new_role.company_id,
                name=new_role.name,
                column_name="primary_meta_data",
                key="created_by",
                value=created_by.model_dump(),
            )
            session.refresh(new_role)
            return new_role.to_dict(new_role)
        except Exception as e:
            raise AppError(
                status_code=status.HTTP_400_BAD_REQUEST,
                message=CompanyRoleResponseMessages.ROLE_CREATION_FAILED.value,
                error=str(e),
            ) from e

    def _get_registered_role(self, session, role_name: str) -> dict:
        """
        Get the registered role with complete data.

        Args:
            session: The database session
            role_id: The ID of the role

        Returns:
            dict: The registered role data
        """
        try:

            role = session.query(Role).filter(Role.name == role_name).first()
            if not role:
                raise AppError(
                    status_code=status.HTTP_404_NOT_FOUND,
                    message=CompanyRoleResponseMessages.ROLE_NOT_FOUND.value,
                )
            return role.to_dict(role)
        except Exception as e:
            raise AppError(
                status_code=status.HTTP_400_BAD_REQUEST,
                message=str(e),
            ) from e
