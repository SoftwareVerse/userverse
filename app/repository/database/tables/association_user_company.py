from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, Uuid
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.company.response_messages import CompanyUserResponseMessages
from app.models.company.roles import CompanyDefaultRoles
from app.models.user.user import UserReadModel
from app.repository.database.base_model import BaseModel
from app.utils.app_error import AppError
from fastapi import status
from sqlalchemy.sql import func


class AssociationUserCompany(BaseModel):
    __tablename__ = "association_user_company"

    user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("user.id"),
        primary_key=True,
    )
    company_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("company.id"),
        primary_key=True,
    )
    role_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("role.id", ondelete="CASCADE"),
        nullable=False,
    )

    role = relationship("Role", back_populates="users", overlaps="company,users")
    company = relationship("Company", back_populates="users", overlaps="role")
    user = relationship("User", back_populates="companies", overlaps="company,role")

    @property
    def role_name(self) -> str | None:
        if "role" in self.__dict__ and self.__dict__["role"] is not None:
            return self.__dict__["role"].name
        return (self.secondary_meta_data or {}).get("_legacy_role_name")

    @role_name.setter
    def role_name(self, value: str) -> None:
        self.secondary_meta_data = self.secondary_meta_data or {}
        self.secondary_meta_data["_legacy_role_name"] = value
        if getattr(self, "role_id", None) is None:
            self.role_id = uuid4()

    @staticmethod
    def to_dict(obj):
        data = BaseModel.to_dict(obj)
        data["role_name"] = obj.role_name
        return data

    @classmethod
    def create(cls, session: Session, **kwargs) -> dict:
        role_name = kwargs.pop("role_name", None)
        if role_name is not None and "role_id" not in kwargs:
            role = Role.role_belongs_to_company(
                session, kwargs["company_id"], role_name
            )
            kwargs["role_id"] = role["id"]
        if role_name is not None:
            secondary_meta_data = kwargs.get("secondary_meta_data") or {}
            secondary_meta_data["_legacy_role_name"] = role_name
            kwargs["secondary_meta_data"] = secondary_meta_data
        return super().create(session, **kwargs)

    @classmethod
    def delete_by_filters(cls, session: Session, filters: dict) -> dict[str, str]:
        role_name = filters.pop("role_name", None)
        if role_name is not None:
            role = Role.role_belongs_to_company(
                session, filters["company_id"], role_name
            )
            filters["role_id"] = role["id"]
        return super().delete_by_filters(session, filters)

    @classmethod
    def is_user_linked_to_company(
        cls,
        session: Session,
        user_id: UUID,
        company_id: UUID,
        role_name: str | None = None,
    ) -> bool:
        query = session.query(cls).filter_by(user_id=user_id, company_id=company_id)
        if role_name:
            query = query.join(cls.role).filter(Role.name == role_name)
        return session.query(query.exists()).scalar()

    @classmethod
    def link_user(
        cls,
        session: Session,
        company_id: UUID,
        user_id: UUID,
        role_id: UUID | str,
        added_by: UserReadModel,
    ) -> "AssociationUserCompany":
        if isinstance(role_id, str):
            role = Role.role_belongs_to_company(session, company_id, role_id)
            role_id = role["id"]
        existing = (
            session.query(cls)
            .filter_by(user_id=user_id, company_id=company_id, _closed_at=None)
            .first()
        )
        if existing:
            raise ValueError(CompanyUserResponseMessages.ADD_EXISTING_USER_FAILED.value)

        assoc = cls(
            user_id=user_id,
            company_id=company_id,
            role_id=role_id,
            primary_meta_data={"added_by": added_by.model_dump(mode="json")},
        )
        session.add(assoc)
        session.commit()
        session.refresh(assoc)
        return assoc

    @classmethod
    def unlink_user(
        cls,
        session: Session,
        company_id: UUID,
        user_id: UUID,
        removed_by: UserReadModel,
    ) -> "AssociationUserCompany":
        assoc = (
            session.query(cls)
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
        assoc._closed_at = func.now()
        session.commit()
        session.refresh(assoc)
        return assoc


from app.repository.database.tables.role import Role
