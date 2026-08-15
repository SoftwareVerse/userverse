import importlib.util
from pathlib import Path
from uuid import uuid4

import pytest

from app.models.system_permissions import SYSTEM_PERMISSION_DEFINITIONS
from app.repository.database.tables import (
    GlobalPermission,
    Role,
    RoleGlobalPermission,
)

MIGRATION_PATH = (
    Path(__file__).parents[2]
    / "alembic/versions/c9f4a6b8d210_seed_default_api_permissions.py"
)


def _load_migration():
    spec = importlib.util.spec_from_file_location(
        "seed_default_api_permissions_migration",
        MIGRATION_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_default_permission_migration_upgrade_is_idempotent_and_reversible(
    test_session,
    monkeypatch,
):
    roles = {
        role_name: Role(name=role_name, description=f"{role_name} role")
        for role_name in ("Owner", "Administrator", "Viewer")
    }
    test_session.add_all(roles.values())
    custom_permission = GlobalPermission(
        name="app.custom.retained",
        description="Must survive the system-permission downgrade",
    )
    test_session.add(custom_permission)
    test_session.flush()
    test_session.add(
        RoleGlobalPermission(
            role_id=roles["Owner"].id,
            global_permission_id=custom_permission.id,
        )
    )
    test_session.commit()
    migration = _load_migration()
    monkeypatch.setattr(migration.op, "get_bind", test_session.connection)

    migration.upgrade()
    migration.upgrade()
    test_session.expire_all()

    assert test_session.query(GlobalPermission).count() == (
        len(SYSTEM_PERMISSION_DEFINITIONS) + 1
    )
    for definition in SYSTEM_PERMISSION_DEFINITIONS:
        permission = test_session.get(GlobalPermission, definition.id)
        assert permission.name == definition.name
        linked_role_names = {
            role_name
            for (role_name,) in test_session.query(Role.name)
            .join(RoleGlobalPermission, RoleGlobalPermission.role_id == Role.id)
            .filter(RoleGlobalPermission.global_permission_id == definition.id)
            .all()
        }
        assert linked_role_names == set(definition.default_roles)

    migration.downgrade()
    test_session.expire_all()

    assert test_session.query(GlobalPermission).all() == [custom_permission]
    assert test_session.query(RoleGlobalPermission).count() == 1
    assert (
        test_session.query(RoleGlobalPermission)
        .filter_by(
            role_id=roles["Owner"].id,
            global_permission_id=custom_permission.id,
        )
        .one_or_none()
        is not None
    )
    assert test_session.query(Role).count() == 3


def test_default_permission_migration_rejects_reserved_name_conflict(
    test_session,
    monkeypatch,
):
    definition = SYSTEM_PERMISSION_DEFINITIONS[0]
    test_session.add(
        GlobalPermission(
            id=uuid4(),
            name=definition.name,
            description="Existing conflicting permission",
        )
    )
    test_session.commit()
    migration = _load_migration()
    monkeypatch.setattr(migration.op, "get_bind", test_session.connection)

    with pytest.raises(RuntimeError, match="Reserved system permission conflict"):
        migration.upgrade()
