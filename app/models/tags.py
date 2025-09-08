from enum import Enum


class UserverseApiTag(Enum):
    USER_MANAGEMENT_BASIC_AUTH = (
        "User Basic Auth Routes",
        "Endpoints for user login and account creation via Basic Auth",
    )
    USER_MANAGEMENT_PROFILE = (
        "User Profile Management",
        "Endpoints to retrieve and update user profiles, and fetch associated companies",
    )
    USER_PASSWORD_MANAGEMENT = (
        "User Password Reset",
        "Endpoints to reset password using OTP verification and Basic Auth",
    )
    USER_VERIFICATION = (
        "User Verification",
        "Endpoints to verify email and resend verification links",
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

    def __init__(self, tag: str, description: str):
        self._tag = tag
        self._description = description

    @property
    def name(self) -> str:
        return self._tag

    @property
    def description(self) -> str:
        return self._description

    @classmethod
    def list(cls):
        return [{"name": tag.name, "description": tag.description} for tag in cls]
