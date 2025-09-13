import bcrypt


class UnknownHashError(Exception):
    """Raised when a stored password is not a recognized bcrypt hash."""


def _is_bcrypt_hash(value: str) -> bool:
    if not isinstance(value, str):
        return False
    return value.startswith(("$2a$", "$2b$", "$2y$")) and len(value) >= 60


def hash_password(password: str) -> str:
    """Hash a plain password using bcrypt and return a UTF-8 string."""
    if not isinstance(password, str) or not password:
        raise ValueError("Password must be a non-empty string")
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    """
    Verify a plain password against a bcrypt hash.
    Returns True if it matches, False otherwise.

    Raises UnknownHashError if the stored value doesn't look like a bcrypt hash.
    """
    if not _is_bcrypt_hash(hashed):
        raise UnknownHashError("hash could not be identified")
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        # Malformed hash string
        raise UnknownHashError("hash could not be identified")


# Demo usage
if __name__ == "__main__":
    plain = "MyS3cret!"
    hashed = hash_password(plain)
    # uv run -m app.utils.hash_password

    print("Password:", plain)
    print("Hashed:  ", hashed)
    print("Verify (correct):", verify_password("MyS3cret!", hashed))
    print("Verify (wrong):  ", verify_password("WrongPass", hashed))
