import pytest

from app.models.company.response_messages import (
    CompanyResponseMessages,
    CompanyUserResponseMessages,
)

pytestmark = pytest.mark.anyio


@pytest.mark.parametrize(
    "login_token_key, company_id, query_params, expected_emails, expected_status",
    [
        # ✅ User 1 accessing own company
        ("login_token", "company_one", "limit=10&page=1", {"user.one@email.com"}, 200),
        (
            "login_token",
            "company_one",
            "limit=10&page=1&role_name=Admin",
            set(),
            200,
        ),
        (
            "login_token",
            "company_one",
            "limit=10&page=1&email=user.one@email.com",
            {"user.one@email.com"},
            200,
        ),
        # ❌ User 1 accessing company 2
        ("login_token", "company_two", "limit=10&page=1", set(), 403),
        # ✅ User 2 accessing own company
        (
            "login_token_user_two",
            "company_two",
            "limit=10&page=1",
            {"user.two@email.com"},
            200,
        ),
        (
            "login_token_user_two",
            "company_two",
            "limit=10&page=1&first_name=Jane",
            {"user.two@email.com"},
            200,
        ),
        (
            "login_token_user_two",
            "company_two",
            "limit=10&page=1&last_name=Smith",
            {"user.two@email.com"},
            200,
        ),
        # ❌ User 2 accessing company 1
        ("login_token_user_two", "company_one", "limit=10&page=1", set(), 403),
    ],
)
async def test_get_users_for_company(
    client,
    login_token,
    login_token_user_two,
    seed_companies,
    verify_both_users,
    login_token_key,
    company_id,
    query_params,
    expected_emails,
    expected_status,
):
    """
    Test retrieving users in a company using both users' tokens and checking role/user filters.
    """

    # Resolve correct token from fixture key
    token_map = {
        "login_token": login_token,
        "login_token_user_two": login_token_user_two,
    }

    headers = {
        "Authorization": f"Bearer {token_map[login_token_key]}",
        "accept": "application/json",
    }
    company_id = seed_companies[company_id]

    response = await client.get(
        f"/company/{company_id}/users?{query_params}", headers=headers
    )
    assert response.status_code == expected_status

    if expected_status == 200:
        json_data = response.json()
        assert (
            json_data["message"] == CompanyUserResponseMessages.GET_COMPANY_USERS.value
        )
        records = json_data["data"]["records"]
        actual_emails = {user["email"] for user in records}
        assert actual_emails == expected_emails
        for user in records:
            assert "role_id" not in user
            assert "role_name" not in user
            assert set(user["role"]) == {"id", "name", "description", "permissions"}
            assert user["role"]["permissions"] == []
        pagination = json_data["data"]["pagination"]
        assert pagination["limit"] == 10
        assert pagination["current_page"] == 1

    elif expected_status == 403:
        json_data = response.json()
        assert "detail" in json_data
        assert (
            json_data["detail"]["message"]
            == CompanyResponseMessages.UNAUTHORIZED_COMPANY_ACCESS.value
        )


async def test_get_users_for_company_returns_nested_role_details(
    client,
    login_token,
    seed_companies,
    verify_both_users,
):
    response = await client.get(
        f"/company/{seed_companies['company_one']}/users?limit=10&page=1",
        headers={
            "Authorization": f"Bearer {login_token}",
            "accept": "application/json",
        },
    )

    assert response.status_code == 200, response.text
    record = response.json()["data"]["records"][0]
    assert record["email"] == "user.one@email.com"
    assert record["role"] == {
        "id": record["role"]["id"],
        "name": "Owner",
        "description": "Full access to manage users and data",
        "permissions": [],
    }
