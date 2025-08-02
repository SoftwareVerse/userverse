# TODO: cases to add
# Create a new role for a company
# Attempt to create a role with an existing name
# Attempt to create a role with an invalid user

from app.models.company.response_messages import (
    CompanyResponseMessages,
    CompanyRoleResponseMessages,
)


def test_a_create_company_one_roles_success(client, login_token, test_company_data):
    """
    Test creating roles for a company successfully.
    """
    roles = test_company_data["roles"]
    headers = {"Authorization": f"Bearer {login_token}"}

    for role_key, role_value in roles.items():
        response = client.post("/company/1/role", json=role_value, headers=headers)
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


def test_a_create_company_two_roles_success(
    client, login_token_user_two, test_company_data
):
    """
    Test creating roles for a company successfully.
    """
    roles = test_company_data["roles"]
    headers = {"Authorization": f"Bearer {login_token_user_two}"}

    for role_key, role_value in roles.items():
        response = client.post("/company/2/role", json=role_value, headers=headers)
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


def test_b_create_company_roles_failure(
    client, login_token_user_two, test_company_data
):
    """
    Test creating roles for a company failure. When the user is not authorized to create roles.
    """
    roles = test_company_data["roles"]
    headers = {"Authorization": f"Bearer {login_token_user_two}"}

    for role_key, role_value in roles.items():
        response = client.post("/company/1/role", json=role_value, headers=headers)
        #
        assert response.status_code in [400, 403]
        json_data = response.json()
        #
        assert "detail" in json_data
        assert (
            json_data["detail"]["message"]
            == CompanyResponseMessages.UNAUTHORIZED_COMPANY_ACCESS.value
        )


def test_c_create_company_roles_failure(
    client, login_token_user_two, test_company_data
):
    """
    Test creating roles for a company failure. When the roles already exist
    """
    roles = test_company_data["roles"]
    headers = {"Authorization": f"Bearer {login_token_user_two}"}

    for role_key, role_value in roles.items():
        response = client.post("/company/2/role", json=role_value, headers=headers)
        #
        assert response.status_code in [400, 403]
        json_data = response.json()
        #
        assert "detail" in json_data
        assert (
            json_data["detail"]["message"]
            == CompanyRoleResponseMessages.ROLE_CREATION_FAILED.value
        )
