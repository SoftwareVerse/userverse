import pytest
from uuid import uuid4
from app.models.company.response_messages import (
    CompanyResponseMessages,
    CompanyUserResponseMessages,
)


def _build_company_payload() -> dict:
    suffix = uuid4().hex
    return {
        "email": f"company-user-add-{suffix}@email.com",
        "name": f"Company User Add {suffix}",
        "description": "Company created for duplicate add-user coverage.",
        "industry": "Testing",
        "phone_number": "+27123456789",
        "address": {
            "street": "123 Main St",
            "city": "Johannesburg",
            "state": "Gauteng",
            "postal_code": "2000",
            "country": "South Africa",
        },
    }


def _create_company(client, token: str) -> int:
    response = client.post(
        "/company",
        json=_build_company_payload(),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code in [200, 201], response.text
    return response.json()["data"]["id"]


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
        # ❌ Admin tries to add a user that does not exist
        (
            "login_token",
            1,
            {"email": "missing.user@email.com", "role": "Viewer"},
            404,
            CompanyUserResponseMessages.ADD_USER_FAILED.value,
        ),
    ],
)
def test_add_user_to_company(
    client,
    login_token,
    login_token_user_two,
    seed_company_roles,
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
    else:
        assert json_data["detail"]["message"] == expected_message


def test_add_user_to_company_rejects_existing_link(
    client, login_token, seed_company_roles
):
    company_id = _create_company(client, login_token)
    headers = {
        "Authorization": f"Bearer {login_token}",
        "accept": "application/json",
        "Content-Type": "application/json",
    }
    payload = {"email": "user.three@email.com", "role": "Viewer"}

    first_response = client.post(
        f"/company/{company_id}/users", json=payload, headers=headers
    )
    assert first_response.status_code == 201, first_response.text

    second_response = client.post(
        f"/company/{company_id}/users", json=payload, headers=headers
    )
    assert second_response.status_code == 400, second_response.text
    assert (
        second_response.json()["detail"]["message"]
        == CompanyUserResponseMessages.ADD_EXISTING_USER_FAILED.value
    )
