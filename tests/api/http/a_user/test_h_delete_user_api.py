from uuid import uuid4
from datetime import timedelta

from app.api.security.jwt import JWTManager
from app.models.security_messages import SecurityResponseMessages
from app.models.user.response_messages import UserResponseMessages
from app.repository.database.session_manager import DatabaseSessionManager
from app.repository.database.tables import User
from tests.utils.basic_auth import get_basic_auth_header

BASE_URL = "/user/me"


def _build_user_payload() -> dict:
    suffix = uuid4().hex
    return {
        "first_name": "Delete",
        "last_name": "Me",
        "phone_number": "0123456789",
        "email": f"delete-user-{suffix}@email.com",
        "password": "secureDelete123",
    }


def _create_user(client, user: dict) -> None:
    response = client.post(
        "/user/create",
        json={
            "first_name": user["first_name"],
            "last_name": user["last_name"],
            "phone_number": user["phone_number"],
        },
        headers=get_basic_auth_header(user["email"], user["password"]),
    )
    assert response.status_code in [200, 201], response.text


def _verify_user_account(client, email: str) -> None:
    token = JWTManager().sign_payload(
        {"sub": email, "type": "verification"},
        expires_delta=timedelta(minutes=60),
    )
    response = client.get(f"/user/verify?token={token}")
    assert response.status_code in [200, 201], response.text


def _login_for_access_token(client, user: dict) -> str:
    response = client.patch(
        "/user/login",
        headers=get_basic_auth_header(user["email"], user["password"]),
    )
    assert response.status_code in [200, 201, 202], response.text
    return response.json()["data"]["access_token"]


def _get_user_row(email: str):
    db = DatabaseSessionManager()
    session = db.session_object()
    try:
        return session.query(User).filter_by(email=email.lower()).first()
    finally:
        session.close()


def test_delete_user_account_success(client):
    user = _build_user_payload()
    _create_user(client, user)
    _verify_user_account(client, user["email"])
    access_token = _login_for_access_token(client, user)

    response = client.delete(
        BASE_URL,
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 200, response.text
    json_data = response.json()
    assert json_data["message"] == UserResponseMessages.USER_DELETED.value
    assert json_data["data"] is None

    user_row = _get_user_row(user["email"])
    assert user_row is not None
    assert user_row._closed_at is not None


def test_delete_user_account_rejects_invalid_token(client):
    response = client.delete(
        BASE_URL,
        headers={"Authorization": "Bearer invalid_token"},
    )

    assert response.status_code == 401, response.text
    assert (
        response.json()["detail"]["message"]
        == SecurityResponseMessages.INVALID_TOKEN.value
    )


def test_delete_user_account_blocks_login_after_deletion(client):
    user = _build_user_payload()
    _create_user(client, user)
    _verify_user_account(client, user["email"])
    access_token = _login_for_access_token(client, user)

    delete_response = client.delete(
        BASE_URL,
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert delete_response.status_code == 200, delete_response.text

    login_response = client.patch(
        "/user/login",
        headers=get_basic_auth_header(user["email"], user["password"]),
    )

    assert login_response.status_code == 404, login_response.text
    assert (
        login_response.json()["detail"]["message"]
        == UserResponseMessages.USER_NOT_FOUND.value
    )


def test_delete_user_account_rejects_repeat_delete_with_same_token(client):
    user = _build_user_payload()
    _create_user(client, user)
    _verify_user_account(client, user["email"])
    access_token = _login_for_access_token(client, user)

    first_response = client.delete(
        BASE_URL,
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert first_response.status_code == 200, first_response.text

    second_response = client.delete(
        BASE_URL,
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert second_response.status_code == 404, second_response.text
    assert (
        second_response.json()["detail"]["message"]
        == UserResponseMessages.USER_NOT_FOUND.value
    )
