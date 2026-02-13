import logging
from typing import Optional
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy_utils import database_exists, create_database

from app.database import Base  # Ensure your Base = declarative_base()
from app.configs import RuntimeSettings, get_settings

logger = logging.getLogger(__name__)


class DatabaseSessionManager:
    def __init__(self, configs: Optional[dict | RuntimeSettings] = None) -> None:
        self._base = Base
        self.configs = configs or get_settings()
        if isinstance(self.configs, dict):
            self.database_url = self.configs.get(
                "database_url", "sqlite:///./development.db"
            )
        else:
            self.database_url = self.configs.database_url

        # Configure engine
        self.engine = self._configure_engine(self.database_url)

        # Import models to ensure they’re registered with metadata
        self._import_models()

        # Create tables
        self._base.metadata.create_all(bind=self.engine)
        logger.info("Database initialized and tables created if not existing.")

        # Create session factory
        self._session_factory = sessionmaker(
            bind=self.engine, autocommit=False, autoflush=False
        )

    def _configure_engine(self, url: str):
        if not database_exists(url):
            logger.info(f"Database does not exist at {url}. Creating...")
            create_database(url)
        return create_engine(url, pool_pre_ping=True, echo=False)

    def _import_models(self):
        """
        Import all models that need to be registered with the Base metadata.
        Ensure this is called before create_all().
        """
        from app.database import association_user_company  # noqa: F401
        from app.database import company  # noqa: F401
        from app.database import role  # noqa: F401
        from app.database import user  # noqa: F401

    def session_object(self) -> Session:
        """
        Return a session object for scripts or tests.
        """
        return self._session_factory()

    def get_engine(self):
        """
        Return the SQLAlchemy engine.
        """
        return self.engine

    def get_session(self):
        """
        FastAPI-compatible generator dependency.
        """
        db = self._session_factory()
        try:
            yield db
        finally:
            db.close()


_default_db: Optional[DatabaseSessionManager] = None


def _get_default_db() -> DatabaseSessionManager:
    global _default_db
    if _default_db is None:
        _default_db = DatabaseSessionManager()
    return _default_db


def get_engine():
    return _get_default_db().get_engine()


def get_session():
    yield from _get_default_db().get_session()


def session_local():
    return _get_default_db().session_object()
