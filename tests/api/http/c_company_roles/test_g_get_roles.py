import pytest
from app.models.company.response_messages import CompanyRoleResponseMessages
from app.utils.app_error import AppError


@pytest.mark.parametrize(
    "query_params,expected_names",
    [
        ("limit=10&page=1", {"Administrator", "Client", "Owner", "User", "Viewer"}),
        ("limit=10&page=1&name=Ad", {"Administrator"}),
        ("limit=10&page=1&name=er&description=access", {"Owner", "User", "Viewer"}),
    ],
)
def test_get_company_roles(
    client,
    seed_pagination_state,
    query_params,
    expected_names,
):
    """
    Test getting company roles with optional filters.
    """
    company_id = seed_pagination_state["role_company_id"]
    headers = {
        "Authorization": f"Bearer {seed_pagination_state['owner_token']}",
        "accept": "application/json",
    }

    response = client.get(
        f"/company/{company_id}/roles?{query_params}",
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
    assert pagination["current_page"] == 1
    assert pagination["total_records"] == len(expected_names)


def test_get_roles_with_invalid_filter(client, seed_pagination_state):
    """
    Test getting company roles with a filter that returns no results.
    """
    company_id = seed_pagination_state["role_company_id"]
    headers = {
        "Authorization": f"Bearer {seed_pagination_state['owner_token']}",
        "accept": "application/json",
    }

    response = client.get(f"/company/{company_id}/roles?name=xyz", headers=headers)
    assert response.status_code == 200

    json_data = response.json()
    assert json_data["message"] == CompanyRoleResponseMessages.ROLE_GET_SUCCESS.value
    assert json_data["data"]["records"] == []
    assert json_data["data"]["pagination"]["total_records"] == 0


def test_get_roles_with_pagination(client, seed_pagination_state):
    """
    Test pagination with limit=1 and page=2.
    """
    company_id = seed_pagination_state["role_company_id"]
    headers = {
        "Authorization": f"Bearer {seed_pagination_state['owner_token']}",
        "accept": "application/json",
    }

    response = client.get(
        f"/company/{company_id}/roles?limit=1&page=2",
        headers=headers,
    )
    assert response.status_code == 200

    json_data = response.json()
    assert json_data["message"] == CompanyRoleResponseMessages.ROLE_GET_SUCCESS.value
    assert len(json_data["data"]["records"]) == 1
    assert json_data["data"]["records"][0]["name"] == "Client"

    pagination = json_data["data"]["pagination"]
    assert pagination["limit"] == 1
    assert pagination["current_page"] == 2
    assert pagination["total_pages"] == 5


def test_get_company_roles_reraises_service_errors(
    client, seed_pagination_state, monkeypatch: pytest.MonkeyPatch
):
    company_id = seed_pagination_state["role_company_id"]
    headers = {
        "Authorization": f"Bearer {seed_pagination_state['owner_token']}",
        "accept": "application/json",
    }

    def _raise_app_error(*args, **kwargs):
        raise AppError(status_code=418, message="forced role failure", log_error=False)

    monkeypatch.setattr(
        "app.api.routers.company.roles.RoleService.get_company_roles",
        _raise_app_error,
    )

    response = client.get(
        f"/company/{company_id}/roles?limit=10&page=1",
        headers=headers,
    )

    assert response.status_code == 418
    assert response.json()["detail"]["message"] == "forced role failure"
