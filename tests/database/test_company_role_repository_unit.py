from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.company.response_messages import CompanyRoleResponseMessages
from app.models.company.roles import (
    RoleAssignCompaniesModel,
    RoleCreateModel,
    RoleDeleteModel,
    RoleReadModel,
    RoleUpdateModel,
)
from app.models.user.account_status import UserAccountStatus
from app.models.user.user import UserReadModel
from app.repository.company_role import CompanyRoleAssignmentRepository, RoleRepository
from app.repository.database.tables import Role
from app.utils.app_error import AppError


def _acting_user() -> UserReadModel:
    return UserReadModel(
        id=uuid4(),
        email="admin@example.com",
        first_name="Admin",
        last_name="User",
        phone_number="+27123456789",
        status=UserAccountStatus.ACTIVE.name_value,
        is_superuser=False,
    )


def _role_obj(name: str = "Viewer", description: str = "Read only"):
    return SimpleNamespace(
        id=uuid4(), name=name, description=description, _closed_at=None
    )


def _role_model(name: str = "Viewer", description: str = "Read only") -> Role:
    return Role(id=uuid4(), name=name, description=description)


def test_role_repository_requires_session():
    with pytest.raises(TypeError, match="requires a database session"):
        RoleRepository()


def test_role_repository_create_role_success(monkeypatch):
    repository = RoleRepository(session=Mock())
    created = _role_obj()
    expected = RoleReadModel(
        id=str(created.id), name=created.name, description=created.description
    )

    monkeypatch.setattr(repository, "create", lambda **kwargs: created)
    monkeypatch.setattr(
        repository,
        "update_json_field",
        lambda role, **kwargs: role,
    )
    monkeypatch.setattr(
        RoleRepository, "_to_read_model", staticmethod(lambda role: expected)
    )

    result = repository.create_role(
        RoleCreateModel(name="Viewer", description="Read only"),
        _acting_user(),
    )

    assert result == expected


def test_role_repository_to_read_model_serializes_id():
    role = _role_model()

    result = RoleRepository._to_read_model(role)

    assert result.id == str(role.id)


def test_role_repository_create_role_wraps_integrity_error(monkeypatch):
    repository = RoleRepository(session=Mock())
    repository.db_session.rollback = Mock()

    def _raise_integrity(**kwargs):
        raise IntegrityError("insert", {}, Exception("duplicate"))

    monkeypatch.setattr(repository, "create", _raise_integrity)

    with pytest.raises(AppError) as exc_info:
        repository.create_role(
            RoleCreateModel(name="Viewer", description="Read only"),
            _acting_user(),
        )

    assert (
        exc_info.value.detail["message"]
        == CompanyRoleResponseMessages.ROLE_ALREADY_EXISTS.value
    )
    repository.db_session.rollback.assert_called_once()


def test_role_repository_create_role_wraps_generic_error(monkeypatch):
    repository = RoleRepository(session=Mock())
    monkeypatch.setattr(
        repository,
        "create",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    with pytest.raises(AppError) as exc_info:
        repository.create_role(
            RoleCreateModel(name="Viewer", description="Read only"),
            _acting_user(),
        )

    assert (
        exc_info.value.detail["message"]
        == CompanyRoleResponseMessages.ROLE_CREATION_FAILED.value
    )


def test_role_repository_update_role_global_and_company_paths(monkeypatch):
    repository = RoleRepository(session=Mock())
    repository.db_session.refresh = Mock()
    global_role = _role_obj(name="Viewer", description="Old")
    company_id = uuid4()
    company_repository = RoleRepository(session=Mock(), company_id=company_id)
    company_repository.db_session.refresh = Mock()
    company_role = _role_obj(name="Viewer", description="Old")

    monkeypatch.setattr(repository, "get_role_record", lambda role_id: global_role)
    monkeypatch.setattr(
        company_repository,
        "_to_read_model",
        staticmethod(
            lambda role: RoleReadModel(
                id=str(role.id), name=role.name, description=role.description
            )
        ),
    )
    monkeypatch.setattr(
        RoleRepository,
        "_to_read_model",
        staticmethod(
            lambda role: RoleReadModel(
                id=str(role.id), name=role.name, description=role.description
            )
        ),
    )
    monkeypatch.setattr(
        CompanyRoleAssignmentRepository,
        "get_role_name_assigned",
        lambda self, name: company_role,
    )

    updated_global = repository.update_role(
        global_role.id,
        RoleUpdateModel(name="Viewer+", description="New"),
    )
    updated_company = company_repository.update_role(
        "Viewer",
        RoleUpdateModel(name="Company Viewer", description="Company"),
    )

    assert updated_global.name == "Viewer+"
    assert updated_global.description == "New"
    assert updated_company.name == "Company Viewer"
    assert updated_company.description == "Company"


def test_role_repository_ensure_role_helpers(monkeypatch):
    role = _role_model()
    repository = RoleRepository(session=Mock())
    monkeypatch.setattr(repository, "get_role_record", lambda role_id: None)

    with pytest.raises(AppError) as exc_info:
        repository.ensure_role_exists(uuid4())
    assert (
        exc_info.value.detail["message"]
        == CompanyRoleResponseMessages.ROLE_NOT_FOUND.value
    )

    monkeypatch.setattr(repository, "get_role_by_name", lambda name: None)
    with pytest.raises(AppError) as exc_info:
        repository.ensure_role_by_name("Missing")
    assert (
        exc_info.value.detail["message"]
        == "Failed to add user to the company. Please verify the input."
    )

    monkeypatch.setattr(repository, "get_role_by_name", lambda name: role)
    assert repository.ensure_role_by_name("Viewer") is role

    companyless = RoleRepository(session=Mock())
    monkeypatch.setattr(companyless, "ensure_role_by_name", lambda name: role)
    assert companyless.ensure_role_belongs_to_company("Viewer") is role

    company_repo = RoleRepository(session=Mock(), company_id=uuid4())
    monkeypatch.setattr(
        CompanyRoleAssignmentRepository,
        "get_role_name_assigned",
        lambda self, name: role,
    )
    assert company_repo.ensure_role_belongs_to_company("Viewer") is role

    monkeypatch.setattr(
        CompanyRoleAssignmentRepository,
        "get_role_name_assigned",
        lambda self, name: SimpleNamespace(),
    )
    with pytest.raises(AppError) as exc_info:
        company_repo.ensure_role_belongs_to_company("Missing")
    assert (
        exc_info.value.detail["message"]
        == "Failed to add user to the company. Please verify the input."
    )


def test_role_repository_update_role_error_paths(monkeypatch):
    repository = RoleRepository(session=Mock())
    repository.db_session.rollback = Mock()
    monkeypatch.setattr(repository, "get_role_record", lambda role_id: None)

    with pytest.raises(AppError) as exc_info:
        repository.update_role(
            uuid4(), RoleUpdateModel(name="Renamed", description=None)
        )
    assert (
        exc_info.value.detail["message"]
        == CompanyRoleResponseMessages.ROLE_UPDATE_FAILED.value
    )

    company_repo = RoleRepository(session=Mock(), company_id=uuid4())
    company_repo.db_session.rollback = Mock()
    monkeypatch.setattr(
        CompanyRoleAssignmentRepository,
        "get_role_name_assigned",
        lambda self, name: None,
    )
    with pytest.raises(AppError) as exc_info:
        company_repo.update_role("Missing", RoleUpdateModel(name=None, description="x"))
    assert (
        exc_info.value.detail["message"]
        == CompanyRoleResponseMessages.ROLE_UPDATE_FAILED.value
    )

    broken_repo = RoleRepository(session=Mock())
    broken_repo.db_session.rollback = Mock()
    broken_repo.db_session.commit = Mock(side_effect=RuntimeError("commit failed"))
    monkeypatch.setattr(broken_repo, "get_role_record", lambda role_id: _role_obj())
    with pytest.raises(AppError) as exc_info:
        broken_repo.update_role(uuid4(), RoleUpdateModel(name="X", description=None))
    assert (
        exc_info.value.detail["message"]
        == CompanyRoleResponseMessages.ROLE_UPDATE_FAILED.value
    )
    broken_repo.db_session.rollback.assert_called_once()


def test_role_repository_delete_role_branches(monkeypatch):
    deleted_by = _acting_user()

    with pytest.raises(AppError) as exc_info:
        RoleRepository(session=Mock()).delete_role(
            payload=RoleDeleteModel(
                role_name_to_delete="Client",
                replacement_role_name="Viewer",
            ),
            deleted_by=deleted_by,
        )
    assert (
        exc_info.value.detail["message"]
        == CompanyRoleResponseMessages.ROLE_UPDATE_FAILED.value
    )

    company_repository = RoleRepository(session=Mock(), company_id=uuid4())
    with pytest.raises(AppError) as exc_info:
        company_repository.delete_role(
            payload=RoleDeleteModel(
                role_name_to_delete="Client",
                replacement_role_name="Viewer",
            ),
        )
    assert (
        exc_info.value.detail["message"]
        == CompanyRoleResponseMessages.ROLE_UPDATE_FAILED.value
    )

    monkeypatch.setattr(
        Role,
        "delete_role_and_reassign_users",
        lambda **kwargs: {"message": "deleted", "users_reassigned": 2},
    )
    result = company_repository.delete_role(
        payload=RoleDeleteModel(
            role_name_to_delete="Client",
            replacement_role_name="Viewer",
        ),
        deleted_by=deleted_by,
    )
    assert result["users_reassigned"] == 2

    active_role = _role_obj(name="Viewer")
    global_repository = RoleRepository(session=Mock())
    global_repository.db_session.add = Mock()
    global_repository.db_session.commit = Mock()
    global_repository.db_session.rollback = Mock()
    monkeypatch.setattr(
        global_repository, "get_role_record", lambda role_id: active_role
    )
    monkeypatch.setattr(
        global_repository, "update_json_field", lambda role, **kwargs: role
    )
    blocked_query = Mock()
    blocked_query.filter.return_value.count.return_value = 1
    global_repository.db_session.query.return_value = blocked_query

    with pytest.raises(AppError) as exc_info:
        global_repository.delete_role(active_role.id, deleted_by)
    assert (
        exc_info.value.detail["message"]
        == CompanyRoleResponseMessages.ROLE_DELETION_FAILED.value
    )

    success_repository = RoleRepository(session=Mock())
    success_repository.db_session.add = Mock()
    success_repository.db_session.commit = Mock()
    success_repository.db_session.rollback = Mock()
    monkeypatch.setattr(
        success_repository, "get_role_record", lambda role_id: active_role
    )
    monkeypatch.setattr(
        success_repository, "update_json_field", lambda role, **kwargs: role
    )
    clear_query = Mock()
    clear_query.filter.return_value.count.return_value = 0
    success_repository.db_session.query.return_value = clear_query

    success = success_repository.delete_role(active_role.id, deleted_by)
    assert success["message"] == f"Role '{active_role.name}' deleted successfully."

    missing_args_repository = RoleRepository(session=Mock())
    missing_args_repository.db_session.rollback = Mock()
    with pytest.raises(AppError) as exc_info:
        missing_args_repository.delete_role()
    assert (
        exc_info.value.detail["message"]
        == CompanyRoleResponseMessages.ROLE_DELETION_FAILED.value
    )

    missing_role_repository = RoleRepository(session=Mock())
    missing_role_repository.db_session.rollback = Mock()
    monkeypatch.setattr(
        missing_role_repository, "get_role_record", lambda role_id: None
    )
    with pytest.raises(AppError) as exc_info:
        missing_role_repository.delete_role(uuid4(), deleted_by)
    assert (
        exc_info.value.detail["message"]
        == CompanyRoleResponseMessages.ROLE_DELETION_FAILED.value
    )


def test_company_role_assignment_assign_role_to_companies_skips_existing_and_adds_new(
    monkeypatch,
):
    session = Mock()
    assigned_by = _acting_user()
    role = _role_obj()
    company_ids = [str(uuid4()), str(uuid4())]
    created_assignments: list[tuple[str, str]] = []
    updated_assignments: list[str] = []

    def _get_assignment(self, role_id):
        return object() if self.company_id == uuid4_obj else None

    uuid4_obj = uuid4(company_ids[0]) if False else None

    first_company = company_ids[0]

    def _patched_get_assignment(self, role_id):
        return object() if str(self.company_id) == first_company else None

    monkeypatch.setattr(
        CompanyRoleAssignmentRepository,
        "get_assignment",
        _patched_get_assignment,
    )
    monkeypatch.setattr(
        CompanyRoleAssignmentRepository,
        "create",
        lambda self, **kwargs: created_assignments.append(
            (str(kwargs["company_id"]), str(kwargs["role_id"]))
        )
        or SimpleNamespace(),
    )
    monkeypatch.setattr(
        CompanyRoleAssignmentRepository,
        "update_json_field",
        lambda self, assignment, **kwargs: updated_assignments.append(
            str(self.company_id)
        ),
    )

    repository = CompanyRoleAssignmentRepository(uuid4(), session)
    result = repository.assign_role_to_companies(
        role=role,
        payload=RoleAssignCompaniesModel(company_ids=company_ids),
        assigned_by=assigned_by,
    )

    assert result == {"role_id": str(role.id), "company_ids": [company_ids[1]]}
    assert created_assignments == [(company_ids[1], str(role.id))]
    assert updated_assignments == [company_ids[1]]


def test_company_role_assignment_get_roles_and_ensure_assigned_branches(monkeypatch):
    repository = CompanyRoleAssignmentRepository(uuid4(), Mock())
    monkeypatch.setattr(
        repository,
        "paginate",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("bad query")),
    )
    with pytest.raises(AppError) as exc_info:
        repository.get_company_roles(
            SimpleNamespace(name="View", description="Read", page=1, limit=10)
        )
    assert (
        exc_info.value.detail["message"]
        == CompanyRoleResponseMessages.ROLE_NOT_FOUND.value
    )

    monkeypatch.setattr(repository, "get_assignment", lambda role_id: None)
    with pytest.raises(AppError) as exc_info:
        repository.ensure_role_assigned(uuid4())
    assert (
        exc_info.value.detail["message"]
        == "Failed to add user to the company. Please verify the input."
    )

    monkeypatch.setattr(repository, "get_assignment", lambda role_id: object())
    assert repository.ensure_role_assigned(uuid4()) is not None

    success_repository = CompanyRoleAssignmentRepository(uuid4(), Mock())
    success_query = Mock()
    success_query.filter.return_value = success_query
    monkeypatch.setattr(
        success_repository.db_session,
        "query",
        lambda model: success_query,
    )
    captured = {}
    monkeypatch.setattr(
        success_repository,
        "paginate",
        lambda query, **kwargs: captured.update(kwargs)
        or {
            "records": [],
            "pagination": {
                "current_page": 1,
                "limit": 10,
                "total_records": 0,
                "total_pages": 0,
            },
        },
    )
    result = success_repository.get_company_roles(
        SimpleNamespace(name="View", description="Read", page=1, limit=10)
    )
    assert result["records"] == []
    assert captured["page"] == 1


def test_company_role_assignment_name_lookup_helpers(monkeypatch):
    repository = CompanyRoleAssignmentRepository(uuid4(), Mock())
    role = _role_model()

    query = Mock()
    query.join.return_value.filter.return_value.one_or_none.return_value = role
    repository.db_session.query.return_value = query
    assert repository.ensure_role_name_assigned("Viewer") is role
    assert repository.get_role_name_assigned("Viewer") is role

    query.join.return_value.filter.return_value.one_or_none.return_value = None
    with pytest.raises(AppError) as exc_info:
        repository.ensure_role_name_assigned("Missing")
    assert (
        exc_info.value.detail["message"]
        == "Failed to add user to the company. Please verify the input."
    )


def test_company_role_assignment_update_company_role_and_assign_role(monkeypatch):
    repository = CompanyRoleAssignmentRepository(uuid4(), Mock())
    repository.db_session.refresh = Mock()
    repository.db_session.rollback = Mock()
    role = _role_model(name="Viewer", description="Old")
    monkeypatch.setattr(repository, "get_role_name_assigned", lambda name: role)
    monkeypatch.setattr(
        RoleRepository,
        "_to_read_model",
        staticmethod(
            lambda role: RoleReadModel(
                id=str(role.id), name=role.name, description=role.description
            )
        ),
    )

    updated = repository.update_company_role(
        "Viewer",
        RoleUpdateModel(name="Viewer+", description="New"),
    )
    assert updated.name == "Viewer+"
    assert updated.description == "New"

    monkeypatch.setattr(repository, "get_role_name_assigned", lambda name: None)
    with pytest.raises(AppError) as exc_info:
        repository.update_company_role(
            "Missing",
            RoleUpdateModel(name=None, description="New"),
        )
    assert (
        exc_info.value.detail["message"]
        == CompanyRoleResponseMessages.ROLE_UPDATE_FAILED.value
    )

    assign_repo = CompanyRoleAssignmentRepository(uuid4(), Mock())
    monkeypatch.setattr(assign_repo, "get_assignment", lambda role_id: None)
    monkeypatch.setattr(assign_repo, "create", lambda **kwargs: SimpleNamespace())
    update_calls = []
    monkeypatch.setattr(
        assign_repo,
        "update_json_field",
        lambda assignment, **kwargs: update_calls.append(kwargs["key"]),
    )
    assigned = assign_repo.assign_role(_role_model(), _acting_user())
    assert assigned.id is not None
    assert update_calls == ["assigned_by"]

    monkeypatch.setattr(assign_repo, "get_assignment", lambda role_id: object())
    with pytest.raises(AppError) as exc_info:
        assign_repo.assign_role(_role_model(), _acting_user())
    assert (
        exc_info.value.detail["message"]
        == CompanyRoleResponseMessages.ROLE_CREATION_FAILED.value
    )


def test_role_repository_get_roles_applies_name_and_description_filters(monkeypatch):
    repository = RoleRepository(session=Mock())
    query = Mock()
    query.filter.return_value = query
    monkeypatch.setattr(repository, "_base_query", lambda: query)
    captured = {}
    monkeypatch.setattr(
        repository,
        "paginate",
        lambda query_obj, **kwargs: captured.update(kwargs)
        or {"records": [], "pagination": {}},
    )

    result = repository.get_roles(
        SimpleNamespace(name="View", description="Read", page=1, limit=10)
    )

    assert result["records"] == []
    assert query.filter.call_count == 3
    assert captured["page"] == 1


def test_company_role_assignment_unassign_role_branches(monkeypatch):
    repository = CompanyRoleAssignmentRepository(uuid4(), Mock())

    monkeypatch.setattr(repository, "get_assignment", lambda role_id: None)
    with pytest.raises(AppError) as exc_info:
        repository.unassign_role(uuid4())
    assert (
        exc_info.value.detail["message"]
        == CompanyRoleResponseMessages.ROLE_NOT_FOUND.value
    )

    assignment = SimpleNamespace(_closed_at=None)
    repository = CompanyRoleAssignmentRepository(uuid4(), Mock())
    repository.db_session.add = Mock()
    repository.db_session.commit = Mock()
    monkeypatch.setattr(repository, "get_assignment", lambda role_id: assignment)
    blocked_query = Mock()
    blocked_query.filter.return_value.count.return_value = 1
    repository.db_session.query.return_value = blocked_query

    with pytest.raises(AppError) as exc_info:
        repository.unassign_role(uuid4())
    assert (
        exc_info.value.detail["message"]
        == CompanyRoleResponseMessages.ROLE_DELETION_FAILED.value
    )

    repository = CompanyRoleAssignmentRepository(uuid4(), Mock())
    repository.db_session.add = Mock()
    repository.db_session.commit = Mock()
    monkeypatch.setattr(repository, "get_assignment", lambda role_id: assignment)
    clear_query = Mock()
    clear_query.filter.return_value.count.return_value = 0
    repository.db_session.query.return_value = clear_query

    result = repository.unassign_role(uuid4())
    assert result == {"message": "Role unassigned successfully."}


def test_company_role_assignment_reassign_and_delete_role_branches(monkeypatch):
    repository = CompanyRoleAssignmentRepository(uuid4(), Mock())
    deleted_by = _acting_user()

    with pytest.raises(AppError) as exc_info:
        repository.reassign_and_delete_role(
            RoleDeleteModel(
                role_name_to_delete="Client",
                replacement_role_name="Client",
            ),
            deleted_by,
        )
    assert (
        exc_info.value.detail["message"]
        == CompanyRoleResponseMessages.ROLE_UPDATE_FAILED.value
    )

    delete_role = _role_model(name="Client")
    monkeypatch.setattr(
        repository,
        "get_role_name_assigned",
        lambda name: delete_role if name == "Client" else None,
    )
    with pytest.raises(AppError) as exc_info:
        repository.reassign_and_delete_role(
            RoleDeleteModel(
                role_name_to_delete="Client",
                replacement_role_name="Viewer",
            ),
            deleted_by,
        )
    assert (
        exc_info.value.detail["message"]
        == CompanyRoleResponseMessages.ROLE_UPDATE_FAILED.value
    )

    replacement_role = _role_model(name="Viewer")
    user_link = SimpleNamespace(role_id=delete_role.id)
    repository = CompanyRoleAssignmentRepository(uuid4(), Mock())
    repository.db_session.add = Mock()
    repository.db_session.commit = Mock()
    repository.db_session.query.return_value.filter.return_value.all.return_value = [
        user_link
    ]
    monkeypatch.setattr(
        repository,
        "get_role_name_assigned",
        lambda name: delete_role if name == "Client" else replacement_role,
    )
    monkeypatch.setattr(repository, "get_assignment", lambda role_id: None)
    with pytest.raises(AppError) as exc_info:
        repository.reassign_and_delete_role(
            RoleDeleteModel(
                role_name_to_delete="Client",
                replacement_role_name="Viewer",
            ),
            deleted_by,
        )
    assert (
        exc_info.value.detail["message"]
        == CompanyRoleResponseMessages.ROLE_UPDATE_FAILED.value
    )
    assert user_link.role_id == replacement_role.id
