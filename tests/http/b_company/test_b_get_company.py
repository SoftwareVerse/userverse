import pytest
from app.models.company.response_messages import CompanyResponseMessages
from app.database.base_model import RecordNotFoundError


def test_a_get_company_one_by_id_success(client, login_token):
    """Test creating Company One using User One's token"""
    headers = {"Authorization": f"Bearer {login_token}"}
    response = client.get(f"/company?company_id={1}", headers=headers)
    #
    assert response.status_code in [200, 201]
    json_data = response.json()
    #
    assert "message" in json_data
    assert json_data["message"] == CompanyResponseMessages.COMPANY_FOUND.value
    assert "data" in json_data
    assert json_data["data"]["id"] == 1
    assert json_data["data"]["name"] == "Company One"
    assert json_data["data"]["email"] == "company.one@email.com"


def test_b_get_company_one_by_email_success(client, login_token, test_company_data):
    """Test creating Company One using User One's token"""
    headers = {"Authorization": f"Bearer {login_token}"}
    company_email = test_company_data["company_one"]["email"]
    response = client.get(f"/company?email={company_email}", headers=headers)
    assert response.status_code in [200, 201]
    #
    json_data = response.json()
    assert "message" in json_data
    assert json_data["message"] == CompanyResponseMessages.COMPANY_FOUND.value
    assert "data" in json_data
    assert json_data["data"]["id"] == 1


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


def test_e_get_company_without_associated(client, login_token):
    """Test getting a company that you are not associated with"""
    headers = {"Authorization": f"Bearer {login_token}"}
    response = client.get("/company?company_id=2", headers=headers)

    assert response.status_code == 403
    json_data = response.json()
    #
    assert "detail" in json_data
    assert (
        json_data["detail"]["message"]
        == CompanyResponseMessages.UNAUTHORIZED_COMPANY_ACCESS.value
    )
    assert "error" in json_data["detail"]
