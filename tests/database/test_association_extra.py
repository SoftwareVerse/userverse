from uuid import UUID, uuid4

import pytest

from app.repository.database.tables import AssociationUserCompany
from app.repository.database.tables import Company
from app.repository.database.tables import Role
from app.repository.database.tables import User
from app.models.user.account_status import UserAccountStatus
from app.models.user.user import UserReadModel
from app.utils.app_error import AppError


def _acting_user(*, user_id: UUID) -> UserReadModel:
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
        test_session,
        user_id=user["id"],
        company_id=company["id"],
        role_name=role["name"],
    )

    assert (
        AssociationUserCompany.is_user_linked_to_company(
            test_session, user["id"], company["id"], role["name"]
        )
        is True
    )
    assert (
        AssociationUserCompany.is_user_linked_to_company(
            test_session, user["id"], company["id"], "Viewer"
        )
        is False
    )


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
    acting_user = _acting_user(user_id=uuid4())
    AssociationUserCompany.link_user(
        test_session, company["id"], user["id"], role["name"], acting_user
    )

    with pytest.raises(ValueError, match="User is already linked"):
        AssociationUserCompany.link_user(
            test_session, company["id"], user["id"], role["name"], acting_user
        )


def test_unlink_user_rejects_missing_link(test_session, test_company_data):
    company = Company.create(test_session, **test_company_data["company_one"])

    with pytest.raises(AppError, match="User has already been removed"):
        AssociationUserCompany.unlink_user(
            test_session, company["id"], uuid4(), _acting_user(user_id=uuid4())
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
        test_session,
        company["id"],
        user["id"],
        role["name"],
        _acting_user(user_id=uuid4()),
    )

    with pytest.raises(AppError, match="You cannot remove super admin from company."):
        AssociationUserCompany.unlink_user(
            test_session, company["id"], user["id"], _acting_user(user_id=user["id"])
        )


def test_unlink_user_soft_deletes_link_and_records_removed_by_metadata(
    test_session, test_company_data, test_user_data, test_role_data
):
    company = Company.create(test_session, **test_company_data["company_one"])
    user = User.create(test_session, **test_user_data["create_user"])
    role = Role.create(
        test_session,
        company_id=company["id"],
        name=test_role_data["viewer_role"]["name"],
        description=test_role_data["viewer_role"]["description"],
    )
    added_by = _acting_user(user_id=uuid4())
    removed_by = _acting_user(user_id=uuid4())

    AssociationUserCompany.link_user(
        test_session, company["id"], user["id"], role["name"], added_by
    )

    unlinked = AssociationUserCompany.unlink_user(
        test_session, company["id"], user["id"], removed_by
    )

    assert unlinked._closed_at is not None
    assert unlinked.primary_meta_data["removed_by"]["id"] == str(removed_by.id)
    assert unlinked.primary_meta_data["removed_by"]["email"] == removed_by.email
