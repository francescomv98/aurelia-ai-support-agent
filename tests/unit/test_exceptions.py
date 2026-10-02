import pytest
from src.services.exceptions import (ApplicationError, AuthorizationError, DatabaseError, ExternalServiceError, LLMError, ValidationError)

@pytest.mark.parametrize("exception_type", [ValidationError, AuthorizationError, DatabaseError, LLMError, ExternalServiceError])
def test_application_exceptions_inherit_from_application_error(exception_type) -> None:
    error = exception_type("Test error")

    assert isinstance(error, ApplicationError)
    assert str(error) == "Test error"


def test_application_error_can_be_raised() -> None:
    with pytest.raises(ApplicationError, match="Application failure"):
        raise ApplicationError("Application failure")