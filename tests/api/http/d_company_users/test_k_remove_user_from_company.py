from uuid import uuid4

from app.models.company.response_messages import (
    CompanyResponseMessages,
    CompanyUserResponseMessages,
)


def _build_company_payload() -> dict:
    suffix = uuid4().hex
    return {
        "email": f"remove-user-{suffix}@email.com",
        "name": f"Remove User Company {suffix}",
        "description": "Company created for remove-user endpoint coverage.",
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


def _add_user_to_company(client, token: str, company_id: int, email: str) -> int:
    response = client.post(
        f"/company/{company_id}/users",
        json={"email": email, "role": "Viewer"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]["id"]


def test_remove_user_from_company_success(client, login_token):
    company_id = _create_company(client, login_token)
    user_id = _add_user_to_company(
        client, login_token, company_id, "user.three@email.com"
    )

    response = client.delete(
        f"/company/{company_id}/user/{user_id}",
        headers={"Authorization": f"Bearer {login_token}", "accept": "application/json"},
    )

    assert response.status_code == 200, response.text
    json_data = response.json()
    assert json_data["message"] == CompanyUserResponseMessages.REMOVE_USER_SUCCESS.value
    assert json_data["data"]["id"] == user_id


def test_remove_user_from_company_forbidden_for_non_owner(
    client, login_token, login_token_user_two
):
    company_id = _create_company(client, login_token)
    user_id = _add_user_to_company(
        client, login_token, company_id, "user.three@email.com"
    )

    response = client.delete(
        f"/company/{company_id}/user/{user_id}",
        headers={
            "Authorization": f"Bearer {login_token_user_two}",
            "accept": "application/json",
        },
    )

    assert response.status_code == 403, response.text
    assert (
        response.json()["detail"]["message"]
        == CompanyResponseMessages.UNAUTHORIZED_COMPANY_ACCESS.value
    )


def test_remove_owner_from_company_forbidden(client, login_token):
    company_id = _create_company(client, login_token)

    response = client.delete(
        f"/company/{company_id}/user/1",
        headers={"Authorization": f"Bearer {login_token}", "accept": "application/json"},
    )

    assert response.status_code == 400, response.text
    json_data = response.json()
    assert json_data["detail"]["message"] == CompanyUserResponseMessages.REMOVE_USER_FAILED.value
    assert json_data["detail"]["error"] == "Owner cannot be removed from the company."
