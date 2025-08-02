from enum import Enum


class UserAccountStatus(str, Enum):
    AWAITING_VERIFICATION = "Awaiting Verification: User must verify their email"
    ACTIVE = "Active: Verified and allowed to log in"
    SUSPENDED = "Suspended: Temporarily disabled by admin"
    DEACTIVATED = "Deactivated: User closed or deleted account"
    BANNED = "Banned: Permanently removed for violating terms"

    @property
    def name_value(self) -> str:
        """Returns just the status name (e.g., 'Active')."""
        return self.value.split(":")[0].strip()

    @property
    def description(self) -> str:
        """Returns the description part (e.g., 'Verified and allowed to log in')."""
        return self.value.split(":", 1)[1].strip()
