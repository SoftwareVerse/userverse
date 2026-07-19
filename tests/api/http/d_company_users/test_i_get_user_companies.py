import pytest
from app.models.company.response_messages import (
    CompanyUserResponseMessages,
)
from app.configs import settings
from app.models.user.account_status import UserAccountStatus
from app.repository.database.session_manager import DatabaseSessionManager
from app.repository.database.tables import User


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


@pytest.mark.parametrize(
    "login_token_key, query_params, expected_company_ids, expected_status",
    [
        ("login_token", "limit=10&page=1", {1}, 200),
        ("login_token", "limit=10&page=1&name=Test", set(), 200),  # updated
        ("login_token", "limit=10&page=1&email=notfound@example.com", set(), 200),
        ("login_token_user_two", "limit=10&page=1", {2}, 200),
        ("login_token_user_two", "limit=10&page=1&role_name=Admin", set(), 200),
        (
            "login_token_user_two",
            "limit=10&page=1&industry=Healthcare",
            set(),
            200,
        ),  # updated
    ],
)
def test_get_user_companies(
    client,
    login_token,
    login_token_user_two,
    seed_companies,
    verify_both_users,
    login_token_key,
    query_params,
    expected_company_ids,
    expected_status,
):
    """
    Test /user/companies with various filters and users.
    """
    token_map = {
        "login_token": login_token,
        "login_token_user_two": login_token_user_two,
    }

    headers = {
        "Authorization": f"Bearer {token_map[login_token_key]}",
        "accept": "application/json",
    }

    response = client.get(f"/user/companies?{query_params}", headers=headers)
    assert response.status_code == expected_status

    if expected_status == 200:
        json_data = response.json()
        assert (
            json_data["message"] == CompanyUserResponseMessages.GET_COMPANY_USERS.value
        )
        company_ids = {company["id"] for company in json_data["data"]["records"]}
        assert company_ids == expected_company_ids

        pagination = json_data["data"]["pagination"]
        assert pagination["limit"] == 10
        assert pagination["current_page"] == 1


def test_get_user_companies_allows_awaiting_verification_when_not_required(
    client, test_user_data, seed_companies, login_token
):
    user_one = test_user_data["user_one"]
    original_setting = settings.REQUIRE_EMAIL_VERIFICATION

    try:
        settings.REQUIRE_EMAIL_VERIFICATION = False
        _set_user_status(
            user_one["email"], UserAccountStatus.AWAITING_VERIFICATION.name_value
        )

        response = client.get(
            "/user/companies?limit=10&page=1",
            headers={
                "Authorization": f"Bearer {login_token}",
                "accept": "application/json",
            },
        )

        assert response.status_code == 200
        assert (
            response.json()["message"]
            == CompanyUserResponseMessages.GET_COMPANY_USERS.value
        )
    finally:
        settings.REQUIRE_EMAIL_VERIFICATION = original_setting
