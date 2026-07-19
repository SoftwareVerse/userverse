from app.models.user.response_messages import UserResponseMessages
from tests.utils.basic_auth import get_basic_auth_header


def _login_for_tokens(client, user: dict) -> dict:
    response = client.patch(
        "/user/login",
        headers=get_basic_auth_header(
            username=user["email"],
            password=user["password"],
        ),
    )
    assert response.status_code in [200, 201, 202]
    return response.json()["data"]


def test_user_login_success(client, test_user_data, seed_users):
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


def test_user_login_invalid_credentials(client, test_user_data, seed_users):
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


def test_user_refresh_success(client, test_user_data, seed_users):
    user_one = test_user_data["user_one"]
    token_data = _login_for_tokens(client, user_one)

    response = client.post(
        "/user/refresh",
        json={"refresh_token": token_data["refresh_token"]},
    )

    assert response.status_code == 202
    json_data = response.json()
    assert json_data["message"] == UserResponseMessages.USER_TOKEN_REFRESHED.value
    refreshed_token_data = json_data["data"]
    assert refreshed_token_data["access_token"]
    assert refreshed_token_data["refresh_token"]
    assert refreshed_token_data["token_type"] == "bearer"


def test_user_revoke_blocks_old_refresh_token(client, test_user_data, seed_users):
    user_one = test_user_data["user_one"]
    token_data = _login_for_tokens(client, user_one)

    revoke_response = client.post(
        "/user/revoke",
        json={"refresh_token": token_data["refresh_token"]},
    )

    assert revoke_response.status_code == 200
    revoke_json = revoke_response.json()
    assert (
        revoke_json["message"]
        == UserResponseMessages.USER_REFRESH_TOKEN_REVOKED.value
    )
    assert revoke_json["data"]["revoked"] is True

    refresh_response = client.post(
        "/user/refresh",
        json={"refresh_token": token_data["refresh_token"]},
    )

    assert refresh_response.status_code == 401
