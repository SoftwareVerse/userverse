from uuid import uuid4

import pytest

from app.models.company.response_messages import (
    CompanyResponseMessages,
    CompanyRoleResponseMessages,
)

pytestmark = pytest.mark.anyio


def _role_payload() -> dict:
    suffix = uuid4().hex
    return {
        "name": f"Global Role {suffix}",
        "description": f"Global role description {suffix}",
    }


async def _create_global_role(client, token: str, payload: dict) -> dict:
    response = await client.post(
        "/roles",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]


async def test_superuser_can_manage_global_roles_and_bulk_assign(
    client, login_token_superuser, seed_companies
):
    payload = _role_payload()
    created = await _create_global_role(client, login_token_superuser, payload)
    role_id = created["id"]
    headers = {"Authorization": f"Bearer {login_token_superuser}"}

    update_response = await client.patch(
        f"/roles/{role_id}",
        json={
            "name": f"{payload['name']} Updated",
            "description": f"{payload['description']} Updated",
        },
        headers=headers,
    )
    assert update_response.status_code == 200, update_response.text
    assert update_response.json()["message"] == CompanyRoleResponseMessages.ROLE_UPDATED.value

    assign_response = await client.post(
        f"/roles/{role_id}/companies",
        json={
            "company_ids": [
                str(seed_companies["company_one"]),
                str(seed_companies["company_two"]),
            ]
        },
        headers=headers,
    )
    assert assign_response.status_code == 201, assign_response.text
    assert assign_response.json()["message"] == CompanyRoleResponseMessages.ROLE_CREATION_SUCCESS.value
    assert assign_response.json()["data"]["company_ids"] == [
        str(seed_companies["company_one"]),
        str(seed_companies["company_two"]),
    ]

    delete_response = await client.delete(
        f"/roles/{role_id}",
        headers=headers,
    )
    assert delete_response.status_code == 200, delete_response.text
    assert delete_response.json()["message"] == CompanyRoleResponseMessages.ROLE_DELETED.value


async def test_company_owner_cannot_manage_global_roles(
    client, login_token, login_token_superuser, seed_companies
):
    owner_headers = {"Authorization": f"Bearer {login_token}"}
    create_response = await client.post(
        "/roles",
        json=_role_payload(),
        headers=owner_headers,
    )
    assert create_response.status_code == 403, create_response.text
    assert (
        create_response.json()["detail"]["message"]
        == CompanyRoleResponseMessages.ROLE_MANAGEMENT_FORBIDDEN.value
    )

    created = await _create_global_role(client, login_token_superuser, _role_payload())
    role_id = created["id"]

    update_response = await client.patch(
        f"/roles/{role_id}",
        json={"name": f"{created['name']} Updated", "description": "Updated"},
        headers=owner_headers,
    )
    assert update_response.status_code == 403, update_response.text
    assert (
        update_response.json()["detail"]["message"]
        == CompanyRoleResponseMessages.ROLE_MANAGEMENT_FORBIDDEN.value
    )

    assign_response = await client.post(
        f"/roles/{role_id}/companies",
        json={"company_ids": [str(seed_companies["company_one"])]},
        headers=owner_headers,
    )
    assert assign_response.status_code == 403, assign_response.text
    assert (
        assign_response.json()["detail"]["message"]
        == CompanyRoleResponseMessages.ROLE_MANAGEMENT_FORBIDDEN.value
    )

    delete_response = await client.delete(
        f"/roles/{role_id}",
        headers=owner_headers,
    )
    assert delete_response.status_code == 403, delete_response.text
    assert (
        delete_response.json()["detail"]["message"]
        == CompanyRoleResponseMessages.ROLE_MANAGEMENT_FORBIDDEN.value
    )


async def test_owner_can_assign_and_unassign_existing_role_for_company(
    client, login_token, login_token_superuser, seed_companies
):
    created = await _create_global_role(client, login_token_superuser, _role_payload())
    role_id = created["id"]
    company_id = seed_companies["company_one"]
    headers = {"Authorization": f"Bearer {login_token}"}

    assign_response = await client.post(
        f"/company/{company_id}/roles/{role_id}",
        headers=headers,
    )
    assert assign_response.status_code == 201, assign_response.text
    assert assign_response.json()["message"] == CompanyRoleResponseMessages.ROLE_CREATION_SUCCESS.value

    unassign_response = await client.delete(
        f"/company/{company_id}/roles/{role_id}",
        headers=headers,
    )
    assert unassign_response.status_code == 200, unassign_response.text
    assert unassign_response.json()["message"] == CompanyRoleResponseMessages.ROLE_DELETED.value


async def test_non_manager_cannot_assign_or_unassign_company_role(
    client, login_token, login_token_user_two, login_token_superuser, seed_companies
):
    created = await _create_global_role(client, login_token_superuser, _role_payload())
    role_id = created["id"]
    company_id = seed_companies["company_one"]

    non_manager_headers = {"Authorization": f"Bearer {login_token_user_two}"}
    forbidden_assign = await client.post(
        f"/company/{company_id}/roles/{role_id}",
        headers=non_manager_headers,
    )
    assert forbidden_assign.status_code == 403, forbidden_assign.text
    assert (
        forbidden_assign.json()["detail"]["message"]
        == CompanyResponseMessages.UNAUTHORIZED_COMPANY_ACCESS.value
    )

    owner_headers = {"Authorization": f"Bearer {login_token}"}
    assign_response = await client.post(
        f"/company/{company_id}/roles/{role_id}",
        headers=owner_headers,
    )
    assert assign_response.status_code == 201, assign_response.text

    forbidden_unassign = await client.delete(
        f"/company/{company_id}/roles/{role_id}",
        headers=non_manager_headers,
    )
    assert forbidden_unassign.status_code == 403, forbidden_unassign.text
    assert (
        forbidden_unassign.json()["detail"]["message"]
        == CompanyResponseMessages.UNAUTHORIZED_COMPANY_ACCESS.value
    )
