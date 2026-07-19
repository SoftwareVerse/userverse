from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.repository.database.base_model import BaseModel


class User(BaseModel):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    first_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    phone_number: Mapped[str | None] = mapped_column(String(255), nullable=True)
    password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    companies = relationship("AssociationUserCompany", back_populates="user")

    @classmethod
    def get_user_by_email(cls, session: Session, email: str) -> dict:
        try:
            user = session.query(cls).filter_by(email=email).one()
            return cls.to_dict(user)
        except NoResultFound as exc:
            raise ValueError(f"User with email:{email}, not found.") from exc
