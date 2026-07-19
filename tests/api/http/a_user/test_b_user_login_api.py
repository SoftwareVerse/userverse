from app.models.user.response_messages import UserResponseMessages
from app.models.user.account_status import UserAccountStatus
from app.configs import settings
from app.repository.database.session_manager import DatabaseSessionManager
from app.repository.database.tables import User
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


def _set_user_status(email: str, status: str) -> None:
    db = DatabaseSessionManager()
    session = db.session_object()
    try:
        user_row = session.query(User).filter_by(email=email).one()
        metadata = dict(user_row.primary_meta_data or {})
        metadata["status"] = status
        user_row.primary_meta_data = metadata
        session.commit()
    finally:
        session.close()


def test_user_login_success(client, test_user_data, seed_verified_users):
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


def test_user_login_rejects_unverified_user(client, test_user_data, seed_users):
    user_one = test_user_data["user_one"]
    original_setting = settings.REQUIRE_EMAIL_VERIFICATION

    try:
        settings.REQUIRE_EMAIL_VERIFICATION = True
        _set_user_status(
            user_one["email"], UserAccountStatus.AWAITING_VERIFICATION.name_value
        )

        response = client.patch(
            "/user/login",
            headers=get_basic_auth_header(
                username=user_one["email"],
                password=user_one["password"],
            ),
        )

        assert response.status_code == 403
        assert (
            response.json()["detail"]["message"]
            == UserResponseMessages.USER_ACCOUNT_INACTIVE.value
        )
    finally:
        settings.REQUIRE_EMAIL_VERIFICATION = original_setting


def test_user_login_resends_verification_email_for_unverified_user(
    client, monkeypatch, test_user_data, seed_users
):
    sent_messages = []
    user_one = test_user_data["user_one"]
    monkeypatch.setattr(
        "app.services.user.basic_auth.MailService.send_template_email",
        lambda **kwargs: sent_messages.append(kwargs),
    )

    original_setting = settings.REQUIRE_EMAIL_VERIFICATION

    try:
        settings.REQUIRE_EMAIL_VERIFICATION = True
        _set_user_status(
            user_one["email"], UserAccountStatus.AWAITING_VERIFICATION.name_value
        )

        response = client.patch(
            "/user/login",
            headers=get_basic_auth_header(
                username=user_one["email"],
                password=user_one["password"],
            ),
        )

        assert response.status_code == 403
        assert (
            response.json()["detail"]["message"]
            == UserResponseMessages.USER_ACCOUNT_INACTIVE.value
        )
        assert sent_messages
        assert sent_messages[0]["to"] == user_one["email"]
        assert sent_messages[0]["context"]["mode"] == "verify"
    finally:
        settings.REQUIRE_EMAIL_VERIFICATION = original_setting
        _set_user_status(user_one["email"], UserAccountStatus.ACTIVE.name_value)


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
    _set_user_status(user_one["email"], UserAccountStatus.ACTIVE.name_value)
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
    _set_user_status(user_one["email"], UserAccountStatus.ACTIVE.name_value)
    token_data = _login_for_tokens(client, user_one)

    revoke_response = client.post(
        "/user/revoke",
        json={"refresh_token": token_data["refresh_token"]},
    )

    assert revoke_response.status_code == 200
    revoke_json = revoke_response.json()
    assert (
        revoke_json["message"] == UserResponseMessages.USER_REFRESH_TOKEN_REVOKED.value
    )
    assert revoke_json["data"]["revoked"] is True

    refresh_response = client.post(
        "/user/refresh",
        json={"refresh_token": token_data["refresh_token"]},
    )

    assert refresh_response.status_code == 401


def test_user_refresh_rejects_inactive_user(client, test_user_data, seed_verified_users):
    user_one = test_user_data["user_one"]
    token_data = _login_for_tokens(client, user_one)

    try:
        _set_user_status(user_one["email"], UserAccountStatus.SUSPENDED.name_value)

        response = client.post(
            "/user/refresh",
            json={"refresh_token": token_data["refresh_token"]},
        )

        assert response.status_code == 403
        assert (
            response.json()["detail"]["message"]
            == UserResponseMessages.USER_ACCOUNT_INACTIVE.value
        )
    finally:
        _set_user_status(user_one["email"], UserAccountStatus.ACTIVE.name_value)


def test_user_access_token_rejects_inactive_user(
    client, test_user_data, seed_verified_users
):
    user_one = test_user_data["user_one"]
    token_data = _login_for_tokens(client, user_one)

    try:
        _set_user_status(user_one["email"], UserAccountStatus.SUSPENDED.name_value)

        response = client.get(
            "/user/get",
            headers={"Authorization": f"Bearer {token_data['access_token']}"},
        )

        assert response.status_code == 403
        assert (
            response.json()["detail"]["message"]
            == UserResponseMessages.USER_ACCOUNT_INACTIVE.value
        )
    finally:
        _set_user_status(user_one["email"], UserAccountStatus.ACTIVE.name_value)


def test_user_login_allows_unverified_user_when_verification_disabled(
    client, monkeypatch, test_user_data, seed_users
):
    user_one = test_user_data["user_one"]
    monkeypatch.setattr(settings, "REQUIRE_EMAIL_VERIFICATION", False)
    try:
        _set_user_status(
            user_one["email"], UserAccountStatus.AWAITING_VERIFICATION.name_value
        )

        response = client.patch(
            "/user/login",
            headers=get_basic_auth_header(
                username=user_one["email"],
                password=user_one["password"],
            ),
        )

        assert response.status_code == 202
        token_data = response.json()["data"]

        protected_response = client.get(
            "/user/get",
            headers={"Authorization": f"Bearer {token_data['access_token']}"},
        )
        assert protected_response.status_code == 200
    finally:
        _set_user_status(user_one["email"], UserAccountStatus.ACTIVE.name_value)
