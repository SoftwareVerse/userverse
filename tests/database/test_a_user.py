import pytest
from app.database.user import User
from app.database.base_model import RecordNotFoundError
from app.models.user.response_messages import UserResponseMessages
from app.repository.user import UserRepository
from app.utils.app_error import AppError


def test_create_user(test_session, test_user_data):
    user_data = test_user_data["create_user"]
    user = User.create(test_session, **user_data)
    assert user["email"] == user_data["email"]


def test_get_user_by_id(test_session, test_user_data):
    user_data = test_user_data["get_user_by_id"]
    created_user = User.create(test_session, **user_data)
    result = User.get_by_id(test_session, created_user["id"])
    assert result["email"] == user_data["email"]


def test_get_user_by_email(test_session, test_user_data):
    user_data = test_user_data["get_user_by_email"]
    created_user = User.create(test_session, **user_data)
    result = User.get_user_by_email(test_session, user_data["email"])
    assert result["email"] == created_user["email"]


def test_update_user(test_session, test_user_data):
    user_data = test_user_data["update_user"]
    created_user = User.create(
        test_session, email=user_data["email"], password=user_data["password"]
    )
    updated_user = User.update(
        test_session, created_user["id"], **user_data["update_fields"]
    )
    assert updated_user["first_name"] == user_data["update_fields"]["first_name"]


def test_delete_user(test_session, test_user_data):
    user_data = test_user_data["delete_user"]
    created_user = User.create(test_session, **user_data)
    response = User.delete(test_session, created_user["id"])
    assert "deleted" in response["message"]


def test_get_by_id_not_found(test_session, test_user_data):
    missing_id = test_user_data["not_found_tests"]["nonexistent_id"]
    with pytest.raises(RecordNotFoundError):
        User.get_by_id(test_session, missing_id)


def test_get_user_by_email_not_found(test_session, test_user_data):
    missing_email = test_user_data["not_found_tests"]["nonexistent_email"]
    with pytest.raises(ValueError):
        User.get_user_by_email(test_session, missing_email)


def test_update_json_field_primary_metadata(test_session, test_user_data):
    user_data = test_user_data["json_field_update"]
    created_user = User.create(
        test_session, email=user_data["email"], password=user_data["password"]
    )
    json_update = user_data["json_update"]
    updated_user = User.update_json_field(
        test_session,
        created_user["id"],
        json_update["column"],
        json_update["key"],
        json_update["value"],
    )
    assert (
        updated_user[json_update["column"]][json_update["key"]] == json_update["value"]
    )


def test_update_json_field_invalid_column(test_session, test_user_data):
    user_data = test_user_data["invalid_json_field"]
    created_user = User.create(
        test_session, email=user_data["email"], password=user_data["password"]
    )
    json_update = user_data["json_update"]
    # ✅ Fixed error message expectation:
    with pytest.raises(
        ValueError, match=f"Column {json_update['column']} does not exist on the model."
    ):
        User.update_json_field(
            test_session,
            created_user["id"],
            json_update["column"],
            json_update["key"],
            json_update["value"],
        )


def test_update_json_field_record_not_found(test_session, test_user_data):
    missing_id = test_user_data["not_found_tests"]["nonexistent_id"]
    json_update = test_user_data["json_field_update"]["json_update"]
    with pytest.raises(RecordNotFoundError):
        User.update_json_field(
            test_session,
            missing_id,
            json_update["column"],
            json_update["key"],
            json_update["value"],
        )


def test_create_user_rejects_duplicate_email(test_session, test_user_data):
    user_data = test_user_data["create_user"]
    User.create(test_session, **user_data)

    with pytest.raises(AppError) as exc_info:
        UserRepository(test_session).create_user(user_data)

    assert exc_info.value.status_code == 409
    assert (
        exc_info.value.detail["message"]
        == UserResponseMessages.USER_ALREADY_EXISTS.value
    )


def test_get_refresh_token_version_raises_when_user_missing(test_session):
    with pytest.raises(AppError) as exc_info:
        UserRepository(test_session).get_refresh_token_version(999)

    assert exc_info.value.status_code == 404
    assert (
        exc_info.value.detail["message"]
        == UserResponseMessages.USER_NOT_FOUND.value
    )


def test_get_refresh_token_version_defaults_to_zero_for_invalid_metadata(
    test_session, test_user_data
):
    user_data = test_user_data["create_user"] | {"email": "refresh-invalid@example.com"}
    created_user = User.create(test_session, **user_data)
    User.update_json_field(
        test_session,
        created_user["id"],
        "primary_meta_data",
        UserRepository.REFRESH_TOKEN_VERSION_KEY,
        "not-a-number",
    )

    version = UserRepository(test_session).get_refresh_token_version(created_user["id"])

    assert version == 0


def test_increment_refresh_token_version_updates_metadata(
    test_session, test_user_data
):
    user_data = test_user_data["create_user"] | {"email": "refresh-increment@example.com"}
    created_user = User.create(test_session, **user_data)
    repository = UserRepository(test_session)

    version = repository.increment_refresh_token_version(created_user["id"])

    assert version == 1
    updated_user = User.get_by_id(test_session, created_user["id"])
    assert (
        updated_user["primary_meta_data"][UserRepository.REFRESH_TOKEN_VERSION_KEY]
        == 1
    )
