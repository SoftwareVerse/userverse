from uuid import uuid4

from app.models.company.response_messages import CompanyResponseMessages


def _build_company_payload() -> dict:
    suffix = uuid4().hex
    return {
        "email": f"delete-company-{suffix}@email.com",
        "name": f"Delete Company {suffix}",
        "description": "Company created for delete endpoint coverage.",
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


def test_delete_company_success_for_owner(client, login_token):
    payload = _build_company_payload()
    headers = {"Authorization": f"Bearer {login_token}"}

    create_response = client.post("/company", json=payload, headers=headers)
    assert create_response.status_code in [200, 201], create_response.text
    company_id = create_response.json()["data"]["id"]

    delete_response = client.delete(f"/company/{company_id}", headers=headers)
    assert delete_response.status_code == 200, delete_response.text
    assert (
        delete_response.json()["message"]
        == CompanyResponseMessages.COMPANY_DELETED.value
    )
    assert delete_response.json()["data"] is None

    get_response = client.get(
        f"/company?company_id={company_id}",
        headers=headers,
    )
    assert get_response.status_code == 404, get_response.text
    assert (
        get_response.json()["detail"]["message"]
        == CompanyResponseMessages.COMPANY_NOT_FOUND.value
    )


def test_delete_company_forbidden_for_non_owner(
    client, login_token, login_token_user_two
):
    payload = _build_company_payload()
    owner_headers = {"Authorization": f"Bearer {login_token}"}

    create_response = client.post("/company", json=payload, headers=owner_headers)
    assert create_response.status_code in [200, 201], create_response.text
    company_id = create_response.json()["data"]["id"]

    delete_response = client.delete(
        f"/company/{company_id}",
        headers={"Authorization": f"Bearer {login_token_user_two}"},
    )
    assert delete_response.status_code == 403, delete_response.text
    assert (
        delete_response.json()["detail"]["message"]
        == CompanyResponseMessages.UNAUTHORIZED_COMPANY_ACCESS.value
    )

    cleanup_response = client.delete(f"/company/{company_id}", headers=owner_headers)
    assert cleanup_response.status_code == 200, cleanup_response.text
