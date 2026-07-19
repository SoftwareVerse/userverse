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
        "role",
        "user",
    )

    def __init__(self) -> None:
        self._base = Base
        self.database_url = settings.DATABASE_URL
        self._import_models()

        self.engine = self._configure_engine()

        tables_exist = self._tables_exist()
        if settings.DB_AUTO_CREATE and not tables_exist:
            self._base.metadata.create_all(bind=self.engine)
        elif not tables_exist and not settings.TESTING:
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
            engine_kwargs["poolclass"] = StaticPool
            return create_engine(url, **engine_kwargs)

        if not database_exists(url):
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
            Role,
            User,
        )

    def _tables_exist(self) -> bool:
        inspector = inspect(self.engine)
        return all(
            inspector.has_table(table_name) for table_name in self.expected_tables
        )

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
