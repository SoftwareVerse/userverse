from sqlalchemy import Column, String, Integer, Boolean
from sqlalchemy.orm import relationship, backref, Session
from sqlalchemy.exc import NoResultFound
from .base_model import BaseModel


class User(BaseModel):
    __tablename__ = "user"

    id = Column(Integer, nullable=False, primary_key=True, autoincrement=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    email = Column(String(255), nullable=False, unique=True)
    phone_number = Column(String(255), nullable=True)
    password = Column(String(255), nullable=False)
    is_superuser = Column(Boolean, nullable=False, default=False)

    # All the companies agent is linked with
    companies = relationship("AssociationUserCompany", back_populates="user")

    @classmethod
    def get_user_by_email(cls, session: Session, email: str) -> dict:
        try:
            agent = session.query(cls).filter_by(email=email).one()
            return cls.to_dict(agent)
        except NoResultFound:
            raise ValueError(f"User with email:{email}, not found.")
