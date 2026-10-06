from mcp.server import MCPServer
from src.database.session import SessionLocal
from src.services.order_service import get_order_status
from src.services.customer_service import get_customer
from src.services.shipment_service import get_shipment
from src.services.machine_service import get_machine
from src.services.maintenance_service import get_maintenance_history

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


if __name__ == "__main__":
    mcp.run(transport="streamable-http", port=8001)