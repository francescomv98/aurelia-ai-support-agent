from pwdlib import PasswordHash

password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    """Hash a password using the recommended password hashing algorithm."""
    if not password:
        raise ValueError("Password cannot be empty.")

    return password_hash.hash(password)


def verify_password(password: str, password_hash_value: str) -> bool:
    """Verify a password against its stored hash."""
    if not password:
        return False

    if not password_hash_value:
        return False

    return password_hash.verify(password, password_hash_value)