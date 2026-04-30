from types import SimpleNamespace

from app.database.session_manager import DatabaseSessionManager


def test_session_manager_uses_default_sqlite_url_for_dict_configs(monkeypatch):
    create_engine_calls = []
    monkeypatch.setattr("app.database.session_manager.create_engine", lambda url, **kwargs: create_engine_calls.append((url, kwargs)) or "engine")
    monkeypatch.setattr("app.database.session_manager.Base.metadata.create_all", lambda bind: None)
    monkeypatch.setattr("app.database.session_manager.DatabaseSessionManager._import_models", lambda self: None)

    manager = DatabaseSessionManager(configs={})

    assert manager.database_url == "sqlite:///./development.db"
    assert create_engine_calls[0][1]["connect_args"] == {"check_same_thread": False}


def test_session_manager_creates_non_sqlite_database_when_missing(monkeypatch):
    create_engine_calls = []
    created = []
    monkeypatch.setattr("app.database.session_manager.create_engine", lambda url, **kwargs: create_engine_calls.append((url, kwargs)) or "engine")
    monkeypatch.setattr("app.database.session_manager.database_exists", lambda url: False)
    monkeypatch.setattr("app.database.session_manager.create_database", lambda url: created.append(url))
    monkeypatch.setattr("app.database.session_manager.Base.metadata.create_all", lambda bind: None)
    monkeypatch.setattr("app.database.session_manager.DatabaseSessionManager._import_models", lambda self: None)

    manager = DatabaseSessionManager(
        configs=SimpleNamespace(database_url="postgresql://db.example/test")
    )

    assert manager.database_url == "postgresql://db.example/test"
    assert created == ["postgresql://db.example/test"]
    assert create_engine_calls[0][1]["pool_pre_ping"] is True


def test_session_local_uses_default_db_session_object(monkeypatch):
    fake_session = object()
    fake_manager = SimpleNamespace(session_object=lambda: fake_session)
    monkeypatch.setattr("app.database.session_manager._default_db", fake_manager)

    from app.database.session_manager import session_local

    assert session_local() is fake_session
