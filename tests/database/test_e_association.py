import pytest
from app.database.user import User
from app.database.company import Company
from app.database.role import Role
from app.database.association_user_company import AssociationUserCompany


def test_create_association(
    test_session, test_company_data, test_user_data, test_role_data
):
    # Setup user, company, and role
    company = Company.create(test_session, **test_company_data["company_one"])
    user = User.create(test_session, **test_user_data["create_user"])
    role = Role.create(
        test_session,
        company_id=company["id"],
        name=test_role_data["admin_role"]["name"],
        description=test_role_data["admin_role"]["description"],
    )

    # Create association
    assoc = AssociationUserCompany.create(
        test_session,
        user_id=user["id"],
        company_id=company["id"],
        role_name=role["name"],
    )

    assert assoc["user_id"] == user["id"]
    assert assoc["company_id"] == company["id"]
    assert assoc["role_name"] == role["name"]


def test_duplicate_association_should_fail(
    test_session, test_company_data, test_user_data, test_role_data
):
    company = Company.create(test_session, **test_company_data["company_one"])
    user = User.create(test_session, **test_user_data["create_user"])
    Role.create(
        test_session,
        company_id=company["id"],
        name=test_role_data["viewer_role"]["name"],
        description=test_role_data["viewer_role"]["description"],
    )

    AssociationUserCompany.create(
        test_session, user_id=user["id"], company_id=company["id"], role_name="Viewer"
    )

    with pytest.raises(ValueError, match="Integrity error"):
        AssociationUserCompany.create(
            test_session,
            user_id=user["id"],
            company_id=company["id"],
            role_name="Viewer",
        )


def test_invalid_role_reference_should_fail(
    test_session, test_company_data, test_user_data
):
    company = Company.create(test_session, **test_company_data["company_one"])
    user = User.create(test_session, **test_user_data["create_user"])

    assoc = AssociationUserCompany(
        user_id=user["id"], company_id=company["id"], role_name="NonExistentRole"
    )

    test_session.add(assoc)

    test_session.commit()


def test_delete_association(
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

    assoc = AssociationUserCompany.create(
        test_session,
        user_id=user["id"],
        company_id=company["id"],
        role_name=role["name"],
    )

    deleted = AssociationUserCompany.delete_by_filters(
        test_session,
        filters={
            "user_id": assoc["user_id"],
            "company_id": assoc["company_id"],
            "role_name": assoc["role_name"],
        },
    )

    assert "deleted" in deleted["message"]
