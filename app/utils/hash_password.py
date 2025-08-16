from passlib.context import CryptContext

# Configure password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """
    Hash a plain password using bcrypt.
    Returns the salted hash string.
    """
    return pwd_context.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    """
    Verify a plain password against the stored hash.
    Returns True if it matches, False otherwise.
    """
    return pwd_context.verify(password, hashed)


# Demo usage
if __name__ == "__main__":
    plain = "MyS3cret!"
    hashed = hash_password(plain)
    # uv run -m app.utils.hash_password

    print("Password:", plain)
    print("Hashed:  ", hashed)
    print("Verify (correct):", verify_password("MyS3cret!", hashed))
    print("Verify (wrong):  ", verify_password("WrongPass", hashed))
