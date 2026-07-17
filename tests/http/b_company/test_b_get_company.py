import pytest
from app.database.company import Company
from app.database.session_manager import DatabaseSessionManager
from app.models.company.response_messages import CompanyResponseMessages
from app.database.base_model import RecordNotFoundError


def _get_company_id_by_email(email: str) -> int:
    db = DatabaseSessionManager()
    session = db.session_object()
    try:
        company = session.query(Company).filter_by(email=email.lower()).first()
        assert company is not None
        return company.id
    finally:
        session.close()


def test_a_get_company_one_by_id_success(
    client, login_token, test_company_data, seed_companies
):
    """Test creating Company One using User One's token"""
    company_id = _get_company_id_by_email(test_company_data["company_one"]["email"])
    headers = {"Authorization": f"Bearer {login_token}"}
    response = client.get(f"/company?company_id={company_id}", headers=headers)
    #
    assert response.status_code in [200, 201]
    json_data = response.json()
    #
    assert "message" in json_data
    assert json_data["message"] == CompanyResponseMessages.COMPANY_FOUND.value
    assert "data" in json_data
    assert json_data["data"]["id"] == company_id
    assert json_data["data"]["name"] == "Company One"
    assert json_data["data"]["email"] == "company.one@email.com"


def test_b_get_company_one_by_email_success(
    client, login_token, test_company_data, seed_companies
):
    """Test creating Company One using User One's token"""
    headers = {"Authorization": f"Bearer {login_token}"}
    company_email = test_company_data["company_one"]["email"]
    company_id = _get_company_id_by_email(company_email)
    response = client.get(f"/company?email={company_email}", headers=headers)
    assert response.status_code in [200, 201]
    #
    json_data = response.json()
    assert "message" in json_data
    assert json_data["message"] == CompanyResponseMessages.COMPANY_FOUND.value
    assert "data" in json_data
    assert json_data["data"]["id"] == company_id


def test_c_get_company_invalid_args(client, login_token):
    """Test creating Company One using invalid args"""
    headers = {"Authorization": f"Bearer {login_token}"}
    response = client.get("/company", headers=headers)

    assert response.status_code in [400, 404]
    json_data = response.json()
    #
    assert "detail" in json_data
    assert (
        json_data["detail"]["message"]
        == CompanyResponseMessages.COMPANY_ID_OR_EMAIL_REQUIRED.value
    )
    assert "error" in json_data["detail"]


def test_d_get_company_not_found(client, login_token):
    """Test creating Company One using User One's token"""
    headers = {"Authorization": f"Bearer {login_token}"}

    with pytest.raises(RecordNotFoundError):
        client.get("/company?company_id=99999", headers=headers)


def test_e_get_company_without_associated(
    client, login_token, test_company_data, seed_companies
):
    """Test getting a company that you are not associated with"""
    headers = {"Authorization": f"Bearer {login_token}"}
    company_id = _get_company_id_by_email(test_company_data["company_two"]["email"])
    response = client.get(f"/company?company_id={company_id}", headers=headers)

    assert response.status_code == 403
    json_data = response.json()
    #
    assert "detail" in json_data
    assert (
        json_data["detail"]["message"]
        == CompanyResponseMessages.UNAUTHORIZED_COMPANY_ACCESS.value
    )
    assert "error" in json_data["detail"]
