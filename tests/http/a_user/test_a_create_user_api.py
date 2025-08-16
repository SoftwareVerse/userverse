import pytest
from app.models.user.response_messages import UserResponseMessages
from tests.utils.basic_auth import get_basic_auth_header

BASE_URL = "/user/create"

def test_a_create_user_one_success(client, test_user_data):
    """Test user creation with valid payload (user one)"""
    use_one = test_user_data["user_one"]
    payload = {
        "first_name": use_one["first_name"],
        "last_name": use_one["last_name"],
        "phone_number": use_one["phone_number"],
    }
    response = client.post(
        BASE_URL,
        json=payload,
        headers=get_basic_auth_header(
            username=use_one["email"],
            password=use_one["password"],
        ),
    )
    assert response.status_code in [200, 201]
    json_data = response.json()

    # Adjusted based on your actual API response structure
    assert "message" in json_data
    assert json_data["message"] == UserResponseMessages.USER_CREATED.value

    user_data = json_data["data"]
    assert "id" in user_data
    assert user_data["email"] == use_one["email"]
    assert user_data["first_name"] == use_one["first_name"]
    assert user_data["last_name"] == use_one["last_name"]


def test_b_create_user_two_success_and_unique_key_fail(client, test_user_data):
    """Test user creation with valid payload (user two), and then attempt to create the same user again"""
    use_two = test_user_data["user_two"]
    payload = {
        "first_name": use_two["first_name"],
        "last_name": use_two["last_name"],
        "phone_number": use_two["phone_number"],
    }
    response = client.post(
        BASE_URL,
        json=payload,
        headers=get_basic_auth_header(
            username=use_two["email"],
            password=use_two["password"],
        ),
    )
    assert response.status_code in [200, 201]
    json_data = response.json()

    # Adjusted based on your actual API response structure
    assert "message" in json_data
    assert json_data["message"] == UserResponseMessages.USER_CREATED.value

    user_data = json_data["data"]
    assert "id" in user_data
    assert user_data["email"] == use_two["email"]
    assert user_data["first_name"] == use_two["first_name"]
    assert user_data["last_name"] == use_two["last_name"]


def test_c_create_user_three_success(client, test_user_data):
    """Test user creation with valid payload (user one)"""
    use_one = test_user_data["user_three"]
    payload = {
        "first_name": use_one["first_name"],
        "last_name": use_one["last_name"],
        "phone_number": use_one["phone_number"],
    }
    response = client.post(
        BASE_URL,
        json=payload,
        headers=get_basic_auth_header(
            username=use_one["email"],
            password=use_one["password"],
        ),
    )
    assert response.status_code in [200, 201]
    json_data = response.json()

    # Adjusted based on your actual API response structure
    assert "message" in json_data
    assert json_data["message"] == UserResponseMessages.USER_CREATED.value

    user_data = json_data["data"]
    assert "id" in user_data
    assert user_data["email"] == use_one["email"]
    assert user_data["first_name"] == use_one["first_name"]
    assert user_data["last_name"] == use_one["last_name"]


def test_c_create_user_two_fail(client, test_user_data):
    """Test user creation failure when the same user is created again"""
    use_two = test_user_data["user_two"]
    payload = {
        "first_name": use_two["first_name"],
        "last_name": use_two["last_name"],
        "phone_number": use_two["phone_number"],
    }
    # Attempt to create the same user again
    with pytest.raises(ValueError):

        client.post(
            BASE_URL,
            json=payload,
            headers=get_basic_auth_header(
                username=use_two["email"],
                password=use_two["password"],
            ),
        )


def test_d_create_user_invalid_phone_should_fail(client, test_user_data):
    """Test user creation failure when phone number is invalid"""
    data = test_user_data["invalid_phone"]
    user = test_user_data["user_two"]
    headers = get_basic_auth_header(username=user["email"], password=user["password"])
    response = client.post(BASE_URL, json=data, headers=headers)
    assert response.status_code in [400, 422]
    json_data = response.json()
    assert "message" in json_data or "detail" in json_data
