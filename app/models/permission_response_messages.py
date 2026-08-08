from enum import Enum


class PermissionResponseMessages(str, Enum):
    CREATED = "Permission has been created successfully."
    FOUND = "Permissions retrieved successfully."
    UPDATED = "Permission has been updated successfully."
    DELETED = "Permission has been deleted successfully."
    ASSIGNED = "Permission has been assigned successfully."
    UNASSIGNED = "Permission has been unassigned successfully."
    NOT_FOUND = "No permission found with the given identifier."
    ALREADY_EXISTS = "A permission with the same name already exists."
    ALREADY_ASSIGNED = "Permission is already assigned to the role."
    ASSIGNMENT_NOT_FOUND = "Permission is not assigned to the role."
    MANAGEMENT_FORBIDDEN = "Access denied. You cannot manage these permissions."
    SYSTEM_PERMISSION_PROTECTED = (
        "System permission identities cannot be renamed or deleted."
    )
    SYSTEM_PERMISSION_CONFLICT = (
        "A reserved system permission name or identifier is already in use."
    )


class PlatformRoleResponseMessages(str, Enum):
    FOUND = "Platform roles retrieved successfully."
    ASSIGNED = "Platform role has been assigned successfully."
    UNASSIGNED = "Platform role has been unassigned successfully."
    ALREADY_ASSIGNED = "Platform role is already assigned to the user."
    ASSIGNMENT_NOT_FOUND = "Platform role is not assigned to the user."
