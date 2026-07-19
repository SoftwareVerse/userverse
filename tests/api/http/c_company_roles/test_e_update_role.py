from app.models.company.response_messages import (
    CompanyResponseMessages,
    CompanyRoleResponseMessages,
)


def test_a_update_role_description_success(client, login_token, test_company_data):
    """
    Test updating a role's description successfully.
    """
    headers = {"Authorization": f"Bearer {login_token}"}
    # Assume company 1 and role 'Admin' exist
    payload = test_company_data["roles"]
    for role_key, role_value in payload.items():
        name = role_value["name"]
        data = {
            "name": name + " Updated",
            "description": role_value["description"] + " Updated",
        }
        response = client.patch(f"/company/1/role/{name}", json=data, headers=headers)
        #
        assert response.status_code == 201
        json_data = response.json()
        #
        assert "message" in json_data
        assert json_data["message"] == CompanyRoleResponseMessages.ROLE_UPDATED.value
        assert "data" in json_data
        assert json_data["data"]["name"] == data["name"]
        assert json_data["data"]["description"] == data["description"]


def test_b_update_role_description_forbidden(client, login_token_user_two):
    """
    Test updating a role's description fails if not admin.
    """
    headers = {"Authorization": f"Bearer {login_token_user_two}"}
    payload = {
        "name": None,
        "description": "Should not update",
    }
    response = client.patch("/company/1/role/Admin", json=payload, headers=headers)
    assert response.status_code in [400, 403]
    json_data = response.json()

    assert "detail" in json_data
    assert (
        json_data["detail"]["message"]
        == CompanyResponseMessages.UNAUTHORIZED_COMPANY_ACCESS.value
    )


def test_c_update_role_description_not_found(client, login_token):
    """
    Test updating a role that does not exist
    """
    headers = {"Authorization": f"Bearer {login_token}"}
    payload = {
        "name": "Should not update",
        "description": "Should not update",
    }
    response = client.patch("/company/1/role/string", json=payload, headers=headers)
    assert response.status_code in [400, 403]
    json_data = response.json()

    assert "detail" in json_data
    assert (
        json_data["detail"]["message"]
        == CompanyRoleResponseMessages.ROLE_UPDATE_FAILED.value
    )
    assert (
        json_data["detail"]["error"]
        == "Role with company_id=1 and name='string' not found."
    )
