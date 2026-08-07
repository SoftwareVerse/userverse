import pytest
from unittest.mock import Mock

from sqlalchemy import event

from app.models.company.company import CompanyQueryParamsModel
from app.repository.company import CompanyRepository
from app.repository.database.tables import AssociationUserCompany
from app.repository.database.tables import Company
from app.repository.database.tables import Role
from app.repository.database.tables import User


def test_get_company_by_email_returns_company(test_session, test_company_data):
    company = Company.create(test_session, **test_company_data["company_one"])

    result = Company.get_company_by_email(test_session, company["email"])

    assert result["id"] == company["id"]


def test_get_company_by_email_raises_for_missing_company(test_session):
    with pytest.raises(
        ValueError, match="Company with email:missing@example.com, not found."
    ):
        Company.get_company_by_email(test_session, "missing@example.com")


def test_company_repository_get_user_companies_supports_description_filter(
    test_session,
):
    user = User.create(
        test_session,
        email="owner@example.com",
        password="secret",
        first_name="Owner",
    )
    company_one = Company.create(
        test_session,
        email="one@example.com",
        name="One",
        description="Finance focused team",
    )
    company_two = Company.create(
        test_session,
        email="two@example.com",
        name="Two",
        description="Retail team",
    )
    Role.create(
        test_session,
        company_id=company_one["id"],
        name="Owner",
        description="Owner role",
    )
    Role.create(
        test_session,
        company_id=company_two["id"],
        name="Owner",
        description="Owner role",
    )
    AssociationUserCompany.create(
        test_session,
        user_id=user["id"],
        company_id=company_one["id"],
        role_name="Owner",
    )
    AssociationUserCompany.create(
        test_session,
        user_id=user["id"],
        company_id=company_two["id"],
        role_name="Owner",
    )

    result = CompanyRepository(test_session).get_user_companies(
        user["id"],
        CompanyQueryParamsModel(limit=10, page=1, description="Finance"),
    )

    assert [company.email for company in result.records] == ["one@example.com"]
    assert result.records[0].role.name == "Owner"
    assert result.records[0].role.permissions == []


def test_company_repository_get_user_companies_returns_company_specific_roles(
    test_session,
):
    user = User.create(
        test_session,
        email="multi-role-user@example.com",
        password="secret",
        first_name="Role",
    )
    company_one = Company.create(
        test_session,
        email="role-one@example.com",
        name="Role One",
        description="First role company",
    )
    company_two = Company.create(
        test_session,
        email="role-two@example.com",
        name="Role Two",
        description="Second role company",
    )
    owner_role = Role.create(
        test_session,
        company_id=company_one["id"],
        name="Owner",
        description="Owner role",
    )
    viewer_role = Role.create(
        test_session,
        company_id=company_two["id"],
        name="Viewer",
        description="Viewer role",
    )
    AssociationUserCompany.create(
        test_session,
        user_id=user["id"],
        company_id=company_one["id"],
        role_name="Owner",
    )
    AssociationUserCompany.create(
        test_session,
        user_id=user["id"],
        company_id=company_two["id"],
        role_name="Viewer",
    )

    result = CompanyRepository(test_session).get_user_companies(
        user["id"],
        CompanyQueryParamsModel(limit=10, page=1),
    )

    roles_by_email = {company.email: company.role for company in result.records}
    assert roles_by_email["role-one@example.com"].model_dump() == {
        "id": str(owner_role["id"]),
        "name": "Owner",
        "description": "Owner role",
        "permissions": [],
    }
    assert roles_by_email["role-two@example.com"].model_dump() == {
        "id": str(viewer_role["id"]),
        "name": "Viewer",
        "description": "Viewer role",
        "permissions": [],
    }


def test_company_repository_get_user_companies_uses_fixed_select_count(test_session):
    user = User.create(
        test_session,
        email="query-count-user@example.com",
        password="secret",
        first_name="Query",
    )
    roles = [
        Role.create(
            test_session,
            company_id=Company.create(
                test_session,
                email=f"query-count-{index}@example.com",
                name=f"Query Count {index}",
                description=f"Query count company {index}",
            )["id"],
            name=role_name,
            description=f"{role_name} role",
        )
        for index, role_name in enumerate(["Owner", "Administrator", "Viewer"], 1)
    ]
    for index, role in enumerate(roles, 1):
        company = Company.get_company_by_email(
            test_session, f"query-count-{index}@example.com"
        )
        AssociationUserCompany.create(
            test_session,
            user_id=user["id"],
            company_id=company["id"],
            role_id=role["id"],
        )

    select_statements = []

    def record_select(conn, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith("SELECT"):
            select_statements.append(statement)

    event.listen(test_session.bind, "before_cursor_execute", record_select)
    try:
        result = CompanyRepository(test_session).get_user_companies(
            user["id"],
            CompanyQueryParamsModel(limit=10, page=1),
        )
    finally:
        event.remove(test_session.bind, "before_cursor_execute", record_select)

    assert len(result.records) == 3
    # Count + page + one bulk query per permission scope. The query count stays
    # constant as company memberships are added.
    assert len(select_statements) == 4


def test_company_repository_ensure_default_roles_updates_description(monkeypatch):
    session = Mock()
    repository = CompanyRepository(session)
    role = Role(name="Owner", description="Old role")
    query = Mock()
    query.filter.return_value.one_or_none.side_effect = [role, None, None]
    session.query.return_value = query
    session.commit = Mock()

    default_roles = repository._ensure_default_roles()

    assert role.description == "Full access to manage users and data"
    assert default_roles["Owner"] is role
    session.commit.assert_called_once()
