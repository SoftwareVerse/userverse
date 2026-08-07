from uuid import uuid4

import pytest

from app.repository.database import session_manager
from app.repository.database.tables import CompanyRole, Role, User

pytestmark = pytest.mark.anyio


def _user_id(email: str):
    session = session_manager.session_local()
    try:
        return session.query(User).filter_by(email=email).one().id
    finally:
        session.close()


def _role_id(company_id, name: str):
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


async def test_hybrid_global_company_and_platform_permissions(
    client,
    login_token,
    login_token_user_two,
    login_token_superuser,
    seed_companies,
):
    suffix = uuid4().hex
    super_headers = {"Authorization": f"Bearer {login_token_superuser}"}
    company_one_headers = {"Authorization": f"Bearer {login_token}"}
    company_two_headers = {"Authorization": f"Bearer {login_token_user_two}"}
    company_one = seed_companies["company_one"]
    company_two = seed_companies["company_two"]

    role_response = await client.post(
        "/roles",
        json={
            "name": f"Hybrid Manager {suffix}",
            "description": "Hybrid permission test role",
        },
        headers=super_headers,
    )
    assert role_response.status_code == 201, role_response.text
    role_id = role_response.json()["data"]["id"]

    global_response = await client.post(
        "/permissions",
        json={
            "name": f"app.dashboard.view.{suffix}",
            "description": "View the platform dashboard",
        },
        headers=super_headers,
    )
    assert global_response.status_code == 201, global_response.text
    global_permission = global_response.json()["data"]
    assert global_permission["scope"] == "global"
    assert global_permission["company_id"] is None

    forbidden_global = await client.post(
        "/permissions",
        json={"name": f"app.forbidden.{suffix}"},
        headers=company_one_headers,
    )
    assert forbidden_global.status_code == 403

    assigned_global = await client.post(
        f"/roles/{role_id}/permissions/{global_permission['id']}",
        headers=super_headers,
    )
    assert assigned_global.status_code == 201, assigned_global.text
    assert assigned_global.json()["data"]["permissions"] == [global_permission]
    global_role_permissions = await client.get(
        f"/roles/{role_id}/permissions",
        headers=super_headers,
    )
    assert global_role_permissions.status_code == 200
    assert global_role_permissions.json()["data"] == [global_permission]
    global_role_list = await client.get(
        "/roles",
        params={"name": f"Hybrid Manager {suffix}"},
        headers=super_headers,
    )
    assert global_role_list.status_code == 200
    assert global_role_list.json()["data"]["records"][0]["permissions"] == [
        global_permission
    ]
    duplicate_global_assignment = await client.post(
        f"/roles/{role_id}/permissions/{global_permission['id']}",
        headers=super_headers,
    )
    assert duplicate_global_assignment.status_code == 409

    for company_id, headers in (
        (company_one, company_one_headers),
        (company_two, company_two_headers),
    ):
        response = await client.post(
            f"/company/{company_id}/roles/{role_id}",
            headers=headers,
        )
        assert response.status_code == 201, response.text
        assert response.json()["data"]["permissions"] == [global_permission]

    company_one_permission_response = await client.post(
        f"/company/{company_one}/permissions",
        json={
            "name": f"invoice.approve.{suffix}",
            "description": "Approve invoices for company one",
        },
        headers=company_one_headers,
    )
    assert company_one_permission_response.status_code == 201
    company_one_permission = company_one_permission_response.json()["data"]
    assert company_one_permission["scope"] == "company"
    assert company_one_permission["company_id"] == str(company_one)

    company_two_permission_response = await client.post(
        f"/company/{company_two}/permissions",
        json={
            "name": f"invoice.approve.{suffix}",
            "description": "Same tenant-local name for company two",
        },
        headers=company_two_headers,
    )
    assert company_two_permission_response.status_code == 201
    company_two_permission = company_two_permission_response.json()["data"]

    cross_tenant = await client.post(
        (
            f"/company/{company_one}/roles/{role_id}/permissions/"
            f"{company_two_permission['id']}"
        ),
        headers=company_one_headers,
    )
    assert cross_tenant.status_code == 404

    local_assignment = await client.post(
        (
            f"/company/{company_one}/roles/{role_id}/permissions/"
            f"{company_one_permission['id']}"
        ),
        headers=company_one_headers,
    )
    assert local_assignment.status_code == 201, local_assignment.text
    assert {
        item["scope"] for item in local_assignment.json()["data"]["permissions"]
    } == {
        "global",
        "company",
    }
    duplicate_local_assignment = await client.post(
        (
            f"/company/{company_one}/roles/{role_id}/permissions/"
            f"{company_one_permission['id']}"
        ),
        headers=company_one_headers,
    )
    assert duplicate_local_assignment.status_code == 409
    removed_local_assignment = await client.delete(
        (
            f"/company/{company_one}/roles/{role_id}/permissions/"
            f"{company_one_permission['id']}"
        ),
        headers=company_one_headers,
    )
    assert removed_local_assignment.status_code == 200
    assert removed_local_assignment.json()["data"]["permissions"] == [global_permission]
    reassigned_local = await client.post(
        (
            f"/company/{company_one}/roles/{role_id}/permissions/"
            f"{company_one_permission['id']}"
        ),
        headers=company_one_headers,
    )
    assert reassigned_local.status_code == 201

    owner_role_id = _role_id(company_one, "Owner")
    owner_global_assignment = await client.post(
        f"/roles/{owner_role_id}/permissions/{global_permission['id']}",
        headers=super_headers,
    )
    assert owner_global_assignment.status_code == 201
    owner_local_assignment = await client.post(
        (
            f"/company/{company_one}/roles/{owner_role_id}/permissions/"
            f"{company_one_permission['id']}"
        ),
        headers=company_one_headers,
    )
    assert owner_local_assignment.status_code == 201

    user_companies = await client.get(
        "/user/companies?limit=10&page=1",
        headers=company_one_headers,
    )
    company_record = next(
        record
        for record in user_companies.json()["data"]["records"]
        if record["id"] == str(company_one)
    )
    assert {item["id"] for item in company_record["role"]["permissions"]} == {
        global_permission["id"],
        company_one_permission["id"],
    }

    company_users = await client.get(
        f"/company/{company_one}/users?limit=10&page=1",
        headers=company_one_headers,
    )
    owner_record = next(
        record
        for record in company_users.json()["data"]["records"]
        if record["email"] == "user.one@email.com"
    )
    assert {item["id"] for item in owner_record["role"]["permissions"]} == {
        global_permission["id"],
        company_one_permission["id"],
    }

    await client.delete(
        f"/roles/{owner_role_id}/permissions/{global_permission['id']}",
        headers=super_headers,
    )
    await client.delete(
        (
            f"/company/{company_one}/roles/{owner_role_id}/permissions/"
            f"{company_one_permission['id']}"
        ),
        headers=company_one_headers,
    )

    company_two_effective = await client.get(
        f"/company/{company_two}/roles/{role_id}/permissions",
        headers=company_two_headers,
    )
    assert company_two_effective.status_code == 200
    assert company_two_effective.json()["data"] == [global_permission]

    user_id = _user_id("user.one@email.com")
    platform_assignment = await client.post(
        f"/users/{user_id}/roles/{role_id}",
        headers=super_headers,
    )
    assert platform_assignment.status_code == 201, platform_assignment.text
    assert platform_assignment.json()["data"][0]["permissions"] == [global_permission]
    platform_roles = await client.get(
        f"/users/{user_id}/roles",
        headers=super_headers,
    )
    assert platform_roles.status_code == 200
    assert platform_roles.json()["data"] == platform_assignment.json()["data"]
    duplicate_platform_assignment = await client.post(
        f"/users/{user_id}/roles/{role_id}",
        headers=super_headers,
    )
    assert duplicate_platform_assignment.status_code == 409

    blocked_role_delete = await client.delete(
        f"/roles/{role_id}",
        headers=super_headers,
    )
    assert blocked_role_delete.status_code == 400

    self_permissions = await client.get(
        "/user/permissions",
        headers=company_one_headers,
    )
    assert self_permissions.status_code == 200, self_permissions.text
    assert global_permission in self_permissions.json()["data"]
    assert company_one_permission not in self_permissions.json()["data"]

    no_membership_grant = await client.get(
        f"/company/{company_two}/permissions",
        headers=company_one_headers,
    )
    assert no_membership_grant.status_code == 403

    deleted = await client.delete(
        f"/company/{company_one}/permissions/{company_one_permission['id']}",
        headers=company_one_headers,
    )
    assert deleted.status_code == 200
    after_delete = await client.get(
        f"/company/{company_one}/roles/{role_id}/permissions",
        headers=company_one_headers,
    )
    assert after_delete.json()["data"] == [global_permission]

    recreated = await client.post(
        f"/company/{company_one}/permissions",
        json={"name": company_one_permission["name"]},
        headers=company_one_headers,
    )
    assert recreated.status_code == 201
    assert recreated.json()["data"]["id"] != company_one_permission["id"]

    removed_platform_role = await client.delete(
        f"/users/{user_id}/roles/{role_id}",
        headers=super_headers,
    )
    assert removed_platform_role.status_code == 200
    self_permissions_after_removal = await client.get(
        "/user/permissions",
        headers=company_one_headers,
    )
    assert global_permission not in self_permissions_after_removal.json()["data"]


async def test_duplicate_permission_and_assignment_conflicts(
    client,
    login_token_superuser,
):
    suffix = uuid4().hex
    headers = {"Authorization": f"Bearer {login_token_superuser}"}
    payload = {"name": f"app.duplicate.{suffix}"}

    created = await client.post("/permissions", json=payload, headers=headers)
    duplicate = await client.post("/permissions", json=payload, headers=headers)

    assert created.status_code == 201
    assert duplicate.status_code == 409

    permission_id = created.json()["data"]["id"]
    listed = await client.get(
        f"/permissions?name={suffix}&limit=1&page=1",
        headers=headers,
    )
    assert listed.status_code == 200
    assert listed.json()["data"]["pagination"]["total_records"] == 1
    assert listed.json()["data"]["records"][0]["id"] == permission_id

    updated = await client.patch(
        f"/permissions/{permission_id}",
        json={"description": "Updated global permission"},
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["data"]["description"] == "Updated global permission"

    cleared = await client.patch(
        f"/permissions/{permission_id}",
        json={"description": None},
        headers=headers,
    )
    assert cleared.status_code == 200
    assert cleared.json()["data"]["description"] is None

    empty_update = await client.patch(
        f"/permissions/{permission_id}",
        json={},
        headers=headers,
    )
    assert empty_update.status_code == 422

    deleted = await client.delete(
        f"/permissions/{permission_id}",
        headers=headers,
    )
    assert deleted.status_code == 200
    recreated = await client.post("/permissions", json=payload, headers=headers)
    assert recreated.status_code == 201
    assert recreated.json()["data"]["id"] != permission_id


async def test_inactive_users_cannot_receive_platform_roles(
    client,
    login_token_superuser,
    seed_verified_users,
    test_user_data,
):
    suffix = uuid4().hex
    headers = {"Authorization": f"Bearer {login_token_superuser}"}
    role_response = await client.post(
        "/roles",
        json={"name": f"Inactive Assignment {suffix}", "description": None},
        headers=headers,
    )
    assert role_response.status_code == 201
    role_id = role_response.json()["data"]["id"]

    email = test_user_data["user_three"]["email"]
    user_id = _user_id(email)
    session = session_manager.session_local()
    try:
        user = session.query(User).filter_by(id=user_id).one()
        metadata = dict(user.primary_meta_data or {})
        metadata["status"] = "Suspended"
        user.primary_meta_data = metadata
        session.commit()
    finally:
        session.close()

    try:
        response = await client.post(
            f"/users/{user_id}/roles/{role_id}",
            headers=headers,
        )
        assert response.status_code == 404
    finally:
        session = session_manager.session_local()
        try:
            user = session.query(User).filter_by(id=user_id).one()
            metadata = dict(user.primary_meta_data or {})
            metadata["status"] = "Active"
            user.primary_meta_data = metadata
            session.commit()
        finally:
            session.close()


async def test_permission_management_edge_cases(
    client,
    login_token,
    login_token_superuser,
    seed_companies,
):
    suffix = uuid4().hex
    super_headers = {"Authorization": f"Bearer {login_token_superuser}"}
    company_headers = {"Authorization": f"Bearer {login_token}"}
    company_id = seed_companies["company_one"]

    blank_create = await client.post(
        "/permissions",
        json={"name": "   "},
        headers=super_headers,
    )
    assert blank_create.status_code == 422

    first_global = await client.post(
        "/permissions",
        json={
            "name": f"  app.edge.first.{suffix}  ",
            "description": f"Global edge description {suffix}",
        },
        headers=super_headers,
    )
    second_global = await client.post(
        "/permissions",
        json={"name": f"app.edge.second.{suffix}"},
        headers=super_headers,
    )
    assert first_global.status_code == 201
    assert second_global.status_code == 201
    first_global_permission = first_global.json()["data"]
    second_global_permission = second_global.json()["data"]
    assert first_global_permission["name"] == f"app.edge.first.{suffix}"

    global_description_filter = await client.get(
        "/permissions",
        params={"description": suffix, "limit": 10, "page": 1},
        headers=super_headers,
    )
    assert global_description_filter.status_code == 200
    assert [
        record["id"] for record in global_description_filter.json()["data"]["records"]
    ] == [first_global_permission["id"]]

    null_name = await client.patch(
        f"/permissions/{first_global_permission['id']}",
        json={"name": None},
        headers=super_headers,
    )
    blank_name = await client.patch(
        f"/permissions/{first_global_permission['id']}",
        json={"name": "   "},
        headers=super_headers,
    )
    assert null_name.status_code == 422
    assert blank_name.status_code == 422

    renamed_global = await client.patch(
        f"/permissions/{second_global_permission['id']}",
        json={"name": f"app.edge.renamed.{suffix}"},
        headers=super_headers,
    )
    assert renamed_global.status_code == 200
    assert renamed_global.json()["data"]["name"] == f"app.edge.renamed.{suffix}"

    global_rename_conflict = await client.patch(
        f"/permissions/{second_global_permission['id']}",
        json={"name": first_global_permission["name"]},
        headers=super_headers,
    )
    assert global_rename_conflict.status_code == 409

    missing_global_permission = await client.patch(
        f"/permissions/{uuid4()}",
        json={"description": "missing"},
        headers=super_headers,
    )
    assert missing_global_permission.status_code == 404

    first_company = await client.post(
        f"/company/{company_id}/permissions",
        json={
            "name": f"  invoice.edge.first.{suffix}  ",
            "description": f"Company edge description {suffix}",
        },
        headers=company_headers,
    )
    second_company = await client.post(
        f"/company/{company_id}/permissions",
        json={"name": f"invoice.edge.second.{suffix}"},
        headers=company_headers,
    )
    assert first_company.status_code == 201
    assert second_company.status_code == 201
    first_company_permission = first_company.json()["data"]
    second_company_permission = second_company.json()["data"]
    assert first_company_permission["name"] == f"invoice.edge.first.{suffix}"

    duplicate_company = await client.post(
        f"/company/{company_id}/permissions",
        json={"name": first_company_permission["name"]},
        headers=company_headers,
    )
    assert duplicate_company.status_code == 409

    company_permissions = await client.get(
        f"/company/{company_id}/permissions",
        params={"description": suffix, "limit": 10, "page": 1},
        headers=company_headers,
    )
    assert company_permissions.status_code == 200
    assert [
        record["id"] for record in company_permissions.json()["data"]["records"]
    ] == [first_company_permission["id"]]

    superuser_company_permissions = await client.get(
        f"/company/{company_id}/permissions",
        params={"name": f"invoice.edge.first.{suffix}"},
        headers=super_headers,
    )
    assert superuser_company_permissions.status_code == 200

    renamed_company = await client.patch(
        f"/company/{company_id}/permissions/{second_company_permission['id']}",
        json={
            "name": f"invoice.edge.renamed.{suffix}",
            "description": "Renamed company permission",
        },
        headers=company_headers,
    )
    assert renamed_company.status_code == 200
    assert renamed_company.json()["data"]["name"] == f"invoice.edge.renamed.{suffix}"

    company_rename_conflict = await client.patch(
        f"/company/{company_id}/permissions/{second_company_permission['id']}",
        json={"name": first_company_permission["name"]},
        headers=company_headers,
    )
    assert company_rename_conflict.status_code == 409

    missing_company_permission = await client.patch(
        f"/company/{company_id}/permissions/{uuid4()}",
        json={"description": "missing"},
        headers=company_headers,
    )
    assert missing_company_permission.status_code == 404

    missing_company = await client.get(
        f"/company/{uuid4()}/permissions",
        headers=super_headers,
    )
    assert missing_company.status_code == 404

    role_response = await client.post(
        "/roles",
        json={"name": f"Permission Edge Role {suffix}", "description": None},
        headers=super_headers,
    )
    unassigned_role_response = await client.post(
        "/roles",
        json={"name": f"Unassigned Edge Role {suffix}", "description": None},
        headers=super_headers,
    )
    assert role_response.status_code == 201
    assert unassigned_role_response.status_code == 201
    role_id = role_response.json()["data"]["id"]
    unassigned_role_id = unassigned_role_response.json()["data"]["id"]

    assigned_role = await client.post(
        f"/company/{company_id}/roles/{role_id}",
        headers=company_headers,
    )
    assert assigned_role.status_code == 201

    missing_global_role = await client.get(
        f"/roles/{uuid4()}/permissions",
        headers=super_headers,
    )
    missing_company_role = await client.get(
        f"/company/{company_id}/roles/{unassigned_role_id}/permissions",
        headers=company_headers,
    )
    assert missing_global_role.status_code == 404
    assert missing_company_role.status_code == 404

    remove_missing_global_link = await client.delete(
        f"/roles/{role_id}/permissions/{first_global_permission['id']}",
        headers=super_headers,
    )
    remove_missing_company_link = await client.delete(
        (
            f"/company/{company_id}/roles/{role_id}/permissions/"
            f"{first_company_permission['id']}"
        ),
        headers=company_headers,
    )
    assert remove_missing_global_link.status_code == 404
    assert remove_missing_company_link.status_code == 404

    user_id = _user_id("user.one@email.com")
    remove_missing_platform_link = await client.delete(
        f"/users/{user_id}/roles/{role_id}",
        headers=super_headers,
    )
    assert remove_missing_platform_link.status_code == 404
