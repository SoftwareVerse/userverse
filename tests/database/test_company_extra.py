import pytest

from app.database.company import Company


def test_get_company_by_email_returns_company(test_session, test_company_data):
    company = Company.create(test_session, **test_company_data["company_one"])

    result = Company.get_company_by_email(test_session, company["email"])

    assert result["id"] == company["id"]


def test_get_company_by_email_raises_for_missing_company(test_session):
    with pytest.raises(ValueError, match="Company with email:missing@example.com, not found."):
        Company.get_company_by_email(test_session, "missing@example.com")
