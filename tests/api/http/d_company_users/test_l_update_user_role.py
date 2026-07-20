from uuid import UUID, uuid4

from app.repository.database.session_manager import DatabaseSessionManager
from app.repository.database.tables import AssociationUserCompany, User


def _build_company_payload() -> dict:
    suffix = uuid4().hex
    return {
        "email": f"company-user-role-{suffix}@email.com",
        "name": f"Company User Role {suffix}",
        "description": "Company created for company-user role update coverage.",
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


def _create_company(client, token: str) -> str:
    response = client.post(
        "/company",
        json=_build_company_payload(),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code in [200, 201], response.text
    return response.json()["data"]["id"]


def _create_role(client, token: str, company_id: str, payload: dict) -> None:
    response = client.post(
        f"/company/{company_id}/role",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code in [200, 201], response.text


def _add_user_to_company(client, token: str, company_id: str, email: str) -> str:
    response = client.post(
        f"/company/{company_id}/users",
        json={"email": email, "role": "Viewer"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]["id"]


def _get_user_id(email: str) -> UUID:
    db = DatabaseSessionManager()
    session = db.session_object()
    try:
        user = session.query(User).filter_by(email=email.lower()).one()
        return user.id
    finally:
        session.close()


def _get_link_row(company_id: str, user_id: str):
    db = DatabaseSessionManager()
    session = db.session_object()
    try:
        company_uuid = UUID(company_id)
        user_uuid = UUID(user_id)
        return (
            session.query(AssociationUserCompany)
            .filter_by(company_id=company_uuid, user_id=user_uuid, _closed_at=None)
            .first()
        )
    finally:
        session.close()


def test_update_company_user_role_success(client, login_token):
    company_id = _create_company(client, login_token)
    _create_role(
        client,
        login_token,
        company_id,
        {
            "name": "User",
            "description": "Standard user role for company-user role update tests.",
        },
    )
    user_id = _add_user_to_company(
        client, login_token, company_id, "user.three@email.com"
    )

    response = client.patch(
        f"/company/{company_id}/user/{user_id}",
        json={"role": "User"},
        headers={"Authorization": f"Bearer {login_token}"},
    )

    assert response.status_code in [200, 201], response.text
    json_data = response.json()
    assert "data" in json_data
    assert json_data["data"]["id"] == user_id
    assert json_data["data"]["role_name"] == "User"

    link_row = _get_link_row(company_id, user_id)
    assert link_row is not None
    assert link_row.role_name == "User"


def test_update_company_user_role_forbidden_for_non_admin(
    client, login_token, login_token_user_two
):
    company_id = _create_company(client, login_token)
    _create_role(
        client,
        login_token,
        company_id,
        {
            "name": "User",
            "description": "Standard user role for company-user role update tests.",
        },
    )
    user_id = _add_user_to_company(
        client, login_token, company_id, "user.three@email.com"
    )

    response = client.patch(
        f"/company/{company_id}/user/{user_id}",
        json={"role": "User"},
        headers={"Authorization": f"Bearer {login_token_user_two}"},
    )

    assert response.status_code == 403, response.text
    link_row = _get_link_row(company_id, user_id)
    assert link_row is not None
    assert link_row.role_name == "Viewer"


def test_update_company_user_role_rejects_unknown_role(client, login_token):
    company_id = _create_company(client, login_token)
    user_id = _add_user_to_company(
        client, login_token, company_id, "user.three@email.com"
    )

    response = client.patch(
        f"/company/{company_id}/user/{user_id}",
        json={"role": "NotARealRole"},
        headers={"Authorization": f"Bearer {login_token}"},
    )

    assert response.status_code == 400, response.text
    link_row = _get_link_row(company_id, user_id)
    assert link_row is not None
    assert link_row.role_name == "Viewer"


def test_update_company_user_role_returns_not_found_for_missing_link(
    client, login_token
):
    company_id = _create_company(client, login_token)
    _create_role(
        client,
        login_token,
        company_id,
        {
            "name": "User",
            "description": "Standard user role for company-user role update tests.",
        },
    )
    user_id = _get_user_id("user.three@email.com")

    response = client.patch(
        f"/company/{company_id}/user/{user_id}",
        json={"role": "User"},
        headers={"Authorization": f"Bearer {login_token}"},
    )

    assert response.status_code == 404, response.text


def test_update_company_user_role_requires_role_field(client, login_token):
    company_id = _create_company(client, login_token)
    user_id = _add_user_to_company(
        client, login_token, company_id, "user.three@email.com"
    )

    response = client.patch(
        f"/company/{company_id}/user/{user_id}",
        json={},
        headers={"Authorization": f"Bearer {login_token}"},
    )

    assert response.status_code == 422, response.text
