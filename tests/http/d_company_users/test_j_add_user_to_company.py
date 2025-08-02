import pytest
from app.models.company.response_messages import (
    CompanyResponseMessages,
    CompanyUserResponseMessages,
)


@pytest.mark.parametrize(
    "login_token_key, company_id, payload, expected_status, expected_message",
    [
        # ✅ Admin adds a new user to company 1 with a valid role
        (
            "login_token",
            1,
            {"email": "user.three@email.com", "role": "Viewer"},
            201,
            CompanyUserResponseMessages.ADD_USER_SUCCESS.value,
        ),
        (
            "login_token_user_two",
            2,
            {"email": "user.three@email.com", "role": "Viewer"},
            201,
            CompanyUserResponseMessages.ADD_USER_SUCCESS.value,
        ),
        # ❌ Non-admin tries to add a user to company 1
        (
            "login_token_user_two",
            1,
            {"email": "user.three@email.com", "role": "Viewer"},
            403,
            CompanyResponseMessages.UNAUTHORIZED_COMPANY_ACCESS.value,
        ),
        # ❌ Admin tries to add a user with an invalid role
        (
            "login_token",
            1,
            {"email": "user.three@email.com", "role": "NotARealRole"},
            400,
            CompanyUserResponseMessages.ADD_USER_FAILED.value,
        ),
    ],
)
def test_add_user_to_company(
    client,
    login_token,
    login_token_user_two,
    login_token_key,
    company_id,
    payload,
    expected_status,
    expected_message,
):
    """
    Test /company/{company_id}/users for adding users with various scenarios:
    - valid user addition
    - unauthorized user attempt
    - invalid role
    """
    token_map = {
        "login_token": login_token,
        "login_token_user_two": login_token_user_two,
    }

    headers = {
        "Authorization": f"Bearer {token_map[login_token_key]}",
        "accept": "application/json",
        "Content-Type": "application/json",
    }

    response = client.post(
        f"/company/{company_id}/users", json=payload, headers=headers
    )
    assert response.status_code == expected_status
    json_data = response.json()

    if expected_status == 201:
        assert "data" in json_data
        assert json_data["message"] == expected_message
