from uuid import uuid4

import pytest

from app.models.system_permissions import (
    SYSTEM_PERMISSION_BY_ID,
    SYSTEM_PERMISSION_DEFINITIONS,
    SystemPermission,
)
from app.models.user.account_status import UserAccountStatus
from app.models.user.user import UserReadModel
from app.repository.company import CompanyRepository
from app.repository.database.tables import (
    AssociationUserCompany,
    Company,
    CompanyPermission,
    CompanyRole,
    CompanyRolePermission,
    GlobalPermission,
    Role,
    RoleGlobalPermission,
    User,
    UserRole,
)
from app.repository.permission import SystemPermissionRepository
from app.services.company.authorization import CompanyAuthorizationService
from app.utils.app_error import AppError
from app.utils.shared_context import SharedContext


def _user_model(user: User, *, is_superuser: bool = False) -> UserReadModel:
    return UserReadModel(
        id=user.id,
        email=user.email,
        first_name=user.first_name,
        status=UserAccountStatus.ACTIVE.name_value,
        is_superuser=is_superuser,
    )


def _create_user(test_session, label: str) -> User:
    user = User(
        email=f"{label}-{uuid4().hex}@example.com",
        password="secret",
        first_name=label,
        primary_meta_data={"status": UserAccountStatus.ACTIVE.name_value},
    )
    test_session.add(user)
    test_session.flush()
    return user


def test_default_roles_receive_exact_system_permission_matrix(test_session):
    repository = CompanyRepository(test_session)

    roles = repository._ensure_default_roles()

    permissions = test_session.query(GlobalPermission).all()
    assert {permission.id for permission in permissions} == set(SYSTEM_PERMISSION_BY_ID)
    assert all(permission.primary_meta_data["system"] for permission in permissions)

    for role_name, role in roles.items():
        actual_ids = {
            permission_id
            for (permission_id,) in test_session.query(
                RoleGlobalPermission.global_permission_id
            )
            .filter(RoleGlobalPermission.role_id == role.id)
            .all()
        }
        expected_ids = {
            definition.id
            for definition in SYSTEM_PERMISSION_DEFINITIONS
            if role_name in definition.default_roles
        }
        assert actual_ids == expected_ids

    removed = (
        test_session.query(RoleGlobalPermission)
        .filter_by(
            role_id=roles["Owner"].id,
            global_permission_id=SystemPermission.COMPANY_DELETE.permission_id,
        )
        .one()
    )
    test_session.delete(removed)
    test_session.commit()

    repository._ensure_default_roles()

    assert (
        test_session.query(RoleGlobalPermission)
        .filter_by(
            role_id=roles["Owner"].id,
            global_permission_id=SystemPermission.COMPANY_DELETE.permission_id,
        )
        .one_or_none()
        is None
    )


def test_system_permission_seeder_rejects_reserved_identity_conflicts(test_session):
    conflicting = GlobalPermission(
        name=SystemPermission.COMPANY_READ.value,
        description="Conflicting tenant-created global permission",
    )
    test_session.add(conflicting)
    test_session.commit()

    with pytest.raises(AppError) as exc_info:
        SystemPermissionRepository(test_session).ensure_permissions()

    assert exc_info.value.status_code == 409


def test_system_permission_definition_resolution_covers_exact_and_duplicate_records(
    test_session,
):
    definition = SYSTEM_PERMISSION_DEFINITIONS[0]
    exact = GlobalPermission(
        id=definition.id,
        name=definition.name,
        description=definition.description,
    )

    assert SystemPermissionRepository._resolve_definition(definition, [exact]) is exact
    with pytest.raises(AppError) as exc_info:
        SystemPermissionRepository._resolve_definition(definition, [exact, exact])
    assert exc_info.value.status_code == 409


def test_company_authorization_uses_exact_global_permission_identity(test_session):
    company = Company(
        name="Authorization Company",
        email=f"authorization-{uuid4().hex}@example.com",
    )
    test_session.add(company)
    test_session.flush()
    roles = CompanyRepository(test_session)._ensure_default_roles()
    for role in roles.values():
        test_session.add(CompanyRole(company_id=company.id, role_id=role.id))

    users_by_role = {}
    for role_name, role in roles.items():
        user = _create_user(test_session, role_name.lower())
        users_by_role[role_name] = user
        test_session.add(
            AssociationUserCompany(
                user_id=user.id,
                company_id=company.id,
                role_id=role.id,
            )
        )
    test_session.commit()

    for role_name, user in users_by_role.items():
        authorization = CompanyAuthorizationService(
            SharedContext(db_session=test_session, user=_user_model(user))
        )
        expected_permissions = {
            definition.permission
            for definition in SYSTEM_PERMISSION_DEFINITIONS
            if role_name in definition.default_roles
        }
        for permission in SystemPermission:
            if permission in expected_permissions:
                authorization.require(company.id, permission)
            else:
                with pytest.raises(AppError) as exc_info:
                    authorization.require(company.id, permission)
                assert exc_info.value.status_code == 403

    viewer = users_by_role["Viewer"]
    viewer_role = roles["Viewer"]
    local_delete = CompanyPermission(
        company_id=company.id,
        name=SystemPermission.COMPANY_DELETE.value,
        description="Same name, company scope",
    )
    test_session.add(local_delete)
    test_session.flush()
    test_session.add(
        CompanyRolePermission(
            company_id=company.id,
            role_id=viewer_role.id,
            company_permission_id=local_delete.id,
        )
    )
    test_session.commit()

    viewer_authorization = CompanyAuthorizationService(
        SharedContext(db_session=test_session, user=_user_model(viewer))
    )
    with pytest.raises(AppError):
        viewer_authorization.require(company.id, SystemPermission.COMPANY_DELETE)

    outsider = _create_user(test_session, "platform-outsider")
    test_session.add(UserRole(user_id=outsider.id, role_id=roles["Owner"].id))
    test_session.commit()
    outsider_authorization = CompanyAuthorizationService(
        SharedContext(db_session=test_session, user=_user_model(outsider))
    )
    with pytest.raises(AppError):
        outsider_authorization.require(company.id, SystemPermission.COMPANY_READ)

    custom_role = Role(name=f"Custom Manager {uuid4().hex}", description=None)
    custom_user = _create_user(test_session, "custom-manager")
    test_session.add(custom_role)
    test_session.flush()
    test_session.add_all(
        [
            CompanyRole(company_id=company.id, role_id=custom_role.id),
            RoleGlobalPermission(
                role_id=custom_role.id,
                global_permission_id=SystemPermission.COMPANY_UPDATE.permission_id,
            ),
            AssociationUserCompany(
                user_id=custom_user.id,
                company_id=company.id,
                role_id=custom_role.id,
            ),
        ]
    )
    test_session.commit()
    CompanyAuthorizationService(
        SharedContext(db_session=test_session, user=_user_model(custom_user))
    ).require(company.id, SystemPermission.COMPANY_UPDATE)

    owner = users_by_role["Owner"]
    owner_authorization = CompanyAuthorizationService(
        SharedContext(db_session=test_session, user=_user_model(owner))
    )
    owner_authorization.require(company.id, SystemPermission.COMPANY_DELETE)
    owner_delete_link = (
        test_session.query(RoleGlobalPermission)
        .filter_by(
            role_id=roles["Owner"].id,
            global_permission_id=SystemPermission.COMPANY_DELETE.permission_id,
        )
        .one()
    )
    test_session.delete(owner_delete_link)
    test_session.commit()
    with pytest.raises(AppError):
        owner_authorization.require(company.id, SystemPermission.COMPANY_DELETE)

    superuser = _create_user(test_session, "superuser")
    CompanyAuthorizationService(
        SharedContext(
            db_session=test_session,
            user=_user_model(superuser, is_superuser=True),
        )
    ).require(uuid4(), SystemPermission.COMPANY_DELETE)
