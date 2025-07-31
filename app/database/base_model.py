"""
Base model for all database entities.
Provides common fields and methods for CRUD operations.
 - path: app/database/base_model.py
"""

from typing import Any, Dict, List, Optional, Union
from sqlalchemy import Column, DateTime, JSON
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.mutable import MutableDict

from app.utils.date_converter import convert_datetime


from app.utils.logging import logger

from app.database import Base  # Ensure Base is imported from the correct module


class RecordNotFoundError(Exception):
    """Custom exception for record not found errors."""

    def __init__(self, model_name: str, record_id: Any):
        super().__init__(f"No {model_name} found with id={record_id}")


class BaseModel(Base):
    __abstract__ = True  # This ensures the class is not mapped to a table

    # Common fields for all models
    _created_at = Column(DateTime(), nullable=False, server_default=func.now())
    _updated_at = Column(DateTime(), nullable=True, onupdate=func.now())
    _closed_at = Column(DateTime(), nullable=True)
    # Use MutableDict here:
    primary_meta_data = Column(MutableDict.as_mutable(JSON), default=dict)
    secondary_meta_data = Column(MutableDict.as_mutable(JSON), default=dict)

    @staticmethod
    def to_dict(obj: Any) -> Dict[str, Any]:
        """Converts SQLAlchemy model object to dictionary."""
        if obj is None:
            return {}
        if isinstance(obj, list):
            return [BaseModel.to_dict(item) for item in obj]
        if isinstance(obj, BaseModel):
            return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}
        return convert_datetime(obj)

    @classmethod
    def get_all(
        cls,
        session: Session,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 10,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """
        Retrieve all records of a model with optional filters and pagination.
        """
        query = session.query(cls)

        # Apply filters
        if filters:
            for column, condition in filters.items():
                query = query.filter(condition)

        # Get total records count
        total_records = query.count()

        # Apply pagination
        records = query.offset(offset).limit(limit).all()

        return {
            "records": [cls.to_dict(record) for record in records],
            "pagination": cls._get_pagination_metadata(total_records, limit, offset),
        }

    @classmethod
    def get_by_id(cls, session: Session, record_id: Any) -> Dict[str, Any]:
        """
        Retrieve a single record by its ID.
        """
        try:
            record = session.query(cls).filter_by(id=record_id).one()
            return cls.to_dict(record)
        except NoResultFound:
            raise RecordNotFoundError(cls.__name__, record_id)

    @classmethod
    def create(cls, session: Session, **kwargs) -> Dict[str, Any]:
        """
        Create and save a new record.
        """
        try:
            record = cls(**kwargs)
            session.add(record)
            session.commit()
            logger.info(f"{cls.__name__} created: {record}")
            return cls.to_dict(record)
        except IntegrityError as e:
            session.rollback()
            logger.error(f"Integrity error: {e.orig}")
            raise ValueError(f"Integrity error: {e.orig}")
        except Exception as e:
            session.rollback()
            logger.error(f"Error creating {cls.__name__}: {e}")
            raise ValueError(f"Error creating {cls.__name__}: {e}")

    @classmethod
    def update(cls, session: Session, record_id: Any, **kwargs) -> Dict[str, Any]:
        """
        Update an existing record by its ID with given fields.
        """
        try:
            record = session.query(cls).filter_by(id=record_id).one()
            for field, value in kwargs.items():
                setattr(record, field, value)
            session.commit()
            logger.info(f"{cls.__name__} updated: {record}")
            return cls.to_dict(record)
        except NoResultFound:
            raise RecordNotFoundError(cls.__name__, record_id)

    @classmethod
    def update_by_filters(
        cls, session: Session, filters: Dict[str, Any], **kwargs
    ) -> Dict[str, Any]:
        """
        Update a record using composite key filters (e.g., company_id + name).
        """
        try:
            record = session.query(cls).filter_by(**filters).one()
            for field, value in kwargs.items():
                setattr(record, field, value)
            session.commit()
            logger.info(f"{cls.__name__} updated with filters {filters}")
            return cls.to_dict(record)
        except NoResultFound:
            raise ValueError(f"{cls.__name__} with filters {filters} not found.")

    @classmethod
    def delete(cls, session: Session, record_id: Any) -> Dict[str, str]:
        """
        Soft delete a record by its ID.
        """
        try:
            record = session.query(cls).filter_by(id=record_id).one()
            record._closed_at = func.now()
            session.add(record)
            session.commit()
            logger.info(f"{cls.__name__} with id={record_id} deleted.")
            return {"message": f"{cls.__name__} with id={record_id} deleted"}
        except NoResultFound:
            raise RecordNotFoundError(cls.__name__, record_id)

    @classmethod
    def delete_by_filters(
        cls, session: Session, filters: Dict[str, Any]
    ) -> Dict[str, str]:
        """
        Soft delete a record using composite key filters.
        """
        try:
            record = session.query(cls).filter_by(**filters).one()
            record._closed_at = func.now()
            session.commit()
            logger.info(f"{cls.__name__} deleted with filters {filters}")
            return {"message": f"{cls.__name__} with filters {filters} deleted"}
        except NoResultFound:
            raise ValueError(f"{cls.__name__} with filters {filters} not found.")

    @classmethod
    def bulk_create(
        cls, session: Session, records: List[Dict[str, Any]]
    ) -> Dict[str, str]:
        """
        Bulk create records for a model.
        """
        objects = [cls(**record) for record in records]
        session.bulk_save_objects(objects)
        session.commit()
        logger.info(f"Bulk created {len(records)} records for {cls.__name__}.")
        return {"message": f"{len(records)} records added successfully"}

    @classmethod
    def update_json_field(
        cls,
        session: Session,
        record_id: Any,
        column_name: str,
        key: str,
        value: Union[str, int, list, dict],
    ) -> Dict[str, Any]:
        try:
            record = session.query(cls).filter_by(id=record_id).one()

            # Check if the column exists
            if not hasattr(record, column_name):
                raise ValueError(f"Column {column_name} does not exist on the model.")

            json_field = getattr(record, column_name)

            # MutableDict takes care of tracking, no need to reassign:
            if json_field is None:
                json_field = {}
                setattr(record, column_name, json_field)

            if not isinstance(json_field, dict):
                raise ValueError(f"Column {column_name} is not a JSON field.")

            json_field[key] = value  # Automatic change tracking by MutableDict
            session.commit()
            logger.info(
                f"Updated JSON field '{column_name}' for {cls.__name__} with id={record_id}"
            )
            return cls.to_dict(record)
        except NoResultFound:
            raise RecordNotFoundError(cls.__name__, record_id)

    @classmethod
    def bulk_update_json_field(
        cls,
        session: Session,
        record_id: Any,
        column_name: str,
        updates: Dict[str, Union[str, int, list, dict]],
    ) -> Dict[str, Any]:
        """
        Atomically updates multiple keys in a JSON/dict column with MutableDict support.

        Args:
            session: SQLAlchemy session.
            record_id: ID of the record to update.
            column_name: Name of the JSON column to update.
            updates: Dictionary of key-value pairs to merge.

        Returns:
            Updated record as a dictionary.
        """
        try:
            record = session.query(cls).filter_by(id=record_id).one()

            if not hasattr(record, column_name):
                raise ValueError(f"Column '{column_name}' does not exist on the model.")

            json_field = getattr(record, column_name)

            if json_field is None:
                json_field = {}
                setattr(record, column_name, json_field)

            if not isinstance(json_field, dict):
                raise ValueError(f"Column '{column_name}' is not a JSON/dict field.")

            for key, value in updates.items():
                json_field[key] = value  # MutableDict handles change tracking

            session.commit()
            session.refresh(record)  # Ensure we return fresh state after commit

            logger.info(
                f"Bulk updated JSON field '{column_name}' for {cls.__name__} with id={record_id}: {updates}"
            )
            return cls.to_dict(record)

        except NoResultFound:
            raise RecordNotFoundError(cls.__name__, record_id)

    @staticmethod
    def _get_pagination_metadata(
        total_records: int, limit: int, offset: int
    ) -> Dict[str, int]:
        """
        Generate pagination metadata.
        """
        return {
            "total_records": total_records,
            "limit": limit,
            "offset": offset,
            "current_page": offset // limit + 1,
            "total_pages": (total_records + limit - 1) // limit,  # Ceiling division
        }