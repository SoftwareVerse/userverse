import pytest
from app.models.company.response_messages import (
    CompanyResponseMessages,
    CompanyUserResponseMessages,
)


@pytest.mark.parametrize(
    "login_token_key, company_id, user_id, expected_status, expected_message",
    [
        # Admin removes non-Admin user
        (
            "login_token",
            1,
            3,  # Assume user.one@email.com is the last admin
            201,
            CompanyUserResponseMessages.REMOVE_USER_SUCCESS.value,
        ),
        # ❌ Non-admin tries to remove a user from company 1
        (
            "login_token_user_two",
            1,
            3,
            403,
            CompanyResponseMessages.UNAUTHORIZED_COMPANY_ACCESS.value,
        ),
        # ❌ Admin tries to remove the last admin
        (
            "login_token",
            1,
            1,  # Assume user.one@email.com is the last admin
            400,
            CompanyUserResponseMessages.SUPER_ADMIN_REMOVE_FORBIDDEN.value,
        ),
    ],
)
def test_remove_user_from_company(
    client,
    login_token,
    login_token_user_two,
    login_token_key,
    company_id,
    user_id,
    expected_status,
    expected_message,
):
    """
    Test /company/{company_id}/user/{user_id} for removing users with various scenarios:
    - unauthorized user attempt
    - last admin removal forbidden
    """
    token_map = {
        "login_token": login_token,
        "login_token_user_two": login_token_user_two,
    }

    headers = {
        "Authorization": f"Bearer {token_map[login_token_key]}",
        "accept": "application/json",
    }

    response = client.delete(f"/company/{company_id}/user/{user_id}", headers=headers)

    assert response.status_code == expected_status, (
        f"Expected status {expected_status}, got {response.status_code}. "
        f"Response body: {response.text}"
    )

    json_data = response.json()

    if expected_status == 201:
        assert "message" in json_data
        assert expected_message == json_data["message"]
        assert "data" in json_data
        assert isinstance(json_data["data"], dict)
    elif expected_status == 403:
        assert "detail" in json_data
        assert "message" in json_data["detail"]
        assert json_data["detail"]["message"] == expected_message
