from app.models.company.response_messages import CompanyResponseMessages


def test_a_update_company_one_success(client, login_token, test_company_data):
    """
    Test updating a company successfully.
    """
    headers = {"Authorization": f"Bearer {login_token}"}
    payload = {
        **test_company_data["update_company_one"],
        "address": test_company_data["json_field"]["updated_value"],
    }
    response = client.patch("/company/1", json=payload, headers=headers)
    #
    assert response.status_code in [200, 201]
    json_data = response.json()
    #
    assert "message" in json_data
    assert json_data["message"] == CompanyResponseMessages.COMPANY_UPDATED.value
    assert "data" in json_data
    assert json_data["data"]["id"] == 1
    assert json_data["data"]["name"] == test_company_data["update_company_one"]["name"]
    assert (
        json_data["data"]["address"]["city"]
        == test_company_data["json_field"]["updated_value"]["city"]
    )
    assert (
        json_data["data"]["address"]["country"]
        == test_company_data["json_field"]["updated_value"]["country"]
    )
    assert (
        json_data["data"]["address"]["street"]
        == test_company_data["json_field"]["updated_value"]["street"]
    )
    assert (
        json_data["data"]["address"]["postal_code"]
        == test_company_data["json_field"]["updated_value"]["postal_code"]
    )
    assert (
        json_data["data"]["address"]["state"]
        == test_company_data["json_field"]["updated_value"]["state"]
    )


def test_b_update_company_two_failure(client, login_token, test_company_data):
    """
    Test updating a company, but the user is not an admin.
    """
    headers = {"Authorization": f"Bearer {login_token}"}
    payload = {
        **test_company_data["update_company_one"],
        "address": test_company_data["json_field"]["updated_value"],
    }
    response = client.patch("/company/2", json=payload, headers=headers)
    #
    assert response.status_code in [400, 401, 403]
    json_data = response.json()
    #
    assert "detail" in json_data
    assert (
        json_data["detail"]["message"]
        == CompanyResponseMessages.UNAUTHORIZED_COMPANY_ACCESS.value
    )
    print(json_data)
