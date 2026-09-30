from src.auth.password import hash_password, verify_password

def test_password_hash_can_be_verified() -> None:
    password = "DemoPassword123!"

    hashed_password = hash_password(password)

    assert hashed_password != password
    assert verify_password(password, hashed_password)


def test_wrong_password_is_rejected() -> None:
    hashed_password = hash_password("DemoPassword123!")

    assert not verify_password("WrongPassword123!", hashed_password)


def test_empty_password_is_rejected() -> None:
    hashed_password = hash_password("DemoPassword123!")

    assert not verify_password("", hashed_password)