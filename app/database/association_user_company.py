from app.models.company.response_messages import CompanyUserResponseMessages
from app.models.user.user import UserReadModel
from app.models.company.roles import CompanyDefaultRoles
from app.utils.app_error import AppError
from sqlalchemy import Column, Integer, String, ForeignKey, ForeignKeyConstraint
from sqlalchemy.orm import relationship, Session
from sqlalchemy.sql import func
from sqlalchemy.orm.attributes import flag_modified
from fastapi import status


from .base_model import BaseModel


class AssociationUserCompany(BaseModel):
    __tablename__ = "association_user_company"

    user_id = Column(Integer, ForeignKey("user.id"), primary_key=True)
    company_id = Column(Integer, ForeignKey("company.id"), primary_key=True)
    role_name = Column(String(256), nullable=False)

    __table_args__ = (
        ForeignKeyConstraint(
            ["company_id", "role_name"],
            ["role.company_id", "role.name"],
            ondelete="CASCADE",
        ),
    )

    # relationships
    role = relationship("Role", back_populates="users", overlaps="company,users")
    company = relationship("Company", back_populates="users", overlaps="role")
    user = relationship("User", back_populates="companies", overlaps="company,role")

    @classmethod
    def is_user_linked_to_company(
        cls, session: Session, user_id: int, company_id: int, role_name: str = None
    ) -> bool:
        """
        Check if a user is associated with a company, optionally filtered by role.
        """
        query = session.query(cls).filter_by(user_id=user_id, company_id=company_id)
        if role_name:
            query = query.filter_by(role_name=role_name)

        return session.query(query.exists()).scalar()

    @classmethod
    def link_user(
        cls,
        session: Session,
        company_id: int,
        user_id: int,
        role_name: str,
        added_by: UserReadModel,
    ) -> "AssociationUserCompany":
        # Prevent duplicate active links
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
            role_name=role_name,
            primary_meta_data={"added_by": added_by.model_dump()},
        )
        session.add(assoc)

        session.commit()
        return assoc

    @classmethod
    def unlink_user(
        cls,
        session: Session,
        company_id: int,
        user_id: int,
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

        # Prevent removing oneself if they are the Administrator (super admin)
        if assoc.user_id == removed_by.id and assoc.role_name == CompanyDefaultRoles.ADMINISTRATOR.name_value:
            raise AppError(
                status_code=status.HTTP_400_BAD_REQUEST,
                message=CompanyUserResponseMessages.SUPER_ADMIN_REMOVE_FORBIDDEN.value,
            )

        assoc.primary_meta_data["removed_by"] = removed_by.model_dump()

        # Force SQLAlchemy to mark the column as dirty
        flag_modified(assoc, "primary_meta_data")

        assoc._closed_at = func.now()
        session.commit()
        return assoc
