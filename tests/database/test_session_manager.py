import pytest
from app.configs import settings
from app.repository.database.session_manager import DatabaseSessionManager
from sqlalchemy.pool import StaticPool
from unittest.mock import Mock


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
        "app.repository.database.session_manager.DatabaseSessionManager._table_state",
        lambda self: "missing",
    )
    monkeypatch.setattr(settings, "DATABASE_URL", "sqlite:///./development.db")
    monkeypatch.setattr(settings, "DB_AUTO_CREATE", True)

    manager = DatabaseSessionManager()

    assert manager.database_url == "sqlite:///./development.db"
    assert create_engine_calls[0][1]["connect_args"] == {"check_same_thread": False}
    assert "poolclass" not in create_engine_calls[0][1]


def test_session_manager_uses_static_pool_for_in_memory_sqlite(monkeypatch):
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
        "app.repository.database.session_manager.DatabaseSessionManager._table_state",
        lambda self: "missing",
    )
    monkeypatch.setattr(settings, "DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setattr(settings, "DB_AUTO_CREATE", True)

    DatabaseSessionManager()

    assert create_engine_calls[0][1]["poolclass"] is StaticPool


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
        "app.repository.database.session_manager.DatabaseSessionManager._table_state",
        lambda self: "missing",
    )
    monkeypatch.setattr(settings, "DATABASE_URL", "postgresql://db.example/test")
    monkeypatch.setattr(settings, "DB_AUTO_CREATE", True)

    manager = DatabaseSessionManager()

    assert manager.database_url == "postgresql://db.example/test"
    assert created == ["postgresql://db.example/test"]
    assert create_engine_calls[0][1]["pool_pre_ping"] is True


def test_session_manager_does_not_create_database_when_auto_create_disabled(
    monkeypatch,
):
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
        "app.repository.database.session_manager.DatabaseSessionManager._table_state",
        lambda self: "missing",
    )
    monkeypatch.setattr(settings, "DATABASE_URL", "postgresql://db.example/test")
    monkeypatch.setattr(settings, "DB_AUTO_CREATE", False)
    monkeypatch.setattr(settings, "TESTING", True)

    DatabaseSessionManager()

    assert create_engine_calls[0][0] == "postgresql://db.example/test"
    assert created == []


def test_session_manager_raises_when_schema_missing_and_auto_create_disabled(
    monkeypatch,
):
    monkeypatch.setattr(
        "app.repository.database.session_manager.create_engine",
        lambda url, **kwargs: "engine",
    )
    monkeypatch.setattr(
        "app.repository.database.session_manager.database_exists", lambda url: True
    )
    monkeypatch.setattr(
        "app.repository.database.session_manager.DatabaseSessionManager._table_state",
        lambda self: "missing",
    )
    monkeypatch.setattr(settings, "DATABASE_URL", "postgresql://db.example/test")
    monkeypatch.setattr(settings, "DB_AUTO_CREATE", False)
    monkeypatch.setattr(settings, "TESTING", False)

    try:
        DatabaseSessionManager()
    except RuntimeError as exc:
        assert "run Alembic migrations before startup" in str(exc)
    else:
        raise AssertionError("Expected DatabaseSessionManager to require migrations")


def test_session_manager_raises_on_partial_schema(monkeypatch):
    monkeypatch.setattr(
        "app.repository.database.session_manager.create_engine",
        lambda url, **kwargs: "engine",
    )
    monkeypatch.setattr(settings, "DATABASE_URL", "sqlite:///./development.db")
    monkeypatch.setattr(settings, "DB_AUTO_CREATE", True)

    monkeypatch.setattr(
        "app.repository.database.session_manager.DatabaseSessionManager._table_state",
        lambda self: "partial",
    )

    try:
        DatabaseSessionManager()
    except RuntimeError as exc:
        assert "incompatible with current models" in str(exc)
    else:
        raise AssertionError("Expected DatabaseSessionManager to reject partial schema")


def test_session_manager_raises_on_incompatible_schema(monkeypatch):
    monkeypatch.setattr(
        "app.repository.database.session_manager.create_engine",
        lambda url, **kwargs: "engine",
    )
    monkeypatch.setattr(settings, "DATABASE_URL", "sqlite:///./development.db")
    monkeypatch.setattr(settings, "DB_AUTO_CREATE", True)

    monkeypatch.setattr(
        "app.repository.database.session_manager.DatabaseSessionManager._table_state",
        lambda self: "incompatible",
    )

    try:
        DatabaseSessionManager()
    except RuntimeError as exc:
        assert "incompatible with current models" in str(exc)
    else:
        raise AssertionError(
            "Expected DatabaseSessionManager to reject incompatible schema"
        )


def test_session_local_uses_default_db_session_object(monkeypatch):
    class FakeManager:
        def session_object(self):
            return fake_session

    fake_session = object()
    monkeypatch.setattr(
        "app.repository.database.session_manager._default_db", FakeManager()
    )

    from app.repository.database.session_manager import session_local

    assert session_local() is fake_session


def test_get_engine_uses_default_db_engine(monkeypatch):
    class FakeManager:
        def get_engine(self):
            return fake_engine

    fake_engine = object()
    monkeypatch.setattr(
        "app.repository.database.session_manager._default_db", FakeManager()
    )

    from app.repository.database.session_manager import get_engine

    assert get_engine() is fake_engine


def test_table_state_and_schema_helpers():
    manager = DatabaseSessionManager.__new__(DatabaseSessionManager)
    manager.expected_tables = ("role", "company_role")
    manager.expected_columns = {
        "role": {"id", "name"},
        "company_role": {"company_id", "role_id"},
    }
    manager.forbidden_columns = {
        "role": {"company_id"},
        "company_role": set(),
    }
    manager.engine = object()

    partial_inspector = Mock()
    partial_inspector.has_table.side_effect = lambda name: name == "role"

    incompatible_inspector = Mock()
    incompatible_inspector.has_table.return_value = True
    incompatible_inspector.get_columns.side_effect = lambda table_name: (
        [{"name": "id"}, {"name": "name"}, {"name": "company_id"}]
        if table_name == "role"
        else [{"name": "company_id"}]
    )

    monkeypatch = pytest.MonkeyPatch()
    try:
        monkeypatch.setattr(
            "app.repository.database.session_manager.inspect",
            lambda engine: partial_inspector,
        )
        assert manager._table_state() == "partial"

        monkeypatch.setattr(
            "app.repository.database.session_manager.inspect",
            lambda engine: incompatible_inspector,
        )
        assert manager._table_state() == "incompatible"
        assert manager._tables_exist() is False
        assert manager._schema_matches_models(incompatible_inspector) is False
        assert manager.get_engine() is manager.engine
    finally:
        monkeypatch.undo()


def test_schema_matches_models_rejects_missing_required_columns():
    manager = DatabaseSessionManager.__new__(DatabaseSessionManager)
    manager.expected_columns = {"role": {"id", "name"}}
    manager.forbidden_columns = {"role": set()}
    inspector = Mock()
    inspector.get_columns.return_value = [{"name": "id"}]

    assert manager._schema_matches_models(inspector) is False


def test_expected_user_schema_includes_superuser_flag():
    assert "is_superuser" in DatabaseSessionManager.expected_columns["user"]
