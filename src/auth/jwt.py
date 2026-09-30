import os
from datetime import datetime, timedelta, timezone
import jwt
from src.auth.models import AuthenticatedUser
from src.logging.logger import logger

def _get_jwt_secret() -> str:
    """Return the JWT signing secret."""

    secret = os.getenv("JWT_SECRET_KEY")

    if not secret:
        logger.error("JWT secret key is not configured")
        raise RuntimeError("JWT_SECRET_KEY environment variable is not set.")

    return secret


def _get_jwt_algorithm() -> str:
    """Return the configured JWT algorithm."""

    return os.getenv("JWT_ALGORITHM", "HS256")


def _get_expiration_minutes() -> int:
    """Return JWT expiration time in minutes."""

    value = os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30")

    try:
        minutes = int(value)
    except ValueError as exc:
        raise RuntimeError("JWT_ACCESS_TOKEN_EXPIRE_MINUTES must be an integer.") from exc

    if minutes <= 0:
        raise RuntimeError("JWT_ACCESS_TOKEN_EXPIRE_MINUTES must be greater than zero.")

    return minutes


def create_access_token(user: AuthenticatedUser) -> str:
    """Create a signed JWT access token."""

    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=_get_expiration_minutes())

    payload = {
        "sub": str(user.user_id),
        "customer_id": user.customer_id,
        "role": user.role.value,
        "iat": now,
        "exp": expires_at
    }

    token = jwt.encode(payload, _get_jwt_secret(), algorithm=_get_jwt_algorithm())

    logger.info("JWT access token created", user_id=user.user_id, role=user.role.value)

    return token


def decode_access_token(token: str) -> AuthenticatedUser:
    """Validate and decode a JWT access token."""

    if not token:
        raise ValueError("Access token cannot be empty.")

    try:
        payload = jwt.decode(token, _get_jwt_secret(), algorithms=[_get_jwt_algorithm()])

        user_id = int(payload["sub"])
        role = payload["role"]

        user = AuthenticatedUser(user_id=user_id, customer_id=payload.get("customer_id"), role=role)

        logger.info("JWT access token validated", user_id=user.user_id, role=user.role.value)

        return user

    except jwt.ExpiredSignatureError as exc:
        logger.warning("JWT access token expired")
        raise ValueError("Access token has expired.") from exc

    except jwt.InvalidTokenError as exc:
        logger.warning("Invalid JWT access token")
        raise ValueError("Invalid access token.") from exc

    except (KeyError, TypeError, ValueError) as exc:
        logger.warning("JWT payload is invalid")
        raise ValueError("Invalid access token payload.") from exc