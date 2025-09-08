import pytest
from app.models.company.response_messages import CompanyRoleResponseMessages


@pytest.mark.parametrize(
    "query_params,expected_names",
    [
        ("limit=10&offset=0", {"Administrator", "User Updated", "Viewer"}),
        ("limit=10&offset=0&name=Ad", {"Administrator"}),
        ("limit=10&offset=0&name=er&description=access", {"User Updated", "Viewer"}),
    ],
)
def test_get_company_roles(
    client, login_token, test_company_data, query_params, expected_names
):
    """
    Test getting company roles with optional filters.
    """
    headers = {
        "Authorization": f"Bearer {login_token}",
        "accept": "application/json",
    }

    response = client.get(
        f"/company/1/roles?{query_params}",
        headers=headers,
    )

    assert response.status_code == 200
    json_data = response.json()

    assert "message" in json_data
    assert json_data["message"] == CompanyRoleResponseMessages.ROLE_GET_SUCCESS.value
    assert "data" in json_data
    assert "records" in json_data["data"]
    assert "pagination" in json_data["data"]

    actual_names = {role["name"] for role in json_data["data"]["records"]}
    assert actual_names == expected_names

    pagination = json_data["data"]["pagination"]
    assert pagination["limit"] == 10
    assert pagination["offset"] == 0
    assert pagination["total_records"] == len(expected_names)


def test_get_roles_with_invalid_filter(client, login_token, test_company_data):
    """
    Test getting company roles with a filter that returns no results.
    """
    headers = {
        "Authorization": f"Bearer {login_token}",
        "accept": "application/json",
    }

    response = client.get("/company/1/roles?name=xyz", headers=headers)
    assert response.status_code == 200

    json_data = response.json()
    assert json_data["message"] == CompanyRoleResponseMessages.ROLE_GET_SUCCESS.value
    assert json_data["data"]["records"] == []
    assert json_data["data"]["pagination"]["total_records"] == 0


def test_get_roles_with_pagination(client, login_token, test_company_data):
    """
    Test pagination with limit=1 and offset=1.
    """
    headers = {
        "Authorization": f"Bearer {login_token}",
        "accept": "application/json",
    }

    response = client.get("/company/1/roles?limit=1&offset=1", headers=headers)
    assert response.status_code == 200

    json_data = response.json()
    assert json_data["message"] == CompanyRoleResponseMessages.ROLE_GET_SUCCESS.value
    assert len(json_data["data"]["records"]) == 1

    pagination = json_data["data"]["pagination"]
    assert pagination["limit"] == 1
    assert pagination["offset"] == 1
    assert pagination["current_page"] == 2
