from unittest.mock import Mock
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from app.repository.database.tables import Role
from app.repository.permission import (
    CompanyPermissionRepository,
    RolePermissionRepository,
)
from app.utils.app_error import AppError


def test_company_permission_assignment_translates_constraint_race(monkeypatch):
    session = Mock()
    session.query.return_value.filter_by.return_value.one_or_none.return_value = None
    session.commit.side_effect = IntegrityError(
        "insert company role permission",
        {},
        Exception("composite foreign key changed concurrently"),
    )
    repository = RolePermissionRepository(session)
    company_id = uuid4()
    role = Role(id=uuid4(), name="Concurrent Role", description=None)
    permission = Mock(id=uuid4())

    monkeypatch.setattr(repository, "_ensure_company_role", lambda *args: Mock())
    monkeypatch.setattr(repository, "_ensure_role", lambda role_id: role)
    monkeypatch.setattr(
        CompanyPermissionRepository,
        "ensure_record",
        lambda self, permission_id: permission,
    )

    with pytest.raises(AppError) as exc_info:
        repository.assign_company_permission(
            company_id,
            role.id,
            permission.id,
        )

    assert exc_info.value.status_code == 404
    session.rollback.assert_called_once_with()
