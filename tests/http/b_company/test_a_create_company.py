import pytest
from app.models.company.response_messages import CompanyResponseMessages


def test_a_create_company_one_success(client, test_company_data, login_token):
    """Test creating Company One using User One's token"""
    payload = {
        **test_company_data["company_one"],
        "address": test_company_data["json_field"]["value"],
    }
    headers = {"Authorization": f"Bearer {login_token}"}

    response = client.post("/company", json=payload, headers=headers)

    assert response.status_code in [200, 201]
    json_data = response.json()

    assert "message" in json_data
    assert json_data["message"] == CompanyResponseMessages.COMPANY_CREATED.value

    data = json_data["data"]
    assert data["name"] == payload["name"]
    assert data["email"] == payload["email"]
    assert data["address"]["city"] == payload["address"]["city"]
    assert data["address"]["country"] == payload["address"]["country"]


def test_b_create_company_two_success(client, test_company_data, login_token_user_two):
    """Test creating Company Two using User Two's token"""
    payload = {
        **test_company_data["company_two"],
        "address": test_company_data["json_field"]["value"],
    }
    headers = {"Authorization": f"Bearer {login_token_user_two}"}

    response = client.post("/company", json=payload, headers=headers)

    assert response.status_code in [200, 201]
    json_data = response.json()

    assert "message" in json_data
    assert json_data["message"] == CompanyResponseMessages.COMPANY_CREATED.value

    data = json_data["data"]
    assert data["name"] == payload["name"]
    assert data["email"] == payload["email"]
    assert data["address"]["city"] == payload["address"]["city"]
    assert data["address"]["country"] == payload["address"]["country"]


def test_c_create_company_one_again_should_fail(client, test_company_data, login_token):
    """Attempt to create Company One again — should fail due to duplicate email"""
    payload = {
        **test_company_data["company_one"],
        "address": test_company_data["json_field"]["value"],
    }
    headers = {"Authorization": f"Bearer {login_token}"}

    with pytest.raises(ValueError):
        client.post("/company", json=payload, headers=headers)
