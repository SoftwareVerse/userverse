from app.models.user.response_messages import UserResponseMessages
from tests.utils.basic_auth import get_basic_auth_header


def test_user_login_success(client, test_user_data):
    """Test user login with valid credentials"""
    user_one = test_user_data["user_one"]
    response = client.patch(
        "/user/login",
        headers=get_basic_auth_header(
            username=user_one["email"],
            password=user_one["password"],
        ),
    )
    assert response.status_code in [200, 201, 202]
    json_data = response.json()

    # Adjusted based on your actual API response structure
    assert "message" in json_data
    assert json_data["message"] == UserResponseMessages.USER_LOGGED_IN.value

    token_data = json_data["data"]
    assert "access_token" in token_data
    assert "refresh_token" in token_data
    assert "access_token_expiration" in token_data
    assert "refresh_token_expiration" in token_data
    assert "token_type" in token_data
    assert token_data["token_type"] == "bearer"


def test_user_login_invalid_credentials(client, test_user_data):
    """Test user login with invalid credentials"""
    user_one = test_user_data["user_one"]

    response = client.patch(
        "/user/login",
        headers=get_basic_auth_header(
            username=user_one["email"],
            password="wrong_password",
        ),
    )
    assert response.status_code == 401
    json_data = response.json()
    assert "detail" in json_data
    json_details = json_data["detail"]

    assert "message" in json_details
    assert "error" in json_details
    assert json_details["message"] == UserResponseMessages.INVALID_CREDENTIALS.value
