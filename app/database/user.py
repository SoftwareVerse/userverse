from sqlalchemy import Column, String, Integer, Boolean
from sqlalchemy.orm import relationship, Session
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

    @classmethod
    def create(cls, session: Session, **kwargs) -> dict:
        """Create a user ensuring password is stored as a secure hash.

        If a "password" is provided and it doesn't look like a bcrypt hash,
        it will be hashed before persisting.
        """
        pwd = kwargs.get("password")
        if isinstance(pwd, str) and pwd and not pwd.startswith("$2"):
            # Lazily import to avoid circulars at module import time
            from app.utils.hash_password import hash_password

            kwargs["password"] = hash_password(pwd)
        return super(User, cls).create(session, **kwargs)
