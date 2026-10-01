from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from src.auth.jwt import decode_access_token
from src.auth.models import AuthenticatedUser
from src.logging.logger import logger

security = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> AuthenticatedUser:
    """Validate the bearer token and return the authenticated user."""

    try:
        return decode_access_token(credentials.credentials)

    except (ValueError, RuntimeError) as exc:
        logger.warning("Authentication token rejected")

        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc), headers={"WWW-Authenticate": "Bearer"}) from exc