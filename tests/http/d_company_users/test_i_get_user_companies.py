import pytest
from tests.http.conftest import client, login_token, login_token_user_two
from app.models.company.response_messages import (
    CompanyResponseMessages,
    CompanyUserResponseMessages,
)


@pytest.mark.parametrize(
    "login_token_key, query_params, expected_company_ids, expected_status",
    [
        ("login_token", "limit=10&offset=0", {1}, 200),
        ("login_token", "limit=10&offset=0&name=Test", set(), 200),  # updated
        ("login_token", "limit=10&offset=0&email=notfound@example.com", set(), 200),
        ("login_token_user_two", "limit=10&offset=0", {2}, 200),
        ("login_token_user_two", "limit=10&offset=0&role_name=Admin", {2}, 200),
        (
            "login_token_user_two",
            "limit=10&offset=0&industry=Healthcare",
            set(),
            200,
        ),  # updated
    ],
)
def test_get_user_companies(
    client,
    login_token,
    login_token_user_two,
    login_token_key,
    query_params,
    expected_company_ids,
    expected_status,
):
    """
    Test /user/companies with various filters and users.
    """
    token_map = {
        "login_token": login_token,
        "login_token_user_two": login_token_user_two,
    }

    headers = {
        "Authorization": f"Bearer {token_map[login_token_key]}",
        "accept": "application/json",
    }

    response = client.get(f"/user/companies?{query_params}", headers=headers)
    assert response.status_code == expected_status

    if expected_status == 200:
        json_data = response.json()
        assert (
            json_data["message"] == CompanyUserResponseMessages.GET_COMPANY_USERS.value
        )
        company_ids = {company["id"] for company in json_data["data"]["records"]}
        assert company_ids == expected_company_ids

        pagination = json_data["data"]["pagination"]
        assert pagination["limit"] == 10
        assert pagination["offset"] == 0
