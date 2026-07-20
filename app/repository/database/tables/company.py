from uuid import UUID, uuid4

from sqlalchemy import String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.repository.database.base_model import BaseModel


class Company(BaseModel):
    __tablename__ = "company"

    id: Mapped[UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid4,
    )
    name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    description: Mapped[str | None] = mapped_column(String(512), nullable=True)
    industry: Mapped[str | None] = mapped_column(String(128), nullable=True)
    email: Mapped[str] = mapped_column(String(256), nullable=False, unique=True)
    phone_number: Mapped[str | None] = mapped_column(String(16), nullable=True)

    users = relationship(
        "AssociationUserCompany",
        back_populates="company",
        overlaps="role,user",
    )
    roles = relationship(
        "Role",
        back_populates="company",
        cascade="all, delete-orphan",
    )

    @classmethod
    def get_company_by_email(cls, session, email: str) -> dict:
        company = session.query(cls).filter_by(email=email).one_or_none()
        if company is None:
            raise ValueError(f"Company with email:{email}, not found.")
        return cls.to_dict(company)
