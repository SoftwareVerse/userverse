import pytest
from app.database.company import Company
from app.database.role import Role


def test_create_admin_role(test_session, test_company_data, test_role_data):
    company = Company.create(test_session, **test_company_data["company_one"])
    role_data = test_role_data["admin_role"]

    role = Role.create(
        test_session,
        company_id=company["id"],
        name=role_data["name"],
        description=role_data["description"],
    )

    assert role["company_id"] == company["id"]
    assert role["name"] == "Admin"


def test_create_viewer_role_for_second_company(
    test_session, test_company_data, test_role_data
):
    company = Company.create(test_session, **test_company_data["company_two"])
    role_data = test_role_data["viewer_role"]

    role = Role.create(
        test_session,
        company_id=company["id"],
        name=role_data["name"],
        description=role_data["description"],
    )

    assert role["company_id"] == company["id"]
    assert role["name"] == "Viewer"


def test_same_role_name_different_companies(
    test_session, test_company_data, test_role_data
):
    company1 = Company.create(test_session, **test_company_data["company_one"])
    company2 = Company.create(test_session, **test_company_data["company_two"])
    role_data = test_role_data["viewer_role"]

    role1 = Role.create(
        test_session,
        company_id=company1["id"],
        name=role_data["name"],
        description="Company1",
    )
    role2 = Role.create(
        test_session,
        company_id=company2["id"],
        name=role_data["name"],
        description="Company2",
    )

    assert role1["name"] == role2["name"]
    assert role1["company_id"] != role2["company_id"]


def test_same_role_name_same_company_should_fail(
    test_session, test_company_data, test_role_data
):
    company = Company.create(test_session, **test_company_data["company_one"])
    role_data = test_role_data["admin_role"]

    Role.create(
        test_session,
        company_id=company["id"],
        name=role_data["name"],
        description="First Admin",
    )

    with pytest.raises(ValueError, match="Integrity error"):
        Role.create(
            test_session,
            company_id=company["id"],
            name=role_data["name"],
            description="Duplicate Admin",
        )


def test_update_role_description_by_filters(
    test_session, test_company_data, test_role_data
):
    company = Company.create(test_session, **test_company_data["company_one"])
    role_data = test_role_data["admin_role"]

    created = Role.create(
        test_session,
        company_id=company["id"],
        name=role_data["name"],
        description=role_data["description"],
    )

    updated = Role.update_by_filters(
        test_session,
        filters={"company_id": created["company_id"], "name": created["name"]},
        description=test_role_data["update_admin_role"]["description"],
    )

    assert updated["description"] == test_role_data["update_admin_role"]["description"]


def test_update_role_name_by_filters(test_session, test_company_data, test_role_data):
    company = Company.create(test_session, **test_company_data["company_one"])
    role_data = test_role_data["viewer_role"]

    created = Role.create(
        test_session,
        company_id=company["id"],
        name=role_data["name"],
        description=role_data["description"],
    )

    updated = Role.update_by_filters(
        test_session,
        filters={"company_id": created["company_id"], "name": created["name"]},
        name="Read-Only",
    )

    assert updated["name"] == "Read-Only"


def test_delete_role_by_filters(test_session, test_company_data, test_role_data):
    company = Company.create(test_session, **test_company_data["company_two"])
    role_data = test_role_data["viewer_role"]

    created = Role.create(
        test_session,
        company_id=company["id"],
        name=role_data["name"],
        description=role_data["description"],
    )

    deleted = Role.delete_by_filters(
        test_session,
        filters={"company_id": created["company_id"], "name": created["name"]},
    )

    assert "deleted" in deleted["message"]
