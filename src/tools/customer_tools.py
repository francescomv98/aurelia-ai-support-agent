from src.auth.models import AuthenticatedUser
from src.security.authorization import require_customer_access
from src.services.customer_service import CustomerResult, get_customer

def get_customer_tool(
    db, user: AuthenticatedUser, customer_id: int | None = None) -> CustomerResult:
    """
    Retrieve customer information for an authorized customer.
    """

    if user.role.value == "CUSTOMER":
        if user.customer_id is None:
            raise PermissionError("Customer user is not associated with a customer.")

        target_customer_id = user.customer_id

    else:
        if customer_id is None:
            raise ValueError("Customer ID is required for internal users.")

        target_customer_id = customer_id

    require_customer_access(user, target_customer_id)

    return get_customer(db=db, customer_id=target_customer_id)