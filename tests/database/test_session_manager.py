from app.configs import settings
from app.repository.database.session_manager import DatabaseSessionManager


def test_session_manager_uses_sqlite_engine_for_sqlite_urls(monkeypatch):
    create_engine_calls = []
    monkeypatch.setattr(
        "app.repository.database.session_manager.create_engine",
        lambda url, **kwargs: create_engine_calls.append((url, kwargs)) or "engine",
    )
    monkeypatch.setattr(
        "app.repository.database.session_manager.Base.metadata.create_all",
        lambda bind: None,
    )
    monkeypatch.setattr(
        "app.repository.database.session_manager.DatabaseSessionManager._tables_exist",
        lambda self: False,
    )
    monkeypatch.setattr(settings, "DATABASE_URL", "sqlite:///./development.db")
    monkeypatch.setattr(settings, "DB_AUTO_CREATE", True)

    manager = DatabaseSessionManager()

    assert manager.database_url == "sqlite:///./development.db"
    assert create_engine_calls[0][1]["connect_args"] == {"check_same_thread": False}


def test_session_manager_creates_non_sqlite_database_when_missing(monkeypatch):
    create_engine_calls = []
    created = []
    monkeypatch.setattr(
        "app.repository.database.session_manager.create_engine",
        lambda url, **kwargs: create_engine_calls.append((url, kwargs)) or "engine",
    )
    monkeypatch.setattr(
        "app.repository.database.session_manager.database_exists", lambda url: False
    )
    monkeypatch.setattr(
        "app.repository.database.session_manager.create_database",
        lambda url: created.append(url),
    )
    monkeypatch.setattr(
        "app.repository.database.session_manager.Base.metadata.create_all",
        lambda bind: None,
    )
    monkeypatch.setattr(
        "app.repository.database.session_manager.DatabaseSessionManager._tables_exist",
        lambda self: False,
    )
    monkeypatch.setattr(settings, "DATABASE_URL", "postgresql://db.example/test")
    monkeypatch.setattr(settings, "DB_AUTO_CREATE", True)

    manager = DatabaseSessionManager()

    assert manager.database_url == "postgresql://db.example/test"
    assert created == ["postgresql://db.example/test"]
    assert create_engine_calls[0][1]["pool_pre_ping"] is True


def test_session_local_uses_default_db_session_object(monkeypatch):
    class FakeManager:
        def session_object(self):
            return fake_session

    fake_session = object()
    monkeypatch.setattr("app.repository.database.session_manager._default_db", FakeManager())

    from app.repository.database.session_manager import session_local

    assert session_local() is fake_session
