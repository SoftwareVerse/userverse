from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from app.configs import settings

PROJECT_ROOT = Path(__file__).parents[2]
LEGACY_DATA_REVISION = "9e858906b135"
HEAD_REVISION = "d1e5f7a9b302"


def _alembic_config() -> Config:
    return Config(str(PROJECT_ROOT / "alembic.ini"))


def test_full_migration_chain_from_empty_database_preserves_legacy_membership(
    tmp_path,
    monkeypatch,
):
    database_path = tmp_path / "migration-chain.db"
    database_url = f"sqlite:///{database_path}"
    monkeypatch.setattr(settings, "DATABASE_URL", database_url)
    config = _alembic_config()

    command.upgrade(config, LEGACY_DATA_REVISION)

    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(text("""
                INSERT INTO user (id, email, password)
                VALUES (1, 'owner@example.com', 'hashed-password')
                """))
        connection.execute(text("""
                INSERT INTO company (id, name, email)
                VALUES (1, 'Example Company', 'company@example.com')
                """))
        connection.execute(text("""
                INSERT INTO association_user_company
                    (user_id, company_id, user_level)
                VALUES (1, 1, 'Owner')
                """))

    command.upgrade(config, "head")

    with engine.connect() as connection:
        inspector = inspect(connection)
        assert {
            "association_user_company",
            "company",
            "company_permission",
            "company_role",
            "company_role_permission",
            "global_permission",
            "privileged_access_event",
            "role",
            "role_global_permission",
            "superuser_bootstrap_control",
            "user",
            "user_role",
        }.issubset(inspector.get_table_names())
        assert (
            connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one()
            == HEAD_REVISION
        )
        assert connection.execute(text("""
                SELECT role.name
                FROM association_user_company AS membership
                JOIN role ON role.id = membership.role_id
                """)).scalar_one() == "Owner"
