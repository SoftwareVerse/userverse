from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.repository.database.base_model import BaseModel


class Company(BaseModel):
    __tablename__ = "company"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
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
