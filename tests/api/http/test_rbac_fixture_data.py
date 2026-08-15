from app.models.company.roles import CompanyDefaultRoles
from app.models.system_permissions import SYSTEM_PERMISSION_DEFINITIONS


def test_company_rbac_fixture_matches_default_role_registry(test_company_data):
    fixture_roles = test_company_data["default_roles"]
    expected_roles = {role.name_value: role.description for role in CompanyDefaultRoles}

    assert {
        role["name"]: role["description"] for role in fixture_roles.values()
    } == expected_roles

    for role in fixture_roles.values():
        assert set(role["permissions"]) == {
            definition.name
            for definition in SYSTEM_PERMISSION_DEFINITIONS
            if role["name"] in definition.default_roles
        }


def test_global_rbac_fixture_has_unique_role_and_permission_names(
    test_global_rbac_data,
):
    roles = test_global_rbac_data["roles"]
    permissions = test_global_rbac_data["permissions"]
    role_names = [role["name"] for role in roles.values()]
    permission_names = [permission["name"] for permission in permissions.values()]

    assert len(role_names) == len(set(role_names))
    assert len(permission_names) == len(set(permission_names))
    assert all("description" in role for role in roles.values())
    assert all("description" in permission for permission in permissions.values())
    assert set(permission_names).isdisjoint(
        definition.name for definition in SYSTEM_PERMISSION_DEFINITIONS
    )
