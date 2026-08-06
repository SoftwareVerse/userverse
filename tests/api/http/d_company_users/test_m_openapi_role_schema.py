from app.main import create_app


def test_openapi_documents_nested_company_user_role_schema():
    schema = create_app().openapi()

    company_user_schema = schema["components"]["schemas"]["CompanyUserReadModel"]
    user_company_schema = schema["components"]["schemas"]["UserCompanyReadModel"]
    role_schema = schema["components"]["schemas"]["RoleReadModel"]
    users_get_schema = schema["paths"]["/company/{company_id}/users"]["get"][
        "responses"
    ]["200"]["content"]["application/json"]["schema"]
    user_companies_schema = schema["paths"]["/user/companies"]["get"]["responses"][
        "200"
    ]["content"]["application/json"]["schema"]

    assert "role_id" not in company_user_schema["properties"]
    assert "role_name" not in company_user_schema["properties"]
    assert company_user_schema["properties"]["role"] == {
        "$ref": "#/components/schemas/RoleReadModel"
    }
    assert "role_id" not in user_company_schema["properties"]
    assert "role_name" not in user_company_schema["properties"]
    assert user_company_schema["properties"]["role"] == {
        "$ref": "#/components/schemas/RoleReadModel"
    }
    assert role_schema["properties"]["permissions"] == {
        "items": {"type": "string"},
        "type": "array",
        "title": "Permissions",
    }
    assert (
        users_get_schema["$ref"]
        == "#/components/schemas/GenericResponseModel_PaginatedResponse_CompanyUserReadModel__"
    )
    assert (
        user_companies_schema["$ref"]
        == "#/components/schemas/GenericResponseModel_PaginatedResponse_UserCompanyReadModel__"
    )
