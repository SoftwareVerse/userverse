from uuid import UUID, uuid4

from sqlalchemy import String, Uuid, select
from sqlalchemy.orm import Session
from sqlalchemy.orm import column_property
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.sql import func

from app.models.company.response_messages import CompanyUserResponseMessages
from app.repository.database.base_model import BaseModel
from app.utils.app_error import AppError
from fastapi import status


class Role(BaseModel):
    __tablename__ = "role"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(256), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(String(256), nullable=True)

    companies = relationship(
        "CompanyRole",
        back_populates="role",
        cascade="all, delete-orphan",
        overlaps="company",
    )
    users = relationship(
        "AssociationUserCompany",
        back_populates="role",
        overlaps="company,companies",
    )

    @staticmethod
    def to_dict(obj):
        data = BaseModel.to_dict(obj)
        company_links = getattr(obj, "companies", None)
        if company_links:
            active_link = next(
                (
                    link
                    for link in company_links
                    if getattr(link, "_closed_at", None) is None
                ),
                None,
            )
            if active_link is not None:
                data["company_id"] = active_link.company_id
        return data

    @classmethod
    def create(cls, session: Session, **kwargs) -> dict:
        company_id = kwargs.pop("company_id", None)
        if company_id is not None:
            existing_role = (
                session.query(cls)
                .filter(cls.name == kwargs["name"], cls._closed_at.is_(None))
                .one_or_none()
            )
            if existing_role is not None:
                existing_assignment = (
                    session.query(CompanyRole)
                    .filter_by(
                        company_id=company_id,
                        role_id=existing_role.id,
                        _closed_at=None,
                    )
                    .one_or_none()
                )
                if existing_assignment is not None:
                    raise ValueError(
                        "Integrity error: role already assigned to company"
                    )
                session.add(
                    CompanyRole(company_id=company_id, role_id=existing_role.id)
                )
                session.commit()
                role_dict = cls.to_dict(existing_role)
                role_dict["company_id"] = company_id
                return role_dict
        role_dict = super().create(session, **kwargs)
        if company_id is not None:
            role = session.query(cls).filter_by(id=role_dict["id"]).one()
            assignment = CompanyRole(company_id=company_id, role_id=role.id)
            session.add(assignment)
            session.commit()
            role_dict["company_id"] = company_id
        return role_dict

    @classmethod
    def role_belongs_to_company(
        cls, session: Session, company_id: UUID, role_name: str
    ) -> dict:
        role = (
            session.query(cls)
            .join(cls.companies)
            .filter(
                cls.name == role_name,
                cls._closed_at.is_(None),
                CompanyRole.company_id == company_id,
                CompanyRole._closed_at.is_(None),
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
    def update_by_filters(cls, session: Session, filters: dict, **kwargs) -> dict:
        company_id = filters.pop("company_id", None)
        if company_id is not None:
            role = (
                session.query(cls)
                .join(cls.companies)
                .filter(
                    CompanyRole.company_id == company_id,
                    cls.name == filters["name"],
                    cls._closed_at.is_(None),
                    CompanyRole._closed_at.is_(None),
                )
                .one()
            )
            for field, value in kwargs.items():
                setattr(role, field, value)
            session.commit()
            session.refresh(role)
            data = cls.to_dict(role)
            data["company_id"] = company_id
            return data
        return super().update_by_filters(session, filters, **kwargs)

    @classmethod
    def delete_by_filters(cls, session: Session, filters: dict) -> dict[str, str]:
        company_id = filters.pop("company_id", None)
        if company_id is not None:
            assignment = (
                session.query(CompanyRole)
                .join(CompanyRole.role)
                .filter(
                    CompanyRole.company_id == company_id,
                    Role.name == filters["name"],
                    CompanyRole._closed_at.is_(None),
                )
                .one()
            )
            assignment._closed_at = func.now()
            session.add(assignment)
            session.commit()
            return {"message": f"{cls.__name__} with filters deleted"}
        return super().delete_by_filters(session, filters)

    @classmethod
    def update_role(
        cls,
        session: Session,
        company_id: UUID,
        name: str,
        new_name: str | None = None,
        new_description: str | None = None,
    ) -> dict:
        try:
            role = (
                session.query(cls)
                .join(cls.companies)
                .filter(
                    CompanyRole.company_id == company_id,
                    cls.name == name,
                    cls._closed_at.is_(None),
                    CompanyRole._closed_at.is_(None),
                )
                .one()
            )
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
        company_id: UUID,
        name: str,
        column_name: str,
        key: str,
        value,
    ):
        role = (
            session.query(cls)
            .join(cls.companies)
            .filter(
                CompanyRole.company_id == company_id,
                cls.name == name,
                cls._closed_at.is_(None),
                CompanyRole._closed_at.is_(None),
            )
            .one_or_none()
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
        session.refresh(role)
        return role

    @classmethod
    def delete_role_and_reassign_users(
        cls,
        session: Session,
        company_id: UUID,
        name_to_delete: str,
        replacement_name: str,
        deleted_by,
    ):
        if name_to_delete == replacement_name:
            raise ValueError("Cannot replace a role with itself.")

        role_to_delete = (
            session.query(cls)
            .join(cls.companies)
            .filter(
                CompanyRole.company_id == company_id,
                cls.name == name_to_delete,
                cls._closed_at.is_(None),
                CompanyRole._closed_at.is_(None),
            )
            .one_or_none()
        )
        if not role_to_delete:
            raise ValueError(f"Role '{name_to_delete}' not found.")

        replacement_role = (
            session.query(cls)
            .join(cls.companies)
            .filter(
                CompanyRole.company_id == company_id,
                cls.name == replacement_name,
                cls._closed_at.is_(None),
                CompanyRole._closed_at.is_(None),
            )
            .one_or_none()
        )
        if not replacement_role:
            raise ValueError(f"Replacement role '{replacement_name}' not found.")

        reassigned_count = 0
        for user_link in (
            session.query(AssociationUserCompany)
            .filter_by(
                company_id=company_id, role_id=role_to_delete.id, _closed_at=None
            )
            .all()
        ):
            user_link.role_id = replacement_role.id
            user_link.secondary_meta_data = user_link.secondary_meta_data or {}
            user_link.secondary_meta_data["_legacy_role_name"] = replacement_role.name
            reassigned_count += 1

        assignment = (
            session.query(CompanyRole)
            .filter_by(
                company_id=company_id, role_id=role_to_delete.id, _closed_at=None
            )
            .one()
        )
        role_to_delete.primary_meta_data = role_to_delete.primary_meta_data or {}
        role_to_delete.primary_meta_data["deleted_by"] = deleted_by.model_dump(
            mode="json"
        )
        role_to_delete._closed_at = func.now()
        assignment._closed_at = func.now()
        session.add(role_to_delete)
        session.add(assignment)
        session.commit()
        session.refresh(role_to_delete)
        return {
            "message": (
                f"Role '{name_to_delete}' soft deleted and users reassigned to "
                f"'{replacement_name}'."
            ),
            "users_reassigned": reassigned_count,
        }


from app.repository.database.tables.company_role import CompanyRole
from app.repository.database.tables.association_user_company import (
    AssociationUserCompany,
)

Role.company_id = column_property(
    select(CompanyRole.company_id)
    .where(CompanyRole.role_id == Role.id)
    .correlate_except(CompanyRole)
    .order_by(CompanyRole._created_at.desc())
    .limit(1)
    .scalar_subquery()
)
