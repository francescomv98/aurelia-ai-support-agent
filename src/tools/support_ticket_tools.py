from src.auth.models import AuthenticatedUser
from src.security.authorization import require_customer_access
from src.services.support_ticket_service import (CreateSupportTicketResult, UpdateSupportTicketResult, create_support_ticket, update_support_ticket, get_machine_by_serial)

def create_support_ticket_tool(db, user: AuthenticatedUser, category: str, priority: str, subject: str, description: str, machine_serial: int | None = None, customer_id: int | None = None) -> CreateSupportTicketResult:
    """Create a support ticket for an authorized customer."""

    if user.role.value == "CUSTOMER":
        if user.customer_id is None:
            raise PermissionError("Customer user is not associated with a customer.")

        if customer_id is not None and customer_id != user.customer_id:
            raise PermissionError("Customer users cannot create tickets for another customer.")

        target_customer_id = user.customer_id

    else:
        if customer_id is None:
            raise ValueError("Customer ID is required for internal users.")

        target_customer_id = customer_id

    require_customer_access(user, target_customer_id)

    machine_id = None

    if machine_serial is not None:
        machine = get_machine_by_serial(db=db, machine_serial=machine_serial, customer_id=target_customer_id)

        if machine is None:
            return CreateSupportTicketResult(
                status="FAILED",
                ticket_number=None,
                message="The specified machine was not found for the customer."
            )

        machine_id = machine.id

    return create_support_ticket(db=db, customer_id=target_customer_id, category=category, priority=priority, subject=subject, description=description, machine_id=machine_id)


def update_support_ticket_tool(db, user: AuthenticatedUser, ticket_number: str, status: str | None = None, priority: str | None = None, subject: str | None = None, description: str | None = None, customer_id: int | None = None) -> UpdateSupportTicketResult:
    """Update a support ticket for an authorized customer."""

    if user.role.value == "CUSTOMER":
        if user.customer_id is None:
            raise PermissionError("Customer user is not associated with a customer.")

        if customer_id is not None and customer_id != user.customer_id:
            raise PermissionError("Customer users cannot update tickets for another customer.")

        target_customer_id = user.customer_id

    else:
        if customer_id is None:
            raise ValueError("Customer ID is required for internal users.")

        target_customer_id = customer_id

    require_customer_access(user, target_customer_id)

    return update_support_ticket(db=db, ticket_number=ticket_number, customer_id=target_customer_id, status=status, priority=priority, subject=subject, description=description)