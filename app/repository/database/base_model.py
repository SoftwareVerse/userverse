from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, JSON, MetaData, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column
from sqlalchemy.orm.exc import NoResultFound

from app.models.generic_pagination import apply_pagination, build_pagination_meta
from app.utils.date_converter import convert_datetime


class RecordNotFoundError(Exception):
    def __init__(self, model_name: str, identifier: Any):
        super().__init__(f"No {model_name} found with id={identifier}")


class Base(DeclarativeBase):
    metadata = MetaData()


class TimestampMixin:
    _created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
    )
    _updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        onupdate=func.now(),
        default=lambda: datetime.now(timezone.utc),
    )
    _closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    primary_meta_data: Mapped[dict[str, Any]] = mapped_column(
        MutableDict.as_mutable(JSON),
        default=dict,
    )
    secondary_meta_data: Mapped[dict[str, Any]] = mapped_column(
        MutableDict.as_mutable(JSON),
        default=dict,
    )


class BaseModel(TimestampMixin, Base):
    __abstract__ = True

    @staticmethod
    def to_dict(obj: Any) -> Any:
        return to_dict(obj)

    @classmethod
    def get_all(
        cls,
        session: Session,
        filters: dict[str, Any] | None = None,
        limit: int = 10,
        page: int = 1,
        order_by: list[Any] | None = None,
    ) -> dict[str, Any]:
        query = session.query(cls)
        if filters:
            for condition in filters.values():
                query = query.filter(condition)
        total_records = query.count()
        ordering = order_by or [
            cls._created_at.asc(),
            *[column.asc() for column in cls.__table__.primary_key.columns],
        ]
        records = apply_pagination(
            query,
            page=page,
            limit=limit,
            order_by=ordering,
        ).all()
        return {
            "records": [cls.to_dict(record) for record in records],
            "pagination": build_pagination_meta(
                total_records=total_records,
                limit=limit,
                page=page,
            ).model_dump(),
        }

    @classmethod
    def get_by_id(cls, session: Session, record_id: Any) -> dict[str, Any]:
        try:
            record = session.query(cls).filter_by(id=record_id).one()
            return cls.to_dict(record)
        except NoResultFound as exc:
            raise RecordNotFoundError(cls.__name__, record_id) from exc

    @classmethod
    def create(cls, session: Session, **kwargs) -> dict[str, Any]:
        try:
            record = cls(**kwargs)
            session.add(record)
            session.commit()
            session.refresh(record)
            return cls.to_dict(record)
        except IntegrityError as exc:
            session.rollback()
            raise ValueError(f"Integrity error: {exc.orig}") from exc
        except Exception as exc:
            session.rollback()
            raise ValueError(f"Error creating {cls.__name__}: {exc}") from exc

    @classmethod
    def update(cls, session: Session, record_id: Any, **kwargs) -> dict[str, Any]:
        try:
            record = session.query(cls).filter_by(id=record_id).one()
            for field, value in kwargs.items():
                setattr(record, field, value)
            session.commit()
            session.refresh(record)
            return cls.to_dict(record)
        except NoResultFound as exc:
            raise RecordNotFoundError(cls.__name__, record_id) from exc

    @classmethod
    def update_by_filters(
        cls, session: Session, filters: dict[str, Any], **kwargs
    ) -> dict[str, Any]:
        try:
            record = session.query(cls).filter_by(**filters).one()
            for field, value in kwargs.items():
                setattr(record, field, value)
            session.commit()
            session.refresh(record)
            return cls.to_dict(record)
        except NoResultFound as exc:
            raise ValueError(
                f"{cls.__name__} with filters {filters} not found."
            ) from exc

    @classmethod
    def delete(cls, session: Session, record_id: Any) -> dict[str, str]:
        try:
            record = session.query(cls).filter_by(id=record_id).one()
            record._closed_at = func.now()
            session.add(record)
            session.commit()
            return {"message": f"{cls.__name__} with id={record_id} deleted"}
        except NoResultFound as exc:
            raise RecordNotFoundError(cls.__name__, record_id) from exc

    @classmethod
    def delete_by_filters(
        cls, session: Session, filters: dict[str, Any]
    ) -> dict[str, str]:
        try:
            record = session.query(cls).filter_by(**filters).one()
            record._closed_at = func.now()
            session.add(record)
            session.commit()
            return {"message": f"{cls.__name__} with filters {filters} deleted"}
        except NoResultFound as exc:
            raise ValueError(
                f"{cls.__name__} with filters {filters} not found."
            ) from exc

    @classmethod
    def bulk_create(
        cls, session: Session, records: list[dict[str, Any]]
    ) -> dict[str, str]:
        objects = [cls(**record) for record in records]
        session.bulk_save_objects(objects)
        session.commit()
        return {"message": f"{len(records)} records added successfully"}

    @classmethod
    def update_json_field(
        cls,
        session: Session,
        record_id: Any,
        column_name: str,
        key: str,
        value: Any,
    ) -> dict[str, Any]:
        try:
            record = session.query(cls).filter_by(id=record_id).one()
        except NoResultFound as exc:
            raise RecordNotFoundError(cls.__name__, record_id) from exc

        if not hasattr(record, column_name):
            raise ValueError(f"Column {column_name} does not exist on the model.")
        json_field = getattr(record, column_name)
        if json_field is None:
            setattr(record, column_name, {})
            json_field = getattr(record, column_name)
        if not isinstance(json_field, dict):
            raise ValueError(f"Column {column_name} is not a JSON field.")

        json_field[key] = value
        session.commit()
        session.refresh(record)
        return cls.to_dict(record)

    @classmethod
    def bulk_update_json_field(
        cls,
        session: Session,
        record_id: Any,
        column_name: str,
        updates: dict[str, Any],
    ) -> dict[str, Any]:
        try:
            record = session.query(cls).filter_by(id=record_id).one()
        except NoResultFound as exc:
            raise RecordNotFoundError(cls.__name__, record_id) from exc

        if not hasattr(record, column_name):
            raise ValueError(f"Column '{column_name}' does not exist on the model.")
        json_field = getattr(record, column_name)
        if json_field is None:
            setattr(record, column_name, {})
            json_field = getattr(record, column_name)
        if not isinstance(json_field, dict):
            raise ValueError(f"Column '{column_name}' is not a JSON/dict field.")

        json_field.update(updates)
        session.commit()
        session.refresh(record)
        return cls.to_dict(record)


def to_dict(obj: Any) -> Any:
    if obj is None:
        return {}
    if isinstance(obj, list):
        return [to_dict(item) for item in obj]
    if hasattr(obj, "__table__"):
        return {
            column.name: getattr(obj, column.name) for column in obj.__table__.columns
        }
    return convert_datetime(obj)
