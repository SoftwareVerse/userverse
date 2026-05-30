from app.models.company.response_messages import (
    CompanyRoleResponseMessages,
    CompanyUserResponseMessages,
)


def test_get_company_roles_page_two_is_stable(client, seed_pagination_state):
    headers = {"Authorization": f"Bearer {seed_pagination_state['owner_token']}"}
    company_id = seed_pagination_state["role_company_id"]

    response = client.get(
        f"/company/{company_id}/roles?limit=2&page=2",
        headers=headers,
    )

    assert response.status_code == 200
    json_data = response.json()
    assert json_data["message"] == CompanyRoleResponseMessages.ROLE_GET_SUCCESS.value

    records = json_data["data"]["records"]
    assert [role["name"] for role in records] == ["User", "Viewer"]

    pagination = json_data["data"]["pagination"]
    assert pagination == {
        "total_records": 4,
        "limit": 2,
        "current_page": 2,
        "total_pages": 2,
    }


def test_get_company_users_page_two_is_stable(client, seed_pagination_state):
    headers = {"Authorization": f"Bearer {seed_pagination_state['owner_token']}"}
    company_id = seed_pagination_state["users_company_id"]

    response = client.get(
        f"/company/{company_id}/users?limit=2&page=2",
        headers=headers,
    )

    assert response.status_code == 200
    json_data = response.json()
    assert json_data["message"] == CompanyUserResponseMessages.GET_COMPANY_USERS.value

    records = json_data["data"]["records"]
    assert [user["email"] for user in records] == [
        "pagination.user.two@email.com",
        "pagination.user.three@email.com",
    ]

    pagination = json_data["data"]["pagination"]
    assert pagination == {
        "total_records": 4,
        "limit": 2,
        "current_page": 2,
        "total_pages": 2,
    }


def test_get_user_companies_page_two_is_stable(client, seed_pagination_state):
    headers = {"Authorization": f"Bearer {seed_pagination_state['owner_token']}"}

    response = client.get(
        "/user/companies?limit=2&page=2",
        headers=headers,
    )

    assert response.status_code == 200
    json_data = response.json()
    assert json_data["message"] == CompanyUserResponseMessages.GET_COMPANY_USERS.value

    records = json_data["data"]["records"]
    assert [company["id"] for company in records] == seed_pagination_state[
        "user_company_ids"
    ][2:]

    pagination = json_data["data"]["pagination"]
    assert pagination == {
        "total_records": 4,
        "limit": 2,
        "current_page": 2,
        "total_pages": 2,
    }
