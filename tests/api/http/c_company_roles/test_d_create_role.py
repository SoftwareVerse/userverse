import pytest
from uuid import uuid4

pytestmark = pytest.mark.anyio
# TODO: cases to add
# Create a new role for a company
# Attempt to create a role with an existing name
# Attempt to create a role with an invalid user

from app.models.company.response_messages import (
    CompanyRoleResponseMessages,
)


async def test_a_create_company_one_roles_success(
    client, login_token_superuser, test_company_data, seed_companies
):
    """
    Test creating roles for a company successfully.
    """
    company_id = seed_companies["company_one"]
    suffix = uuid4().hex
    roles = {
        key: {
            **value,
            "name": f"{value['name']}-{suffix}",
            "description": f"{value['description']} ({suffix})",
        }
        for key, value in test_company_data["roles"].items()
    }
    headers = {"Authorization": f"Bearer {login_token_superuser}"}

    for role_key, role_value in roles.items():
        response = await client.post(
            f"/company/{company_id}/role", json=role_value, headers=headers
        )
        #
        assert response.status_code in [200, 201]
        json_data = response.json()
        #
        assert "message" in json_data
        assert (
            json_data["message"]
            == CompanyRoleResponseMessages.ROLE_CREATION_SUCCESS.value
        )
        assert "data" in json_data
        assert json_data["data"]["name"] == role_value["name"]
        assert json_data["data"]["description"] == role_value["description"]
        assert json_data["data"]["permissions"] == []


async def test_a_create_company_two_roles_success(
    client, login_token_superuser, test_company_data, seed_companies
):
    """
    Test creating roles for a company successfully.
    """
    company_id = seed_companies["company_two"]
    suffix = uuid4().hex
    roles = {
        key: {
            **value,
            "name": f"{value['name']}-{suffix}",
            "description": f"{value['description']} ({suffix})",
        }
        for key, value in test_company_data["roles"].items()
    }
    headers = {"Authorization": f"Bearer {login_token_superuser}"}

    for role_key, role_value in roles.items():
        response = await client.post(
            f"/company/{company_id}/role", json=role_value, headers=headers
        )
        #
        assert response.status_code in [200, 201]
        json_data = response.json()
        #
        assert "message" in json_data
        assert (
            json_data["message"]
            == CompanyRoleResponseMessages.ROLE_CREATION_SUCCESS.value
        )
        assert "data" in json_data
        assert json_data["data"]["name"] == role_value["name"]
        assert json_data["data"]["description"] == role_value["description"]
        assert json_data["data"]["permissions"] == []


async def test_b_create_company_roles_failure(
    client, login_token_user_two, test_company_data, seed_companies
):
    """
    Test creating roles for a company failure. When the user is not authorized to create roles.
    """
    company_id = seed_companies["company_one"]
    roles = test_company_data["roles"]
    headers = {"Authorization": f"Bearer {login_token_user_two}"}

    for role_key, role_value in roles.items():
        response = await client.post(
            f"/company/{company_id}/role", json=role_value, headers=headers
        )
        #
        assert response.status_code == 403
        json_data = response.json()
        #
        assert "detail" in json_data
        assert (
            json_data["detail"]["message"]
            == CompanyRoleResponseMessages.ROLE_MANAGEMENT_FORBIDDEN.value
        )


async def test_c_create_company_roles_failure(
    client, login_token_superuser, test_company_data, seed_companies
):
    """
    Test creating roles for a company failure. When the roles already exist
    """
    company_id = seed_companies["company_two"]
    suffix = uuid4().hex
    roles = {
        key: {
            **value,
            "name": f"{value['name']}-{suffix}",
            "description": f"{value['description']} ({suffix})",
        }
        for key, value in test_company_data["roles"].items()
    }
    headers = {"Authorization": f"Bearer {login_token_superuser}"}

    for role_key, role_value in roles.items():
        first_response = await client.post(
            f"/company/{company_id}/role", json=role_value, headers=headers
        )
        assert first_response.status_code in [200, 201], first_response.text

        response = await client.post(
            f"/company/{company_id}/role", json=role_value, headers=headers
        )
        #
        assert response.status_code == 400
        json_data = response.json()
        #
        assert "detail" in json_data
        assert (
            json_data["detail"]["message"]
            == CompanyRoleResponseMessages.ROLE_CREATION_FAILED.value
        )
