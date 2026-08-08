from uuid import UUID, uuid4

import pytest

from app.models.system_permissions import SYSTEM_PERMISSION_BY_ID, SystemPermission
from app.repository.database import session_manager
from app.repository.database.tables import CompanyRole, Role, User

pytestmark = pytest.mark.anyio


def _user_id(email: str):
    session = session_manager.session_local()
    try:
        return session.query(User.id).filter_by(email=email.lower()).scalar()
    finally:
        session.close()


def _company_role_id(company_id, name: str):
    company_id = UUID(str(company_id))
    session = session_manager.session_local()
    try:
        return (
            session.query(Role.id)
            .join(CompanyRole, CompanyRole.role_id == Role.id)
            .filter(
                CompanyRole.company_id == company_id,
                CompanyRole._closed_at.is_(None),
                Role.name == name,
                Role._closed_at.is_(None),
            )
            .scalar()
        )
    finally:
        session.close()


async def test_default_role_endpoint_matrix_and_superuser_bypass(
    client,
    login_token,
    login_token_user_two,
    login_token_superuser,
    seed_verified_users,
    test_company_data,
    test_global_rbac_data,
):
    suffix = uuid4().hex
    owner_headers = {"Authorization": f"Bearer {login_token}"}
    member_headers = {"Authorization": f"Bearer {login_token_user_two}"}
    super_headers = {"Authorization": f"Bearer {login_token_superuser}"}
    rbac_company = test_company_data["rbac_company"]
    company_payload = {
        **test_company_data["company_one"],
        "name": f"{rbac_company['name']} {suffix}",
        "email": f"{rbac_company['email_prefix']}-{suffix}@example.com",
        "description": rbac_company["description"],
        "address": test_company_data["json_field"]["value"],
    }
    created_company = await client.post(
        "/company",
        json=company_payload,
        headers=owner_headers,
    )
    assert created_company.status_code == 201, created_company.text
    company_id = created_company.json()["data"]["id"]
    user_two_id = _user_id("user.two@email.com")
    user_three_id = _user_id("user.three@email.com")

    added_viewer = await client.post(
        f"/company/{company_id}/users",
        json={"email": "user.two@email.com", "role": "Viewer"},
        headers=owner_headers,
    )
    assert added_viewer.status_code == 201, added_viewer.text

    viewer_allowed_requests = (
        ("get", "/company", {"params": {"company_id": company_id}}),
        ("get", f"/company/{company_id}/users", {}),
    )
    for method, path, kwargs in viewer_allowed_requests:
        response = await getattr(client, method)(path, headers=member_headers, **kwargs)
        assert response.status_code == 200, response.text

    missing_id = uuid4()
    matrix_permission = test_company_data["permissions"]["matrix_permission"]
    matrix_permission_name = f"{matrix_permission['name']}.{suffix}"
    viewer_denied_requests = (
        ("patch", f"/company/{company_id}", {"json": {"description": "Denied"}}),
        ("delete", f"/company/{company_id}", {}),
        (
            "post",
            f"/company/{company_id}/users",
            {"json": {"email": "user.three@email.com", "role": "Viewer"}},
        ),
        (
            "patch",
            f"/company/{company_id}/user/{user_two_id}",
            {"json": {"role": "Administrator"}},
        ),
        ("delete", f"/company/{company_id}/user/{user_two_id}", {}),
        ("get", f"/company/{company_id}/roles", {}),
        ("post", f"/company/{company_id}/roles/{missing_id}", {}),
        ("delete", f"/company/{company_id}/roles/{missing_id}", {}),
        (
            "post",
            f"/company/{company_id}/permissions",
            {"json": {"name": matrix_permission_name}},
        ),
        ("get", f"/company/{company_id}/permissions", {}),
        (
            "patch",
            f"/company/{company_id}/permissions/{missing_id}",
            {"json": {"description": "Denied"}},
        ),
        ("delete", f"/company/{company_id}/permissions/{missing_id}", {}),
        (
            "get",
            f"/company/{company_id}/roles/{missing_id}/permissions",
            {},
        ),
        (
            "post",
            f"/company/{company_id}/roles/{missing_id}/permissions/{missing_id}",
            {},
        ),
        (
            "delete",
            f"/company/{company_id}/roles/{missing_id}/permissions/{missing_id}",
            {},
        ),
    )
    for method, path, kwargs in viewer_denied_requests:
        response = await getattr(client, method)(path, headers=member_headers, **kwargs)
        assert response.status_code == 403, (method, path, response.text)

    promoted = await client.patch(
        f"/company/{company_id}/user/{user_two_id}",
        json={"role": "Administrator"},
        headers=owner_headers,
    )
    assert promoted.status_code == 200, promoted.text

    company_read = await client.get(
        "/company",
        params={"company_id": company_id},
        headers=member_headers,
    )
    company_update = await client.patch(
        f"/company/{company_id}",
        json={"description": "Managed by Administrator"},
        headers=member_headers,
    )
    members_read = await client.get(
        f"/company/{company_id}/users",
        headers=member_headers,
    )
    assert company_read.status_code == 200
    assert company_update.status_code == 200
    assert members_read.status_code == 200

    added_member = await client.post(
        f"/company/{company_id}/users",
        json={"email": "user.three@email.com", "role": "Viewer"},
        headers=member_headers,
    )
    assert added_member.status_code == 201, added_member.text
    updated_member = await client.patch(
        f"/company/{company_id}/user/{user_three_id}",
        json={"role": "Administrator"},
        headers=member_headers,
    )
    assert updated_member.status_code == 200, updated_member.text
    removed_member = await client.delete(
        f"/company/{company_id}/user/{user_three_id}",
        headers=member_headers,
    )
    assert removed_member.status_code == 200, removed_member.text

    roles_read = await client.get(
        f"/company/{company_id}/roles",
        headers=member_headers,
    )
    assert roles_read.status_code == 200, roles_read.text
    matrix_role = test_global_rbac_data["roles"]["matrix_role"]
    global_role = await client.post(
        "/roles",
        json={
            **matrix_role,
            "name": f"{matrix_role['name']} {suffix}",
        },
        headers=super_headers,
    )
    assert global_role.status_code == 201, global_role.text
    role_id = global_role.json()["data"]["id"]
    assigned_role = await client.post(
        f"/company/{company_id}/roles/{role_id}",
        headers=member_headers,
    )
    assert assigned_role.status_code == 201, assigned_role.text
    unassigned_role = await client.delete(
        f"/company/{company_id}/roles/{role_id}",
        headers=member_headers,
    )
    assert unassigned_role.status_code == 200, unassigned_role.text

    created_permission = await client.post(
        f"/company/{company_id}/permissions",
        json={
            **matrix_permission,
            "name": matrix_permission_name,
        },
        headers=member_headers,
    )
    assert created_permission.status_code == 201, created_permission.text
    permission_id = created_permission.json()["data"]["id"]
    listed_permissions = await client.get(
        f"/company/{company_id}/permissions",
        headers=member_headers,
    )
    updated_permission = await client.patch(
        f"/company/{company_id}/permissions/{permission_id}",
        json={"description": "Updated by Administrator"},
        headers=member_headers,
    )
    assert listed_permissions.status_code == 200
    assert updated_permission.status_code == 200

    viewer_role_id = _company_role_id(company_id, "Viewer")
    assigned_permission = await client.post(
        (
            f"/company/{company_id}/roles/{viewer_role_id}/permissions/"
            f"{permission_id}"
        ),
        headers=member_headers,
    )
    assert assigned_permission.status_code == 201, assigned_permission.text
    effective_permissions = await client.get(
        f"/company/{company_id}/roles/{viewer_role_id}/permissions",
        headers=member_headers,
    )
    assert effective_permissions.status_code == 200, effective_permissions.text
    removed_permission_link = await client.delete(
        (
            f"/company/{company_id}/roles/{viewer_role_id}/permissions/"
            f"{permission_id}"
        ),
        headers=member_headers,
    )
    assert removed_permission_link.status_code == 200, removed_permission_link.text
    deleted_permission = await client.delete(
        f"/company/{company_id}/permissions/{permission_id}",
        headers=member_headers,
    )
    assert deleted_permission.status_code == 200, deleted_permission.text

    administrator_delete = await client.delete(
        f"/company/{company_id}",
        headers=member_headers,
    )
    assert administrator_delete.status_code == 403

    for path in (
        f"/company?company_id={company_id}",
        f"/company/{company_id}/users",
        f"/company/{company_id}/roles",
        f"/company/{company_id}/permissions",
    ):
        superuser_response = await client.get(path, headers=super_headers)
        assert superuser_response.status_code == 200, superuser_response.text

    owner_delete = await client.delete(
        f"/company/{company_id}",
        headers=owner_headers,
    )
    assert owner_delete.status_code == 200, owner_delete.text


async def test_system_permissions_allow_description_only_updates(
    client,
    login_token,
    login_token_superuser,
    seed_companies,
    test_company_data,
):
    super_headers = {"Authorization": f"Bearer {login_token_superuser}"}
    permission_id = SystemPermission.COMPANY_READ.permission_id

    updated = await client.patch(
        f"/permissions/{permission_id}",
        json={"description": "Updated system permission description"},
        headers=super_headers,
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["data"]["name"] == SystemPermission.COMPANY_READ.value

    unchanged_name = await client.patch(
        f"/permissions/{permission_id}",
        json={"name": SystemPermission.COMPANY_READ.value},
        headers=super_headers,
    )
    assert unchanged_name.status_code == 200, unchanged_name.text

    renamed = await client.patch(
        f"/permissions/{permission_id}",
        json={"name": "company.read.renamed"},
        headers=super_headers,
    )
    deleted = await client.delete(
        f"/permissions/{permission_id}",
        headers=super_headers,
    )
    assert renamed.status_code == 409
    assert deleted.status_code == 409

    restored = await client.patch(
        f"/permissions/{permission_id}",
        json={"description": SYSTEM_PERMISSION_BY_ID[permission_id].description},
        headers=super_headers,
    )
    assert restored.status_code == 200, restored.text

    collision_permission = test_company_data["permissions"]["system_name_collision"]
    tenant_same_name = await client.post(
        f"/company/{seed_companies['company_one']}/permissions",
        json=collision_permission,
        headers={"Authorization": f"Bearer {login_token}"},
    )
    assert tenant_same_name.status_code == 201, tenant_same_name.text
    assert tenant_same_name.json()["data"]["scope"] == "company"
    assert tenant_same_name.json()["data"]["name"] == collision_permission["name"]
