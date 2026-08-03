from __future__ import annotations

from typing import Any, Generator

from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy_utils import create_database, database_exists

from app.configs import settings
from app.repository.database import Base


class DatabaseSessionManager:
    expected_tables = (
        "association_user_company",
        "company",
        "company_role",
        "role",
        "user",
    )
    expected_columns = {
        "association_user_company": {"user_id", "company_id", "role_id"},
        "company": {"id", "email"},
        "company_role": {"company_id", "role_id"},
        "role": {"id", "name", "description"},
        "user": {"id", "email", "password"},
    }
    forbidden_columns = {
        "association_user_company": {"role_name", "user_level"},
        "role": {"company_id"},
    }

    def __init__(self) -> None:
        self._base = Base
        self.database_url = settings.DATABASE_URL
        self._import_models()

        self.engine = self._configure_engine()

        table_state = self._table_state()
        if settings.DB_AUTO_CREATE and table_state == "missing":
            self._base.metadata.create_all(bind=self.engine)
        elif table_state in {"partial", "incompatible"}:
            raise RuntimeError(
                "Database schema is incompatible with current models; run Alembic "
                "migrations or recreate the database."
            )
        elif table_state == "missing" and not settings.TESTING:
            raise RuntimeError(
                "Database schema is not initialized; run Alembic migrations before startup"
            )

        self.SessionLocal = sessionmaker(
            bind=self.engine,
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
        )

    def _configure_engine(self) -> Engine:
        url = self.database_url
        engine_kwargs: dict[str, Any] = {
            "pool_pre_ping": True,
            "echo": settings.DB_ECHO,
        }

        if url.startswith("sqlite"):
            engine_kwargs["connect_args"] = {"check_same_thread": False}
            if url in {"sqlite://", "sqlite:///:memory:"}:
                engine_kwargs["poolclass"] = StaticPool
            return create_engine(url, **engine_kwargs)

        if settings.DB_AUTO_CREATE and not database_exists(url):
            create_database(url)

        if url.startswith("postgresql"):
            engine_kwargs.update(
                {
                    "pool_size": settings.DB_POOL_SIZE,
                    "max_overflow": settings.DB_MAX_OVERFLOW,
                    "pool_timeout": settings.DB_POOL_TIMEOUT,
                    "pool_recycle": settings.DB_POOL_RECYCLE,
                }
            )

        return create_engine(url, **engine_kwargs)

    def _import_models(self) -> None:
        from app.repository.database.tables import (  # noqa: F401
            AssociationUserCompany,
            Company,
            CompanyRole,
            Role,
            User,
        )

    def _table_state(self) -> str:
        inspector = inspect(self.engine)
        existing_tables = {
            table_name
            for table_name in self.expected_tables
            if inspector.has_table(table_name)
        }
        if not existing_tables:
            return "missing"
        if existing_tables != set(self.expected_tables):
            return "partial"
        if not self._schema_matches_models(inspector):
            return "incompatible"
        return "ok"

    def _tables_exist(self) -> bool:
        return self._table_state() == "ok"

    def _schema_matches_models(self, inspector) -> bool:
        for table_name, required_columns in self.expected_columns.items():
            actual_columns = {
                column["name"] for column in inspector.get_columns(table_name)
            }
            if not required_columns.issubset(actual_columns):
                return False
            forbidden = self.forbidden_columns.get(table_name, set())
            if actual_columns.intersection(forbidden):
                return False
        return True

    def get_session(self) -> Generator[Session, None, None]:
        db = self.SessionLocal()
        try:
            yield db
        finally:
            db.close()

    def session_object(self) -> Session:
        return self.SessionLocal()

    def get_engine(self) -> Engine:
        return self.engine


_default_db: DatabaseSessionManager | None = None


def _get_default_db() -> DatabaseSessionManager:
    global _default_db
    if _default_db is None:
        _default_db = DatabaseSessionManager()
    return _default_db


def get_engine() -> Engine:
    return _get_default_db().get_engine()


def get_session():
    yield from _get_default_db().get_session()


def session_local() -> Session:
    return _get_default_db().session_object()
