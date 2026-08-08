import importlib.util
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import (
    Column,
    MetaData,
    String,
    Table,
    Uuid,
    create_engine,
    inspect,
    select,
)

MIGRATION_PATH = (
    Path(__file__).parents[2]
    / "alembic/versions/d1e5f7a9b302_add_superuser_bootstrap_control.py"
)


def _load_migration():
    spec = importlib.util.spec_from_file_location(
        "add_superuser_bootstrap_control_migration",
        MIGRATION_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_superuser_bootstrap_migration_upgrade_and_downgrade():
    engine = create_engine("sqlite:///:memory:")
    metadata = MetaData()
    Table(
        "user",
        metadata,
        Column("id", Uuid(), primary_key=True),
        Column("email", String(255), nullable=False),
    )
    metadata.create_all(engine)
    migration = _load_migration()

    with engine.begin() as connection:
        migration.op = Operations(MigrationContext.configure(connection))
        migration.upgrade()

        inspector = inspect(connection)
        assert "superuser_bootstrap_control" in inspector.get_table_names()
        assert "privileged_access_event" in inspector.get_table_names()
        control = Table(
            "superuser_bootstrap_control",
            MetaData(),
            autoload_with=connection,
        )
        assert connection.execute(select(control.c.id)).scalar_one() == 1
        assert {
            index["name"] for index in inspector.get_indexes("privileged_access_event")
        } == {"ix_privileged_access_event_target_created"}

        migration.downgrade()
        assert set(inspect(connection).get_table_names()) == {"user"}
