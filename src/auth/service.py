from sqlalchemy import select
from sqlalchemy.orm import Session
from src.auth.jwt import create_access_token
from src.auth.models import AuthenticatedUser
from src.auth.password import verify_password
from src.database.models import User
from src.logging.logger import logger

class AuthenticationService:
    """Handle user authentication and access token creation."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def authenticate(self, username: str, password: str) -> str:
        """Authenticate a user and return a JWT access token."""

        if not username.strip():
            raise ValueError("Username cannot be empty.")

        if not password:
            raise ValueError("Password cannot be empty.")

        logger.info("Authenticating user", username=username)

        try:
            statement = select(User).where(User.username == username)

            user = self.db.scalar(statement)

            # Do not reveal whether the username exists.
            if user is None:
                logger.warning("Authentication failed", username=username)
                raise ValueError("Invalid username or password.")

            if not user.is_active:
                logger.warning("Authentication rejected for inactive user", user_id=user.id)
                raise ValueError("Invalid username or password.")

            if not verify_password(password, user.password_hash):
                logger.warning("Authentication failed", user_id=user.id)
                raise ValueError("Invalid username or password.")

            authenticated_user = AuthenticatedUser(user_id=user.id, customer_id=user.customer_id, role=user.role.name)

            token = create_access_token(authenticated_user)

            logger.info("User authenticated successfully", user_id=user.id, role=user.role.name)

            return token

        except ValueError:
            raise

        except Exception:
            logger.exception("Authentication service failed", username=username)
            raise