from app.models.security_messages import SecurityResponseMessages
from app.models.user.response_messages import UserResponseMessages

BASE_URL = "/user/update"

def test_a_update_user_success(client, login_token_user_two, test_user_data):
    """Test updating user information successfully."""
    user_two = test_user_data["user_two"]
    update_data = test_user_data["update_user"]
    # Assuming the login_token is valid and corresponds to user_one
    headers = {"Authorization": f"Bearer {login_token_user_two}"}
    updated_first_name = user_two["first_name"] + " " + update_data["first_name"]
    updated_last_name = user_two["last_name"] + " " + update_data["last_name"]
    payload = {
        "first_name": updated_first_name,
        "last_name": updated_last_name,
        "password": update_data["password"],
    }
    response = client.patch(
        BASE_URL,
        json=payload,
        headers=headers,
    )
    assert response.status_code == 201
    json_response = response.json()
    assert "data" in json_response
    assert "email" in json_response["data"]
    assert "first_name" in json_response["data"]
    assert "last_name" in json_response["data"]
    assert "phone_number" in json_response["data"]
    assert json_response["message"] == UserResponseMessages.USER_UPDATED.value
    # Check if the user data matches the expected data
    assert json_response["data"]["email"] == user_two["email"]
    assert json_response["data"]["first_name"] == updated_first_name
    assert json_response["data"]["last_name"] == updated_last_name
    assert json_response["data"]["phone_number"] == user_two["phone_number"]


def test_b_update_user_fail_with_invalid_token(client, test_user_data):
    """Test updating user information with an invalid token."""
    user_two = test_user_data["user_two"]
    update_data = test_user_data["update_user"]
    # Assuming the login_token is valid and corresponds to user_one
    headers = {"Authorization": "Bearer invalid_token"}
    updated_first_name = user_two["first_name"] + " " + update_data["first_name"]
    updated_last_name = user_two["last_name"] + " " + update_data["last_name"]
    payload = {
        "first_name": updated_first_name,
        "last_name": updated_last_name,
        "password": update_data["password"],
    }
    response = client.patch(
        BASE_URL,
        json=payload,
        headers=headers,
    )
    assert response.status_code == 401
    json_response = response.json()
    assert "detail" in json_response
    json_details = json_response["detail"]

    assert "message" in json_details
    assert "error" in json_details
    assert json_details["message"] == SecurityResponseMessages.INVALID_TOKEN.value
