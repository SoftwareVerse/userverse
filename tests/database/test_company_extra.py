import pytest
from unittest.mock import Mock

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
