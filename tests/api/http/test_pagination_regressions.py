import pytest

from app.models.company.response_messages import (
    CompanyRoleResponseMessages,
    CompanyUserResponseMessages,
)

pytestmark = pytest.mark.anyio


async def test_get_company_roles_page_two_is_stable(client, seed_pagination_state):
    headers = {"Authorization": f"Bearer {seed_pagination_state['owner_token']}"}
    company_id = seed_pagination_state["role_company_id"]

    response = await client.get(
        f"/company/{company_id}/roles?limit=2&page=2",
        headers=headers,
    )

    assert response.status_code == 200
    json_data = response.json()
    assert json_data["message"] == CompanyRoleResponseMessages.ROLE_GET_SUCCESS.value

    records = json_data["data"]["records"]
    assert [role["name"] for role in records] == ["Owner", "User"]

    pagination = json_data["data"]["pagination"]
    assert pagination == {
        "total_records": 5,
        "limit": 2,
        "current_page": 2,
        "total_pages": 3,
    }


async def test_get_company_users_page_two_is_stable(client, seed_pagination_state):
    headers = {"Authorization": f"Bearer {seed_pagination_state['owner_token']}"}
    company_id = seed_pagination_state["users_company_id"]

    response = await client.get(
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


async def test_get_user_companies_page_two_is_stable(client, seed_pagination_state):
    headers = {"Authorization": f"Bearer {seed_pagination_state['owner_token']}"}

    response = await client.get(
        "/user/companies?limit=2&page=2",
        headers=headers,
    )

    assert response.status_code == 200
    json_data = response.json()
    assert json_data["message"] == CompanyUserResponseMessages.GET_COMPANY_USERS.value

    records = json_data["data"]["records"]
    assert [company["id"] for company in records] == [
        str(company_id) for company_id in seed_pagination_state["user_company_ids"][2:]
    ]

    pagination = json_data["data"]["pagination"]
    assert pagination == {
        "total_records": 4,
        "limit": 2,
        "current_page": 2,
        "total_pages": 2,
    }


async def test_get_user_companies_returns_company_specific_roles(
    client, seed_pagination_state, test_company_data
):
    headers = {"Authorization": f"Bearer {seed_pagination_state['owner_token']}"}

    response = await client.get(
        "/user/companies?limit=4&page=1",
        headers=headers,
    )

    assert response.status_code == 200
    json_data = response.json()
    records = json_data["data"]["records"]

    assert [company["id"] for company in records] == [
        str(company_id) for company_id in seed_pagination_state["user_company_ids"]
    ]
    for company in records:
        expected_role = seed_pagination_state["owner_company_roles"][company["id"]]
        assert company["name"].startswith("Pagination Company")
        assert company["address"] == {
            "street": "123 Pagination Road",
            "city": "Johannesburg",
            "state": "Gauteng",
            "postal_code": "2000",
            "country": "South Africa",
        }
        permissions = company["role"].pop("permissions")
        assert company["role"] == expected_role
        default_role = next(
            role
            for role in test_company_data["default_roles"].values()
            if role["name"] == expected_role["name"]
        )
        assert {permission["name"] for permission in permissions} == set(
            default_role["permissions"]
        )
        assert all(permission["scope"] == "global" for permission in permissions)
        assert all(permission["company_id"] is None for permission in permissions)

    assert json_data["data"]["pagination"] == {
        "total_records": 4,
        "limit": 4,
        "current_page": 1,
        "total_pages": 1,
    }
