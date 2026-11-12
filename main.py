import os
from contextlib import asynccontextmanager
from src.security.rate_limiter import RateLimiter
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from src.api.routes.auth import router as auth_router
from src.api.routes.chat import close_checkpointer, router as chat_router
from src.api.routes.documents import router as documents_router
from src.app_logging.logger import configure_logging, logger
from src.services.exceptions import (ApplicationError, AuthorizationError, DatabaseError, ExternalServiceError, LLMError, NotFoundError,
                                     ValidationError)

configure_logging()

HEALTH_PATH = "/health"


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield
    await close_checkpointer()


app = FastAPI(
    title="Aurelia AI Support Agent",
    description="Enterprise AI support agent for Aurelia Industrial Systems.",
    version="1.0.0",
    lifespan=lifespan
)

app.state.rate_limiter = RateLimiter(
    max_requests=int(os.getenv("RATE_LIMIT_REQUESTS", "30")),
    window_seconds=int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))
)


@app.exception_handler(ValidationError)
async def validation_error_handler(request: Request, exc: ValidationError) -> JSONResponse:
    logger.warning("Validation error", path=request.url.path, method=request.method, error=str(exc))

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": str(exc)}
    )


@app.exception_handler(AuthorizationError)
async def authorization_error_handler(request: Request, exc: AuthorizationError) -> JSONResponse:
    logger.warning("Authorization error", path=request.url.path, method=request.method, error=str(exc))

    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content={"detail": str(exc)}
    )


@app.exception_handler(NotFoundError)
async def not_found_error_handler(request: Request, exc: NotFoundError) -> JSONResponse:
    logger.warning("Resource not found", path=request.url.path, method=request.method, error=str(exc))

    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": str(exc)}
    )


@app.exception_handler(DatabaseError)
async def database_error_handler(request: Request, exc: DatabaseError) -> JSONResponse:
    logger.exception("Database error", path=request.url.path, method=request.method)

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "A database error occurred."}
    )


@app.exception_handler(LLMError)
async def llm_error_handler(request: Request, exc: LLMError) -> JSONResponse:
    logger.exception("LLM error", path=request.url.path, method=request.method)

    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": "The AI service is temporarily unavailable."}
    )


@app.exception_handler(ExternalServiceError)
async def external_service_error_handler(request: Request, exc: ExternalServiceError) -> JSONResponse:
    logger.exception("External service error", path=request.url.path, method=request.method)

    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": "An external service is temporarily unavailable."}
    )


@app.exception_handler(ApplicationError)
async def application_error_handler(request: Request, exc: ApplicationError) -> JSONResponse:
    logger.exception("Application error", path=request.url.path, method=request.method)

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An application error occurred."}
    )


@app.exception_handler(Exception)
async def unexpected_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unexpected application error", path=request.url.path, method=request.method)

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred."}
    )


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Apply rate limiting to incoming HTTP requests."""
    client_host = request.client.host if request.client else "unknown"

    # Container health probes must never be throttled, or a busy client could mark the service unhealthy.
    if request.url.path == HEALTH_PATH:
        return await call_next(request)

    if not app.state.rate_limiter.is_allowed(client_host):
        logger.warning("Rate limit exceeded", client=client_host, path=request.url.path, method=request.method)

        return JSONResponse(
            status_code=429,
            content={
                "detail": "Too many requests. Please try again later."
            }
        )

    return await call_next(request)


@app.get(HEALTH_PATH, include_in_schema=False)
async def health() -> dict[str, str]:
    """Liveness probe: the process is up and serving HTTP. It does not call the database or OpenAI."""
    return {"status": "ok"}


app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(documents_router)

logger.info("Aurelia AI Support Agent starting")