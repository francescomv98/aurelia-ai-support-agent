import pytest
from src.auth.jwt import decode_access_token
from src.auth.service import AuthenticationService
from src.database.session import SessionLocal

@pytest.mark.integration
def test_seeded_user_can_authenticate() -> None:
    with SessionLocal() as db:
        service = AuthenticationService(db)

        token = service.authenticate(username="alfa.support", password="AureliaDemo123!")

        assert token

        authenticated_user = decode_access_token(token)

        assert authenticated_user.user_id > 0
        assert authenticated_user.customer_id == 1
        assert authenticated_user.role.value == "CUSTOMER"


@pytest.mark.integration
def test_seeded_user_cannot_authenticate_with_wrong_password() -> None:
    with SessionLocal() as db:
        service = AuthenticationService(db)

        with pytest.raises(ValueError, match="Invalid username or password."):
            service.authenticate(username="alfa.support", password="WrongPassword123!")