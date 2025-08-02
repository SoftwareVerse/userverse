import os
import logging
from typing import Optional
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy_utils import database_exists, create_database

from app.database import Base  # Ensure your Base = declarative_base()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DatabaseSessionManager:
    def __init__(self, configs: Optional[dict] = None) -> None:
        self._base = Base
        self.configs = configs or {}
        self.database_url = self.configs.get("database_url") or os.getenv(
            "DATABASE_URL", "sqlite:///./development.db"
        )

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
        from .company import Company
        from .role import Role
        from .association_user_company import AssociationUserCompany
        from .user import User

        # Add more models if needed

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


# Default singleton instance
default_db = DatabaseSessionManager()

# Export common accessors for easy import
get_engine = default_db.get_engine
get_session = default_db.get_session
session_local = default_db.session_object
