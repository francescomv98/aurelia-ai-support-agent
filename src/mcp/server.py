import os
from mcp.server import MCPServer
from src.database.session import SessionLocal
from src.services.customer_service import get_customer
from src.services.shipment_service import get_shipment
from src.services.machine_service import get_machine
from src.services.maintenance_service import get_maintenance_history
from src.services.ticket_service import get_machine_ticket
from src.services.order_service import create_order, cancel_order, get_order_status, OrderItemRequest
from src.services.support_ticket_service import create_support_ticket, update_support_ticket, get_machine_by_serial
from src.services.product_service import get_product

mcp = MCPServer(
    name="Aurelia Support MCP Server",
    description="MCP server exposing Aurelia Industrial Systems support capabilities.",
    version="1.0.0"
)


@mcp.tool()
def get_order_status_tool(order_id: str, customer_id: int) -> str:
    """Retrieve the status of an order for an authorized customer."""

    db = SessionLocal()

    try:
        result = get_order_status(db=db, order_id=order_id, customer_id=customer_id)

        return result.message

    finally:
        db.close()


@mcp.tool()
def get_customer_tool(customer_id: int) -> str:
    """Retrieve information about a customer."""

    db = SessionLocal()

    try:
        result = get_customer(db=db, customer_id=customer_id)

        return result.message

    finally:
        db.close()


@mcp.tool()
def track_shipment_tool(tracking_number: str, customer_id: int) -> str:
    """Track a shipment for an authorized customer."""

    db = SessionLocal()

    try:
        result = get_shipment(db=db, tracking_number=tracking_number, customer_id=customer_id)

        return result.message

    finally:
        db.close()


@mcp.tool()
def get_machine_status_tool(machine_serial: str, customer_id: int) -> str:
    """Retrieve the status of a machine for an authorized customer."""

    db = SessionLocal()

    try:
        result = get_machine(db=db, machine_serial=machine_serial, customer_id=customer_id)

        return result.message

    finally:
        db.close()


@mcp.tool()
def get_maintenance_history_tool(machine_serial: str, customer_id: int) -> str:
    """Retrieve the maintenance history of a machine for an authorized customer."""

    db = SessionLocal()

    try:
        result = get_maintenance_history(db=db, machine_serial=machine_serial, customer_id=customer_id)

        return result.message

    finally:
        db.close()


@mcp.tool()
def get_support_ticket_tool(machine_serial: str, customer_id: int) -> str:
    """Retrieve the support ticket for a customer's machine."""
    db = SessionLocal()
    try:
        result = get_machine_ticket(db=db, machine_serial=machine_serial, customer_id=customer_id)
        return result.message
    finally:
        db.close()


@mcp.tool()
def get_product_tool(product_code: str) -> str:
    """Retrieve product information from the enterprise database."""
    db = SessionLocal()
    try:
        result = get_product(db=db, product_code=product_code)
        return result.message
    finally:
        db.close()


@mcp.tool()
def create_order_tool(customer_id: int, items: list[dict[str, object]]) -> str:
    """Create a new order for a customer."""
    db = SessionLocal()
    try:
        order_items = [
            OrderItemRequest(
                product_code=str(item["product_code"]),
                quantity=int(item["quantity"])
            )
            for item in items
        ]

        result = create_order(db=db, customer_id=customer_id, items=order_items)

        return result.message
    finally:
        db.close()


@mcp.tool()
def cancel_order_tool(order_id: str, customer_id: int) -> str:
    """Cancel an order for an authorized customer."""
    db = SessionLocal()
    try:
        result = cancel_order(db=db, order_id=order_id, customer_id=customer_id)
        return result.message
    finally:
        db.close()


@mcp.tool()
def create_support_ticket_tool(customer_id: int, category: str, priority: str, subject: str, description: str, machine_serial: str | None = None) -> str:
    """Create a support ticket for a customer."""
    db = SessionLocal()
    try:
        machine_id = None

        if machine_serial is not None:
            machine = get_machine_by_serial(db=db, machine_serial=machine_serial, customer_id=customer_id)

            if machine is None:
                return "The specified machine was not found for the customer."

            machine_id = machine.id
        result = create_support_ticket(db=db, customer_id=customer_id, category=category, priority=priority, subject=subject, description=description, machine_id=machine_id)
        return result.message
    finally:
        db.close()


@mcp.tool()
def update_support_ticket_tool(ticket_number: str, customer_id: int, status: str | None = None, priority: str | None = None, subject: str | None = None, description: str | None = None) -> str:
    """Update an existing support ticket for an authorized customer."""
    db = SessionLocal()
    try:
        result = update_support_ticket(db=db, ticket_number=ticket_number, customer_id=customer_id, status=status, priority=priority, subject=subject, description=description)
        return result.message
    finally:
        db.close()


if __name__ == "__main__":
    # Binds to localhost by default. Set MCP_HOST=0.0.0.0 only on a private
    # network (e.g. docker-compose): the tools trust the customer_id they receive.
    mcp.run(transport="streamable-http", host=os.getenv("MCP_HOST", "127.0.0.1"), port=int(os.getenv("MCP_PORT", "8001")))