from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from src.auth.service import AuthenticationService
from src.database.session import SessionLocal
from src.logging.logger import logger

router = APIRouter(prefix="/auth", tags=["authentication"])


class LoginRequest(BaseModel):
    """Request payload for user authentication."""

    username: str
    password: str


class LoginResponse(BaseModel):
    """Response containing an access token."""

    access_token: str
    token_type: str = "bearer"


def get_db():
    """Provide a database session for the request."""

    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


@router.post("/login", response_model=LoginResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    """Authenticate a user and return an access token."""

    logger.info("Login request received", username=request.username)

    try:
        service = AuthenticationService(db)
        token = service.authenticate(username=request.username, password=request.password)

        return LoginResponse(access_token=token)

    except ValueError as exc:
        logger.warning("Login rejected", username=request.username)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc