from dataclasses import dataclass
from enum import Enum
from uuid import NAMESPACE_URL, UUID, uuid5

SYSTEM_PERMISSION_NAMESPACE = uuid5(
    NAMESPACE_URL,
    "https://userverse.softwareverse.co.za/system-permissions",
)


class SystemPermission(str, Enum):
    COMPANY_READ = "company.read"
    COMPANY_UPDATE = "company.update"
    COMPANY_DELETE = "company.delete"
    COMPANY_MEMBERS_READ = "company.members.read"
    COMPANY_MEMBERS_ADD = "company.members.add"
    COMPANY_MEMBERS_ROLE_UPDATE = "company.members.role.update"
    COMPANY_MEMBERS_REMOVE = "company.members.remove"
    COMPANY_ROLES_READ = "company.roles.read"
    COMPANY_ROLES_ASSIGN = "company.roles.assign"
    COMPANY_ROLES_UNASSIGN = "company.roles.unassign"
    COMPANY_PERMISSIONS_READ = "company.permissions.read"
    COMPANY_PERMISSIONS_CREATE = "company.permissions.create"
    COMPANY_PERMISSIONS_UPDATE = "company.permissions.update"
    COMPANY_PERMISSIONS_DELETE = "company.permissions.delete"
    COMPANY_PERMISSIONS_ASSIGN = "company.permissions.assign"
    COMPANY_PERMISSIONS_UNASSIGN = "company.permissions.unassign"

    @property
    def permission_id(self) -> UUID:
        return uuid5(SYSTEM_PERMISSION_NAMESPACE, self.value)


@dataclass(frozen=True)
class SystemPermissionDefinition:
    permission: SystemPermission
    description: str
    default_roles: frozenset[str]

    @property
    def id(self) -> UUID:
        return self.permission.permission_id

    @property
    def name(self) -> str:
        return self.permission.value


OWNER = "Owner"
ADMINISTRATOR = "Administrator"
VIEWER = "Viewer"
OWNER_AND_ADMINISTRATOR = frozenset({OWNER, ADMINISTRATOR})
ALL_DEFAULT_ROLES = frozenset({OWNER, ADMINISTRATOR, VIEWER})

SYSTEM_PERMISSION_DEFINITIONS = (
    SystemPermissionDefinition(
        SystemPermission.COMPANY_READ,
        "Read company details.",
        ALL_DEFAULT_ROLES,
    ),
    SystemPermissionDefinition(
        SystemPermission.COMPANY_UPDATE,
        "Update company details.",
        OWNER_AND_ADMINISTRATOR,
    ),
    SystemPermissionDefinition(
        SystemPermission.COMPANY_DELETE,
        "Delete a company.",
        frozenset({OWNER}),
    ),
    SystemPermissionDefinition(
        SystemPermission.COMPANY_MEMBERS_READ,
        "Read company members.",
        ALL_DEFAULT_ROLES,
    ),
    SystemPermissionDefinition(
        SystemPermission.COMPANY_MEMBERS_ADD,
        "Add members to a company.",
        OWNER_AND_ADMINISTRATOR,
    ),
    SystemPermissionDefinition(
        SystemPermission.COMPANY_MEMBERS_ROLE_UPDATE,
        "Update a company member's role.",
        OWNER_AND_ADMINISTRATOR,
    ),
    SystemPermissionDefinition(
        SystemPermission.COMPANY_MEMBERS_REMOVE,
        "Remove members from a company.",
        OWNER_AND_ADMINISTRATOR,
    ),
    SystemPermissionDefinition(
        SystemPermission.COMPANY_ROLES_READ,
        "Read roles enabled for a company.",
        OWNER_AND_ADMINISTRATOR,
    ),
    SystemPermissionDefinition(
        SystemPermission.COMPANY_ROLES_ASSIGN,
        "Enable a global role for a company.",
        OWNER_AND_ADMINISTRATOR,
    ),
    SystemPermissionDefinition(
        SystemPermission.COMPANY_ROLES_UNASSIGN,
        "Disable a global role for a company.",
        OWNER_AND_ADMINISTRATOR,
    ),
    SystemPermissionDefinition(
        SystemPermission.COMPANY_PERMISSIONS_READ,
        "Read company permissions and effective role permissions.",
        OWNER_AND_ADMINISTRATOR,
    ),
    SystemPermissionDefinition(
        SystemPermission.COMPANY_PERMISSIONS_CREATE,
        "Create company permissions.",
        OWNER_AND_ADMINISTRATOR,
    ),
    SystemPermissionDefinition(
        SystemPermission.COMPANY_PERMISSIONS_UPDATE,
        "Update company permissions.",
        OWNER_AND_ADMINISTRATOR,
    ),
    SystemPermissionDefinition(
        SystemPermission.COMPANY_PERMISSIONS_DELETE,
        "Delete company permissions.",
        OWNER_AND_ADMINISTRATOR,
    ),
    SystemPermissionDefinition(
        SystemPermission.COMPANY_PERMISSIONS_ASSIGN,
        "Assign company permissions to company roles.",
        OWNER_AND_ADMINISTRATOR,
    ),
    SystemPermissionDefinition(
        SystemPermission.COMPANY_PERMISSIONS_UNASSIGN,
        "Remove company permissions from company roles.",
        OWNER_AND_ADMINISTRATOR,
    ),
)

SYSTEM_PERMISSION_BY_ID = {
    definition.id: definition for definition in SYSTEM_PERMISSION_DEFINITIONS
}
SYSTEM_PERMISSION_BY_NAME = {
    definition.name: definition for definition in SYSTEM_PERMISSION_DEFINITIONS
}


def is_system_permission_id(permission_id: UUID) -> bool:
    return permission_id in SYSTEM_PERMISSION_BY_ID
