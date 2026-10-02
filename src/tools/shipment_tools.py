from src.auth.models import AuthenticatedUser
from src.security.authorization import require_customer_access
from src.services.shipment_service import ShipmentResult, get_shipment
from src.services.exceptions import AuthorizationError, ValidationError

def get_shipment_tool(db, tracking_number: str, user: AuthenticatedUser, customer_id: int | None = None) -> ShipmentResult:
    """
    Retrieve shipment information for an authorized customer.
    """

    if user.role.value == "CUSTOMER":
        if user.customer_id is None:
            raise AuthorizationError("Customer user is not associated with a customer.")

        target_customer_id = user.customer_id

    else:
        if customer_id is None:
            raise ValidationError("Customer ID is required for internal users.")

        target_customer_id = customer_id

    require_customer_access(user, target_customer_id)

    return get_shipment(db=db, tracking_number=tracking_number, customer_id=target_customer_id)