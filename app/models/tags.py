from enum import Enum


class UserverseApiTag(Enum):
    USER_MANAGEMENT_BASIC_AUTH = (
        "User Management with Basic Auth",
        "Endpoints for managing users with basic authentication",
    )
    USER_MANAGEMENT = ("User Management", "Endpoints for managing users")
    USER_PASSWORD_MANAGEMENT = (
        "User Password Management",
        "Operations related to changing or resetting passwords",
    )
    COMPANY_MANAGEMENT = ("Company Management", "Create and manage companies")
    COMPANY_USER_MANAGEMENT = (
        "Company User Management",
        "Manage users within companies",
    )
    COMPANY_ROLE_MANAGEMENT = (
        "Company Role Management",
        "Manage roles and permissions for company users",
    )

    def __init__(self, name: str, description: str):
        self._name = name
        self._description = description

    @property
    def name(self):
        return self._name

    @property
    def description(self):
        return self._description

    @classmethod
    def list(cls):
        return [{"name": tag.name, "description": tag.description} for tag in cls]
