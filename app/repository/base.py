from __future__ import annotations

from typing import Any, Generic, TypeVar

from sqlalchemy.orm import Session

from app.models.generic_pagination import apply_pagination, build_pagination_meta
from app.repository.database.base_model import RecordNotFoundError, to_dict

TModel = TypeVar("TModel")


class BaseSQLRepository(Generic[TModel]):
    model: type[TModel]

    def __init__(self, db_session: Session):
        self.db_session = db_session

    def _base_query(self):
        return self.db_session.query(self.model)

    def get_by_id(self, record_id: Any) -> TModel:
        record = self._base_query().filter_by(id=record_id).one_or_none()
        if record is None:
            raise RecordNotFoundError(self.model.__name__, record_id)
        return record

    def create(self, **kwargs: Any) -> TModel:
        record = self.model(**kwargs)
        self.db_session.add(record)
        self.db_session.commit()
        self.db_session.refresh(record)
        return record

    def update(self, record: TModel, **kwargs: Any) -> TModel:
        for field, value in kwargs.items():
            setattr(record, field, value)
        self.db_session.add(record)
        self.db_session.commit()
        self.db_session.refresh(record)
        return record

    def soft_delete(self, record: TModel) -> None:
        setattr(record, "_closed_at", self._now_sql())
        self.db_session.add(record)
        self.db_session.commit()

    def update_json_field(
        self,
        record: TModel,
        *,
        column_name: str,
        key: str,
        value: Any,
    ) -> TModel:
        if not hasattr(record, column_name):
            raise ValueError(f"Column {column_name} does not exist on the model.")

        json_field = getattr(record, column_name)
        if json_field is None:
            setattr(record, column_name, {})
            json_field = getattr(record, column_name)
        if not isinstance(json_field, dict):
            raise ValueError(f"Column {column_name} is not a JSON field.")

        json_field[key] = value
        self.db_session.add(record)
        self.db_session.commit()
        self.db_session.refresh(record)
        return record

    def paginate(self, query, *, page: int, limit: int, order_by: list[Any]) -> dict[str, Any]:
        total_records = query.count()
        records = apply_pagination(
            query,
            page=page,
            limit=limit,
            order_by=order_by,
        ).all()
        return {
            "records": [to_dict(record) for record in records],
            "pagination": build_pagination_meta(
                total_records=total_records,
                limit=limit,
                page=page,
            ),
        }

    @staticmethod
    def serialize(record: Any) -> Any:
        return to_dict(record)

    @staticmethod
    def _now_sql():
        from sqlalchemy.sql import func

        return func.now()
