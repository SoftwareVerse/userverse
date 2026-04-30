import pytest

from app.database.association_user_company import AssociationUserCompany
from app.database.company import Company
from app.database.role import Role
from app.database.user import User
from app.models.user.account_status import UserAccountStatus
from app.models.user.user import UserReadModel
from app.utils.app_error import AppError


def _acting_user(*, user_id: int) -> UserReadModel:
    return UserReadModel(
        id=user_id,
        first_name="Admin",
        last_name="User",
        email="admin@example.com",
        phone_number="1234567890",
        status=UserAccountStatus.ACTIVE.name_value,
        is_superuser=True,
    )


def test_is_user_linked_to_company_supports_role_filter(
    test_session, test_company_data, test_user_data, test_role_data
):
    company = Company.create(test_session, **test_company_data["company_one"])
    user = User.create(test_session, **test_user_data["create_user"])
    role = Role.create(
        test_session,
        company_id=company["id"],
        name=test_role_data["admin_role"]["name"],
        description=test_role_data["admin_role"]["description"],
    )
    AssociationUserCompany.create(
        test_session, user_id=user["id"], company_id=company["id"], role_name=role["name"]
    )

    assert AssociationUserCompany.is_user_linked_to_company(
        test_session, user["id"], company["id"], role["name"]
    ) is True
    assert AssociationUserCompany.is_user_linked_to_company(
        test_session, user["id"], company["id"], "Viewer"
    ) is False


def test_link_user_rejects_duplicate_active_link(
    test_session, test_company_data, test_user_data, test_role_data
):
    company = Company.create(test_session, **test_company_data["company_one"])
    user = User.create(test_session, **test_user_data["create_user"])
    role = Role.create(
        test_session,
        company_id=company["id"],
        name=test_role_data["admin_role"]["name"],
        description=test_role_data["admin_role"]["description"],
    )
    acting_user = _acting_user(user_id=999)
    AssociationUserCompany.link_user(
        test_session, company["id"], user["id"], role["name"], acting_user
    )

    with pytest.raises(ValueError, match="User is already linked"):
        AssociationUserCompany.link_user(
            test_session, company["id"], user["id"], role["name"], acting_user
        )


def test_unlink_user_rejects_missing_link(
    test_session, test_company_data
):
    company = Company.create(test_session, **test_company_data["company_one"])

    with pytest.raises(AppError, match="User has already been removed"):
        AssociationUserCompany.unlink_user(
            test_session, company["id"], 1, _acting_user(user_id=999)
        )


def test_unlink_user_rejects_self_removal_for_administrator(
    test_session, test_company_data, test_user_data, test_role_data
):
    company = Company.create(test_session, **test_company_data["company_one"])
    user = User.create(test_session, **test_user_data["create_user"])
    role = Role.create(
        test_session,
        company_id=company["id"],
        name="Administrator",
        description=test_role_data["admin_role"]["description"],
    )
    AssociationUserCompany.link_user(
        test_session, company["id"], user["id"], role["name"], _acting_user(user_id=999)
    )

    with pytest.raises(AppError, match="You cannot remove super admin from company."):
        AssociationUserCompany.unlink_user(
            test_session, company["id"], user["id"], _acting_user(user_id=user["id"])
        )
