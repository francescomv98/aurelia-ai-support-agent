class ApplicationError(Exception):
    """Base exception for expected application errors."""


class ValidationError(ApplicationError):
    """Raised when input or operation parameters are invalid."""


class AuthorizationError(ApplicationError):
    """Raised when a user is not authorized to perform an operation."""


class DatabaseError(ApplicationError):
    """Raised when a database operation fails."""


class LLMError(ApplicationError):
    """Raised when an LLM operation fails."""


class ExternalServiceError(ApplicationError):
    """Raised when an external service operation fails."""