from sqlalchemy import Column, String, Integer
from sqlalchemy.orm import relationship, Session
from sqlalchemy.exc import NoResultFound
from .base_model import BaseModel


class Company(BaseModel):
    __tablename__ = "company"

    id = Column(Integer, nullable=False, primary_key=True, autoincrement=True)
    name = Column(String(256), nullable=True)
    description = Column(String(512), nullable=True)
    industry = Column(String(128), nullable=True)
    email = Column(String(256), nullable=False, unique=True)
    phone_number = Column(String(16), nullable=True)
    # relationship with users
    users = relationship(
        "AssociationUserCompany", back_populates="company", overlaps="role,user"
    )
    # relationship with roles
    roles = relationship("Role", back_populates="company", cascade="all, delete-orphan")

    @classmethod
    def get_company_by_email(cls, session: Session, email: str) -> dict:
        try:
            company = session.query(cls).filter_by(email=email).one()
            return cls.to_dict(company)
        except NoResultFound:
            raise ValueError(f"Company with email:{email}, not found.")
