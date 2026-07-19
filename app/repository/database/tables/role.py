from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.sql import func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.company.response_messages import CompanyUserResponseMessages
from app.models.user.user import UserReadModel
from app.repository.database.base_model import BaseModel
from app.utils.app_error import AppError
from fastapi import status


class Role(BaseModel):
    __tablename__ = "role"

    company_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("company.id", ondelete="CASCADE"),
        primary_key=True,
    )
    name: Mapped[str] = mapped_column(String(256), primary_key=True)
    description: Mapped[str | None] = mapped_column(String(256), nullable=True)

    company = relationship("Company", back_populates="roles", overlaps="users")
    users = relationship(
        "AssociationUserCompany",
        back_populates="role",
        overlaps="company,users",
    )

    @classmethod
    def role_belongs_to_company(cls, session: Session, company_id: int, role_name: str) -> dict:
        role = (
            session.query(cls)
            .filter_by(company_id=company_id, name=role_name, _closed_at=None)
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
        session: Session,
        company_id: int,
        name: str,
        new_name: str | None = None,
        new_description: str | None = None,
    ) -> dict:
        try:
            role = session.query(cls).filter_by(company_id=company_id, name=name).one()
            if new_name:
                role.name = new_name
            if new_description:
                role.description = new_description
            session.commit()
            session.refresh(role)
            return cls.to_dict(role)
        except NoResultFound as exc:
            raise ValueError(
                f"Role with company_id={company_id} and name='{name}' not found."
            ) from exc

    @classmethod
    def update_json_field(
        cls,
        session: Session,
        company_id: int,
        name: str,
        column_name: str,
        key: str,
        value,
    ):
        role = session.query(cls).filter_by(company_id=company_id, name=name).one_or_none()
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
        session.refresh(role)
        return role

    @classmethod
    def delete_role_and_reassign_users(
        cls,
        session: Session,
        company_id: int,
        name_to_delete: str,
        replacement_name: str,
        deleted_by: UserReadModel,
    ):
        if name_to_delete == replacement_name:
            raise ValueError("Cannot replace a role with itself.")

        role_to_delete = (
            session.query(cls).filter_by(company_id=company_id, name=name_to_delete).one_or_none()
        )
        if not role_to_delete:
            raise ValueError(f"Role '{name_to_delete}' not found.")

        replacement_role = (
            session.query(cls).filter_by(company_id=company_id, name=replacement_name).one_or_none()
        )
        if not replacement_role:
            raise ValueError(f"Replacement role '{replacement_name}' not found.")

        reassigned_count = 0
        for user_link in role_to_delete.users:
            user_link.role = replacement_role
            reassigned_count += 1

        role_to_delete._closed_at = func.now()
        session.add(role_to_delete)
        session.commit()
        cls.update_json_field(
            session=session,
            company_id=company_id,
            name=name_to_delete,
            column_name="primary_meta_data",
            key="deleted_by",
            value=deleted_by.model_dump(),
        )
        session.refresh(role_to_delete)
        return {
            "message": (
                f"Role '{name_to_delete}' soft deleted and users reassigned to "
                f"'{replacement_name}'."
            ),
            "users_reassigned": reassigned_count,
        }
