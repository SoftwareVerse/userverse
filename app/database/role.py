from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.orm.exc import NoResultFound
from fastapi import status

from app.models.company.response_messages import (
    CompanyResponseMessages,
    CompanyUserResponseMessages,
)
from app.models.user.user import UserReadModel
from app.utils.app_error import AppError
from .base_model import BaseModel


class Role(BaseModel):
    __tablename__ = "role"

    company_id = Column(
        Integer, ForeignKey("company.id", ondelete="CASCADE"), primary_key=True
    )
    name = Column(String(256), primary_key=True)
    description = Column(String(256), nullable=True)

    company = relationship("Company", back_populates="roles", overlaps="users")
    users = relationship(
        "AssociationUserCompany", back_populates="role", overlaps="company,users"
    )

    @classmethod
    def role_belongs_to_company(cls, session, company_id: int, role_name: str) -> bool:
        """
        Check if a role belongs to a specific company.

        Args:
            session: SQLAlchemy session.
            company_id: ID of the company to check.
            role_name: Name of the role to check.

        Returns:
            bool: True if the role belongs to the company, False otherwise.
        """
        role = (
            session.query(cls)
            .filter_by(
                company_id=company_id,
                name=role_name,
                _closed_at=None,  # Only consider active roles
            )
            .one_or_none()
        )

        if role:
            return cls.to_dict(role)

        raise AppError(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=CompanyUserResponseMessages.ADD_USER_FAILED.value,
            error=f"Role: {role_name} is not linked to the company",
        )

    @classmethod
    def update_role(
        cls,
        session,
        company_id: int,
        name: str,
        new_name: str = None,
        new_description: str = None,
    ) -> dict:
        """
        Update a role's name and/or description using the composite key (company_id, name).
        """
        try:
            role = session.query(cls).filter_by(company_id=company_id, name=name).one()

            if new_name:
                role.name = new_name
            if new_description:
                role.description = new_description

            session.commit()
            return cls.to_dict(role)

        except NoResultFound:
            raise ValueError(
                f"Role with company_id={company_id} and name='{name}' not found."
            )

    @classmethod
    def update_json_field(
        cls,
        session,
        company_id: int,
        name: str,
        column_name: str,
        key: str,
        value: any,
    ):
        """
        Update a key in a JSON field using (company_id, name) as composite key.
        """
        role = (
            session.query(cls).filter_by(company_id=company_id, name=name).one_or_none()
        )
        if not role:
            raise ValueError(
                f"Role with company_id={company_id} and name='{name}' not found."
            )

        if not hasattr(role, column_name):
            raise ValueError(f"Column '{column_name}' does not exist on Role.")

        json_column = getattr(role, column_name)
        if not isinstance(json_column, dict):
            raise ValueError(f"Column '{column_name}' is not a JSON field.")

        json_column[key] = value
        setattr(role, column_name, json_column)

        session.commit()
        return role

    @classmethod
    def delete_role_and_reassign_users(
        cls,
        session,
        company_id: int,
        name_to_delete: str,
        replacement_name: str,
        deleted_by: UserReadModel,
    ):
        """
        Delete a role and reassign its users to a replacement role.

        Args:
            session: SQLAlchemy session.
            company_id: ID of the company.
            name_to_delete: Role name to delete.
            replacement_name: Role name to assign to affected users.

        Returns:
            dict: A success message and counts of affected users.
        Raises:
            ValueError: If roles are not found or reassignment is invalid.
        """
        if name_to_delete == replacement_name:
            raise ValueError("Cannot replace a role with itself.")

        role_to_delete = (
            session.query(cls)
            .filter_by(company_id=company_id, name=name_to_delete)
            .one_or_none()
        )

        if not role_to_delete:
            raise ValueError(f"Role '{name_to_delete}' not found.")

        replacement_role = (
            session.query(cls)
            .filter_by(company_id=company_id, name=replacement_name)
            .one_or_none()
        )

        if not replacement_role:
            raise ValueError(f"Replacement role '{replacement_name}' not found.")

        # Reassign users to the replacement role
        reassigned_count = 0
        for user_link in role_to_delete.users:
            user_link.role = replacement_role
            reassigned_count += 1

        # Delete the original role
        # Soft delete the role
        role_to_delete._closed_at = func.now()
        session.add(role_to_delete)
        session.commit()
        role_to_delete.update_json_field(
            session=session,
            company_id=company_id,
            name=name_to_delete,
            column_name="primary_meta_data",
            key="deleted_by",
            value=deleted_by.model_dump(),
        )
        session.refresh(role_to_delete)

        return {
            "message": f"Role '{name_to_delete}' soft deleted and users reassigned to '{replacement_name}'.",
            "users_reassigned": reassigned_count,
        }
