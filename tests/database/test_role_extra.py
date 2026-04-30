import pytest

from app.database.association_user_company import AssociationUserCompany
from app.database.company import Company
from app.database.role import Role
from app.database.user import User
from app.models.user.user import UserReadModel
from app.utils.app_error import AppError


def _deleted_by_user() -> UserReadModel:
    return UserReadModel(
        id=99,
        first_name="Admin",
        last_name="User",
        email="admin@example.com",
        phone_number="1234567890",
        status="Active",
        is_superuser=True,
    )


def test_role_belongs_to_company_returns_role_dict(
    test_session, test_company_data, test_role_data
):
    company = Company.create(test_session, **test_company_data["company_one"])
    role = Role.create(
        test_session,
        company_id=company["id"],
        name=test_role_data["admin_role"]["name"],
        description=test_role_data["admin_role"]["description"],
    )

    result = Role.role_belongs_to_company(test_session, company["id"], role["name"])

    assert result["name"] == role["name"]


def test_role_belongs_to_company_raises_when_role_missing(
    test_session, test_company_data
):
    company = Company.create(test_session, **test_company_data["company_one"])

    with pytest.raises(AppError, match="Role: Missing is not linked to the company"):
        Role.role_belongs_to_company(test_session, company["id"], "Missing")


def test_update_role_raises_when_role_missing(test_session):
    with pytest.raises(
        ValueError, match="Role with company_id=1 and name='Missing' not found."
    ):
        Role.update_role(test_session, 1, "Missing", new_name="Renamed")


def test_update_role_json_field_rejects_missing_role(test_session):
    with pytest.raises(
        ValueError, match="Role with company_id=1 and name='Missing' not found."
    ):
        Role.update_json_field(
            test_session, 1, "Missing", "primary_meta_data", "key", "value"
        )


def test_update_role_json_field_rejects_missing_column(
    test_session, test_company_data, test_role_data
):
    company = Company.create(test_session, **test_company_data["company_one"])
    role = Role.create(
        test_session,
        company_id=company["id"],
        name=test_role_data["admin_role"]["name"],
        description=test_role_data["admin_role"]["description"],
    )

    with pytest.raises(ValueError, match="Column 'missing' does not exist on Role."):
        Role.update_json_field(
            test_session, company["id"], role["name"], "missing", "key", "value"
        )


def test_update_role_json_field_rejects_non_dict_column(
    test_session, test_company_data, test_role_data
):
    company = Company.create(test_session, **test_company_data["company_one"])
    role = Role.create(
        test_session,
        company_id=company["id"],
        name=test_role_data["admin_role"]["name"],
        description=test_role_data["admin_role"]["description"],
    )

    with pytest.raises(ValueError, match="Column 'description' is not a JSON field."):
        Role.update_json_field(
            test_session, company["id"], role["name"], "description", "key", "value"
        )


def test_delete_role_and_reassign_users_rejects_same_replacement_name(test_session):
    with pytest.raises(ValueError, match="Cannot replace a role with itself."):
        Role.delete_role_and_reassign_users(
            test_session, 1, "Admin", "Admin", _deleted_by_user()
        )


def test_delete_role_and_reassign_users_rejects_missing_target_role(
    test_session, test_company_data
):
    company = Company.create(test_session, **test_company_data["company_one"])

    with pytest.raises(ValueError, match="Role 'Admin' not found."):
        Role.delete_role_and_reassign_users(
            test_session, company["id"], "Admin", "Viewer", _deleted_by_user()
        )


def test_delete_role_and_reassign_users_rejects_missing_replacement_role(
    test_session, test_company_data, test_role_data
):
    company = Company.create(test_session, **test_company_data["company_one"])
    Role.create(
        test_session,
        company_id=company["id"],
        name=test_role_data["admin_role"]["name"],
        description=test_role_data["admin_role"]["description"],
    )

    with pytest.raises(ValueError, match="Replacement role 'Viewer' not found."):
        Role.delete_role_and_reassign_users(
            test_session, company["id"], "Admin", "Viewer", _deleted_by_user()
        )


def test_delete_role_and_reassign_users_soft_deletes_and_reassigns_users(
    test_session, test_company_data, test_role_data, test_user_data
):
    company = Company.create(test_session, **test_company_data["company_one"])
    admin_role = Role.create(
        test_session,
        company_id=company["id"],
        name=test_role_data["admin_role"]["name"],
        description=test_role_data["admin_role"]["description"],
    )
    viewer_role = Role.create(
        test_session,
        company_id=company["id"],
        name=test_role_data["viewer_role"]["name"],
        description=test_role_data["viewer_role"]["description"],
    )
    user = User.create(test_session, **test_user_data["create_user"])
    AssociationUserCompany.create(
        test_session,
        user_id=user["id"],
        company_id=company["id"],
        role_name=admin_role["name"],
    )

    result = Role.delete_role_and_reassign_users(
        test_session,
        company["id"],
        admin_role["name"],
        viewer_role["name"],
        _deleted_by_user(),
    )

    updated_link = test_session.query(AssociationUserCompany).one()
    deleted_role = (
        test_session.query(Role)
        .filter_by(company_id=company["id"], name=admin_role["name"])
        .one()
    )
    assert result["users_reassigned"] == 1
    assert updated_link.role_name == viewer_role["name"]
    assert deleted_role.primary_meta_data["deleted_by"]["email"] == "admin@example.com"
    assert deleted_role._closed_at is not None
