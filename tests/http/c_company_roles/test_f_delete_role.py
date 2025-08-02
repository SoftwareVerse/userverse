import json
from app.models.company.response_messages import (
    CompanyRoleResponseMessages,
)


def test_a_delete_role_success(client, login_token, test_company_data):
    """
    Test deleting a role successfully and reassigning users.
    """
    headers = {
        "Authorization": f"Bearer {login_token}",
        "Content-Type": "application/json",
    }
    payload = {
        "role_name_to_delete": "Client Updated",
        "replacement_role_name": "Viewer",
    }

    response = client.request(
        method="DELETE",
        url="/company/1/role",
        data=json.dumps(payload),
        headers=headers,
    )

    assert response.status_code == 201  # Ensure this matches actual API response
    json_data = response.json()
    assert "message" in json_data
    assert json_data["message"] == CompanyRoleResponseMessages.ROLE_DELETED.value
    assert "data" in json_data
    assert "message" in json_data["data"]
    assert payload["role_name_to_delete"] in json_data["data"]["message"]
    assert "users_reassigned" in json_data["data"]
    assert isinstance(json_data["data"]["users_reassigned"], int)


def test_b_delete_default_role_forbidden(client, login_token):
    """
    Test attempting to delete a default system role like 'Administrator'.
    """
    headers = {
        "Authorization": f"Bearer {login_token}",
        "Content-Type": "application/json",
    }
    payload = {
        "role_name_to_delete": "Administrator",
        "replacement_role_name": "Viewer",
    }

    response = client.request(
        method="DELETE",
        url="/company/1/role",
        data=json.dumps(payload),
        headers=headers,
    )

    assert response.status_code == 422  # triggered by Pydantic field validator
    json_data = response.json()
    assert "detail" in json_data
    assert any(
        "Cannot delete default system role" in err["msg"] for err in json_data["detail"]
    )


def test_c_delete_role_not_found(client, login_token):
    """
    Test deleting a role that does not exist.
    """
    headers = {
        "Authorization": f"Bearer {login_token}",
        "Content-Type": "application/json",
    }
    payload = {
        "role_name_to_delete": "NonExistentRole",
        "replacement_role_name": "Viewer",
    }

    response = client.request(
        method="DELETE",
        url="/company/1/role",
        data=json.dumps(payload),
        headers=headers,
    )

    assert response.status_code == 400
    json_data = response.json()
    assert "detail" in json_data
    assert "error" in json_data["detail"]
    assert "message" in json_data["detail"]
    assert "Role 'NonExistentRole' not found." == json_data["detail"]["error"]
    assert (
        json_data["detail"]["message"]
        == CompanyRoleResponseMessages.ROLE_UPDATE_FAILED.value
    )


def test_d_delete_role_self_replacement_forbidden(client, login_token):
    """
    Test rejecting deletion where role is being replaced with itself.
    """
    headers = {
        "Authorization": f"Bearer {login_token}",
        "Content-Type": "application/json",
    }
    payload = {
        "role_name_to_delete": "Client Updated",
        "replacement_role_name": "Client Updated",
    }

    response = client.request(
        method="DELETE",
        url="/company/1/role",
        data=json.dumps(payload),
        headers=headers,
    )

    assert response.status_code == 400
    json_data = response.json()
    assert "detail" in json_data
    assert "error" in json_data["detail"]
    assert "message" in json_data["detail"]
    assert "Cannot replace a role with itself." == json_data["detail"]["error"]
    assert (
        json_data["detail"]["message"]
        == CompanyRoleResponseMessages.ROLE_UPDATE_FAILED.value
    )
