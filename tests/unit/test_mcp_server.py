from unittest.mock import MagicMock, patch
import pytest
from src.services.exceptions import DatabaseError, ValidationError
from datetime import datetime
from src.mcp.server import (get_customer_tool, get_machine_status_tool, get_order_status_tool, track_shipment_tool, get_maintenance_history_tool,
    get_support_ticket_tool, create_order_tool, cancel_order_tool, create_support_ticket_tool, update_support_ticket_tool)
from src.services.machine_service import MachineResult
from src.services.shipment_service import ShipmentResult
from src.services.customer_service import CustomerResult
from src.services.order_service import OrderResult
from src.services.maintenance_service import MaintenanceHistoryResult
from src.services.ticket_service import TicketResult
from src.services.order_service import CreateOrderResult, OrderItemRequest, CancelOrderResult
from src.services.support_ticket_service import CreateSupportTicketResult, UpdateSupportTicketResult

@patch("src.mcp.server.SessionLocal")
@patch("src.mcp.server.get_order_status")
def test_get_order_status_tool_returns_order_message(mock_get_order_status, mock_session_local):
    db = MagicMock()
    mock_session_local.return_value = db

    mock_get_order_status.return_value = OrderResult(
        status="FOUND",
        order_status="DELIVERED",
        message="Order ORD-10241 is DELIVERED."
    )

    result = get_order_status_tool(order_id="ORD-10241", customer_id=1)

    assert result == "Order ORD-10241 is DELIVERED."

    mock_get_order_status.assert_called_once_with(db=db, order_id="ORD-10241", customer_id=1)

    db.close.assert_called_once()


@patch("src.mcp.server.SessionLocal")
@patch("src.mcp.server.get_order_status")
def test_get_order_status_tool_returns_not_found_message(mock_get_order_status, mock_session_local):
    db = MagicMock()
    mock_session_local.return_value = db

    mock_get_order_status.return_value = OrderResult(
        status="NOT_FOUND",
        message="Order not found."
    )

    result = get_order_status_tool(order_id="ORD-99999", customer_id=1)

    assert result == "Order not found."

    mock_get_order_status.assert_called_once_with(db=db, order_id="ORD-99999", customer_id=1)

    db.close.assert_called_once()


@patch("src.mcp.server.SessionLocal")
@patch("src.mcp.server.get_order_status")
def test_get_order_status_tool_propagates_database_error(mock_get_order_status, mock_session_local):
    db = MagicMock()
    mock_session_local.return_value = db

    error = DatabaseError("Database operation failed.")
    mock_get_order_status.side_effect = error

    with pytest.raises(DatabaseError, match="Database operation failed."):
        get_order_status_tool(order_id="ORD-10241", customer_id=1)

    db.close.assert_called_once()


@patch("src.mcp.server.SessionLocal")
@patch("src.mcp.server.get_order_status")
def test_get_order_status_tool_passes_customer_id(mock_get_order_status, mock_session_local):
    db = MagicMock()
    mock_session_local.return_value = db

    mock_get_order_status.return_value = OrderResult(
        status="NOT_FOUND",
        message="Order not found."
    )

    result = get_order_status_tool(order_id="ORD-10241", customer_id=2)

    assert result == "Order not found."

    mock_get_order_status.assert_called_once_with(db=db, order_id="ORD-10241", customer_id=2)

    db.close.assert_called_once()


@patch("src.mcp.server.SessionLocal")
@patch("src.mcp.server.get_customer")
def test_get_customer_tool_returns_customer_message(mock_get_customer, mock_session_local):
    db = MagicMock()
    mock_session_local.return_value = db

    mock_get_customer.return_value = CustomerResult(
        status="FOUND",
        customer_code="CUST-001",
        name="Alfa Manufacturing S.p.A.",
        industry="Manufacturing",
        country="Italy",
        message= "Customer CUST-001: Alfa Manufacturing S.p.A. Industry: Manufacturing. Country: Italy."
    )

    result = get_customer_tool(customer_id=1)

    assert result == "Customer CUST-001: Alfa Manufacturing S.p.A. Industry: Manufacturing. Country: Italy."

    mock_get_customer.assert_called_once_with(db=db, customer_id=1)

    db.close.assert_called_once()


@patch("src.mcp.server.SessionLocal")
@patch("src.mcp.server.get_customer")
def test_get_customer_tool_returns_not_found_message(mock_get_customer, mock_session_local):
    db = MagicMock()
    mock_session_local.return_value = db

    mock_get_customer.return_value = CustomerResult(
        status="NOT_FOUND",
        customer_code=None,
        name=None,
        industry=None,
        country=None,
        message="The customer was not found in the system."
    )

    result = get_customer_tool(customer_id=999)

    assert result == "The customer was not found in the system."

    mock_get_customer.assert_called_once_with(db=db, customer_id=999)

    db.close.assert_called_once()


@patch("src.mcp.server.SessionLocal")
@patch("src.mcp.server.get_customer")
def test_get_customer_tool_propagates_database_error(mock_get_customer, mock_session_local):
    db = MagicMock()
    mock_session_local.return_value = db

    mock_get_customer.side_effect = DatabaseError("Database operation failed.")

    with pytest.raises(DatabaseError, match="Database operation failed."):
        get_customer_tool(customer_id=1)

    db.close.assert_called_once()


@patch("src.mcp.server.SessionLocal")
@patch("src.mcp.server.get_shipment")
def test_track_shipment_tool_returns_shipment_message(mock_get_shipment, mock_session_local):
    db = MagicMock()
    mock_session_local.return_value = db

    mock_get_shipment.return_value = ShipmentResult(
        status="FOUND",
        tracking_number="SHIP-90231",
        carrier="DHL",
        shipment_status="IN_TRANSIT",
        estimated_delivery=datetime(2026, 9, 30),
        message="Shipment SHIP-90231 is currently IN_TRANSIT. Carrier: DHL. Estimated delivery: 2026-09-30."
    )

    result = track_shipment_tool(tracking_number="SHIP-90231", customer_id=1)

    assert result == "Shipment SHIP-90231 is currently IN_TRANSIT. Carrier: DHL. Estimated delivery: 2026-09-30."

    mock_get_shipment.assert_called_once_with(db=db, tracking_number="SHIP-90231", customer_id=1)

    db.close.assert_called_once()


@patch("src.mcp.server.SessionLocal")
@patch("src.mcp.server.get_machine")
def test_get_machine_status_tool_returns_machine_message(mock_get_machine, mock_session_local):
    db = MagicMock()
    mock_session_local.return_value = db

    mock_get_machine.return_value = MachineResult(
        status="FOUND",
        machine_serial="AIS2-2025-00142",
        model="AIS-200",
        operating_hours=1734,
        message="Machine AIS2-2025-00142 is an AIS-200 with 1734 operating hours."
    )

    result = get_machine_status_tool(machine_serial="AIS2-2025-00142", customer_id=1)

    assert result == "Machine AIS2-2025-00142 is an AIS-200 with 1734 operating hours."

    mock_get_machine.assert_called_once_with(db=db, machine_serial="AIS2-2025-00142", customer_id=1)

    db.close.assert_called_once()


@patch("src.mcp.server.SessionLocal")
@patch("src.mcp.server.get_machine")
def test_get_machine_status_tool_returns_not_found_message(mock_get_machine, mock_session_local):
    db = MagicMock()
    mock_session_local.return_value = db

    mock_get_machine.return_value = MachineResult(
        status="NOT_FOUND",
        message="Machine not found."
    )

    result = get_machine_status_tool(machine_serial="UNKNOWN-001", customer_id=1)

    assert result == "Machine not found."

    mock_get_machine.assert_called_once_with(db=db, machine_serial="UNKNOWN-001", customer_id=1)

    db.close.assert_called_once()


@patch("src.mcp.server.SessionLocal")
@patch("src.mcp.server.get_machine")
def test_get_machine_status_tool_propagates_database_error(mock_get_machine, mock_session_local):
    db = MagicMock()
    mock_session_local.return_value = db

    mock_get_machine.side_effect = DatabaseError("Database operation failed.")

    with pytest.raises(DatabaseError, match="Database operation failed."):
        get_machine_status_tool(machine_serial="AIS2-2025-00142", customer_id=1)

    db.close.assert_called_once()


@patch("src.mcp.server.SessionLocal")
@patch("src.mcp.server.get_maintenance_history")
def test_get_maintenance_history_tool_returns_history_message(mock_get_maintenance_history, mock_session_local):
    db = MagicMock()
    mock_session_local.return_value = db

    mock_get_maintenance_history.return_value = MaintenanceHistoryResult(
        status="FOUND",
        machine_serial="AIS2-2025-00142",
        records=[
            (
                "PREVENTIVE maintenance performed on "
                "2026-01-15T10:00:00. "
                "Operating hours: 1500. "
                "Notes: Routine preventive maintenance."
            )
        ],
        message=(
            "Maintenance history for machine AIS2-2025-00142: "
            "PREVENTIVE maintenance performed on "
            "2026-01-15T10:00:00. "
            "Operating hours: 1500. "
            "Notes: Routine preventive maintenance."
        )
    )

    result = get_maintenance_history_tool(machine_serial="AIS2-2025-00142", customer_id=1)

    assert result == (
        "Maintenance history for machine AIS2-2025-00142: "
        "PREVENTIVE maintenance performed on "
        "2026-01-15T10:00:00. "
        "Operating hours: 1500. "
        "Notes: Routine preventive maintenance."
    )

    mock_get_maintenance_history.assert_called_once_with(db=db, machine_serial="AIS2-2025-00142", customer_id=1)

    db.close.assert_called_once()


@patch("src.mcp.server.SessionLocal")
@patch("src.mcp.server.get_maintenance_history")
def test_get_maintenance_history_tool_returns_not_found_message(mock_get_maintenance_history, mock_session_local):
    db = MagicMock()
    mock_session_local.return_value = db

    mock_get_maintenance_history.return_value = MaintenanceHistoryResult(
        status="NOT_FOUND",
        machine_serial="UNKNOWN-001",
        records=[],
        message="Machine not found."
    )

    result = get_maintenance_history_tool(machine_serial="UNKNOWN-001", customer_id=1)

    assert result == "Machine not found."

    mock_get_maintenance_history.assert_called_once_with(db=db, machine_serial="UNKNOWN-001", customer_id=1)

    db.close.assert_called_once()


@patch("src.mcp.server.SessionLocal")
@patch("src.mcp.server.get_maintenance_history")
def test_get_maintenance_history_tool_propagates_database_error(mock_get_maintenance_history, mock_session_local):
    db = MagicMock()
    mock_session_local.return_value = db

    mock_get_maintenance_history.side_effect = DatabaseError("Database operation failed.")

    with pytest.raises(DatabaseError, match="Database operation failed."):
        get_maintenance_history_tool(machine_serial="AIS2-2025-00142", customer_id=1)

    db.close.assert_called_once()


def test_get_support_ticket_tool_returns_ticket() -> None:
    mock_db = MagicMock()

    result = TicketResult(
        status="FOUND",
        ticket_number="TCK-5021",
        category="TECHNICAL",
        priority="P2",
        ticket_status="IN_PROGRESS",
        subject="Cooling system temperature issue",
        message="Support ticket TCK-5021 exists for machine AIS2-2025-00142."
    )

    with patch("src.mcp.server.SessionLocal", return_value=mock_db), patch("src.mcp.server.get_machine_ticket", return_value=result) as mock_get_ticket:

        response = get_support_ticket_tool(machine_serial="AIS2-2025-00142", customer_id=1)

    assert response == result.message

    mock_get_ticket.assert_called_once_with(db=mock_db, machine_serial="AIS2-2025-00142", customer_id=1)

    mock_db.close.assert_called_once()


def test_get_support_ticket_tool_returns_not_found() -> None:
    mock_db = MagicMock()

    result = TicketResult(
        status="NOT_FOUND",
        message="No support ticket was found for this machine."
    )

    with patch("src.mcp.server.SessionLocal", return_value=mock_db), patch("src.mcp.server.get_machine_ticket", return_value=result):

        response = get_support_ticket_tool(machine_serial="UNKNOWN-001", customer_id=1)

    assert response == "No support ticket was found for this machine."
    mock_db.close.assert_called_once()


def test_get_support_ticket_tool_propagates_database_error() -> None:
    mock_db = MagicMock()

    with patch("src.mcp.server.SessionLocal", return_value=mock_db), patch("src.mcp.server.get_machine_ticket", side_effect=DatabaseError("Database operation failed.")):

        with pytest.raises(DatabaseError, match="Database operation failed."):
            get_support_ticket_tool(machine_serial="AIS2-2025-00142", customer_id=1)

    mock_db.close.assert_called_once()


def test_create_order_tool_returns_created_order() -> None:
    mock_db = MagicMock()

    result = CreateOrderResult(
        status="CREATED",
        order_number="ORD-10246",
        message="Order ORD-10246 was created successfully."
    )

    with patch("src.mcp.server.SessionLocal", return_value=mock_db), patch("src.mcp.server.create_order", return_value=result) as mock_create_order:

        response = create_order_tool(
            customer_id=1,
            items=[
                {
                    "product_code": "PROD-100",
                    "quantity": 1
                }
            ]
        )

    assert response == result.message

    mock_create_order.assert_called_once()

    call_kwargs = mock_create_order.call_args.kwargs

    assert call_kwargs["db"] is mock_db
    assert call_kwargs["customer_id"] == 1

    order_items = call_kwargs["items"]

    assert len(order_items) == 1
    assert isinstance(order_items[0], OrderItemRequest)
    assert order_items[0].product_code == "PROD-100"
    assert order_items[0].quantity == 1

    mock_db.close.assert_called_once()


def test_create_order_tool_supports_multiple_items() -> None:
    mock_db = MagicMock()

    result = CreateOrderResult(
        status="CREATED",
        order_number="ORD-10247",
        message="Order ORD-10247 was created successfully."
    )

    with patch("src.mcp.server.SessionLocal", return_value=mock_db), patch("src.mcp.server.create_order", return_value=result) as mock_create_order:

        response = create_order_tool(
            customer_id=1,
            items=[
                {
                    "product_code": "PROD-200",
                    "quantity": 2
                },
                {
                    "product_code": "SP-204",
                    "quantity": 4
                }
            ]
        )

    assert response == result.message

    order_items = mock_create_order.call_args.kwargs["items"]

    assert len(order_items) == 2

    assert order_items[0].product_code == "PROD-200"
    assert order_items[0].quantity == 2

    assert order_items[1].product_code == "SP-204"
    assert order_items[1].quantity == 4

    mock_db.close.assert_called_once()


def test_create_order_tool_propagates_validation_error() -> None:
    mock_db = MagicMock()

    with patch("src.mcp.server.SessionLocal", return_value=mock_db), patch("src.mcp.server.create_order", side_effect=ValidationError("Order item quantity must be greater than zero.")):

        with pytest.raises(ValidationError, match="Order item quantity must be greater than zero"):
            create_order_tool(
                customer_id=1,
                items=[
                    {
                        "product_code": "PROD-100",
                        "quantity": 0
                    }
                ]
            )

    mock_db.close.assert_called_once()


def test_create_order_tool_propagates_database_error() -> None:
    mock_db = MagicMock()

    with patch("src.mcp.server.SessionLocal", return_value=mock_db), patch("src.mcp.server.create_order", side_effect=DatabaseError("Database operation failed.")):

        with pytest.raises(DatabaseError, match="Database operation failed"):
            create_order_tool(
                customer_id=1,
                items=[
                    {
                        "product_code": "PROD-100",
                        "quantity": 1
                    }
                ]
            )

    mock_db.close.assert_called_once()


def test_cancel_order_tool_returns_cancelled_order() -> None:
    mock_db = MagicMock()

    result = CancelOrderResult(
        status="CANCELLED",
        order_number="ORD-10242",
        message="Order ORD-10242 was cancelled successfully."
    )

    with patch("src.mcp.server.SessionLocal", return_value=mock_db), patch("src.mcp.server.cancel_order", return_value=result) as mock_cancel_order:

        response = cancel_order_tool(order_id="ORD-10242", customer_id=2)

    assert response == result.message

    mock_cancel_order.assert_called_once_with(db=mock_db, order_id="ORD-10242", customer_id=2)

    mock_db.close.assert_called_once()


def test_cancel_order_tool_returns_not_found() -> None:
    mock_db = MagicMock()

    result = CancelOrderResult(
        status="NOT_FOUND",
        order_number=None,
        message="Order not found."
    )

    with patch("src.mcp.server.SessionLocal", return_value=mock_db), patch("src.mcp.server.cancel_order", return_value=result):

        response = cancel_order_tool(order_id="ORD-99999", customer_id=2)

    assert response == "Order not found."
    mock_db.close.assert_called_once()


def test_cancel_order_tool_returns_not_cancellable() -> None:
    mock_db = MagicMock()

    result = CancelOrderResult(
        status="NOT_CANCELLABLE",
        order_number="ORD-10241",
        message="Order ORD-10241 cannot be cancelled because it is currently DELIVERED."        
    )

    with patch("src.mcp.server.SessionLocal", return_value=mock_db), patch("src.mcp.server.cancel_order", return_value=result):
        response = cancel_order_tool(order_id="ORD-10241", customer_id=1)

    assert response == result.message
    mock_db.close.assert_called_once()


def test_cancel_order_tool_propagates_database_error() -> None:
    mock_db = MagicMock()

    with patch("src.mcp.server.SessionLocal", return_value=mock_db), patch("src.mcp.server.cancel_order", side_effect=DatabaseError("Database operation failed.")):

        with pytest.raises(DatabaseError, match="Database operation failed"):
            cancel_order_tool(order_id="ORD-10242", customer_id=2)

    mock_db.close.assert_called_once()


def test_create_support_ticket_tool_returns_created_ticket() -> None:
    mock_db = MagicMock()

    mock_machine = MagicMock()
    mock_machine.id = 1

    result = CreateSupportTicketResult(
        status="CREATED",
        ticket_number="TCK-5048",
        message="Support ticket TCK-5048 was created successfully."
    )

    with patch("src.mcp.server.SessionLocal", return_value=mock_db), patch("src.mcp.server.get_machine_by_serial", return_value=mock_machine), patch("src.mcp.server.create_support_ticket", return_value=result) as mock_create_ticket:

        response = create_support_ticket_tool(customer_id=1, category="TECHNICAL", priority="P2", subject="Cooling system issue", description="The machine reports a cooling system temperature warning.", machine_serial="AIS2-2025-00142")

    assert response == "Support ticket TCK-5048 was created successfully."

    mock_create_ticket.assert_called_once_with(db=mock_db, customer_id=1, category="TECHNICAL", priority="P2", subject="Cooling system issue", description="The machine reports a cooling system temperature warning.", machine_id=1)


def test_create_support_ticket_tool_allows_ticket_without_machine() -> None:
    mock_db = MagicMock()

    result = CreateSupportTicketResult(
        status="CREATED",
        ticket_number="TCK-5049",
        message="Support ticket TCK-5049 was created successfully."
    )

    with patch("src.mcp.server.SessionLocal", return_value=mock_db), patch("src.mcp.server.create_support_ticket", return_value=result) as mock_create_ticket:

        response = create_support_ticket_tool(customer_id=1, category="ORDER", priority="P3", subject="Order question", description="I have a question about my order.")

    assert response == result.message

    mock_create_ticket.assert_called_once_with(db=mock_db, customer_id=1, category="ORDER", priority="P3", subject="Order question", description="I have a question about my order.", machine_id=None)

    mock_db.close.assert_called_once()


def test_create_support_ticket_tool_propagates_validation_error() -> None:
    mock_db = MagicMock()

    with patch("src.mcp.server.SessionLocal", return_value=mock_db), patch("src.mcp.server.create_support_ticket", side_effect=ValidationError("Ticket subject is required.")):

        with pytest.raises(ValidationError, match="Ticket subject is required"):
            create_support_ticket_tool(customer_id=1, category="TECHNICAL", priority="P2", subject="", description="Cooling system issue.")

    mock_db.close.assert_called_once()


def test_create_support_ticket_tool_propagates_database_error() -> None:
    mock_db = MagicMock()

    with patch("src.mcp.server.SessionLocal", return_value=mock_db), patch("src.mcp.server.create_support_ticket", side_effect=DatabaseError("Database operation failed.")):

        with pytest.raises(DatabaseError, match="Database operation failed"):
            create_support_ticket_tool(customer_id=1, category="TECHNICAL", priority="P2", subject="Cooling system issue", description="Cooling system temperature warning.")

    mock_db.close.assert_called_once()


def test_update_support_ticket_tool_returns_updated_ticket() -> None:
    mock_db = MagicMock()
    result = UpdateSupportTicketResult(
        status="UPDATED",
        ticket_number="TCK-5043",
        message="Support ticket TCK-5043 was updated successfully."
    )

    with patch("src.mcp.server.SessionLocal", return_value=mock_db), patch("src.mcp.server.update_support_ticket", return_value=result) as mock_update_ticket:
        response = update_support_ticket_tool(ticket_number="TCK-5043", customer_id=1, priority="P2")

    assert response == result.message

    mock_update_ticket.assert_called_once_with(db=mock_db, ticket_number="TCK-5043", customer_id=1, status=None, priority="P2", subject=None, description=None)

    mock_db.close.assert_called_once()


def test_update_support_ticket_tool_returns_not_found() -> None:
    mock_db = MagicMock()
    result = UpdateSupportTicketResult(
        status="NOT_FOUND",
        ticket_number=None,
        message="Support ticket not found."
    )

    with patch("src.mcp.server.SessionLocal", return_value=mock_db), patch("src.mcp.server.update_support_ticket", return_value=result) as mock_update_ticket:
        response = update_support_ticket_tool(ticket_number="TCK-9999", customer_id=1, status="RESOLVED")

    assert response == result.message

    mock_update_ticket.assert_called_once_with(db=mock_db, ticket_number="TCK-9999", customer_id=1, status="RESOLVED", priority=None, subject=None, description=None)

    mock_db.close.assert_called_once()


def test_update_support_ticket_tool_propagates_validation_error() -> None:
    mock_db = MagicMock()

    with patch("src.mcp.server.SessionLocal", return_value=mock_db), patch("src.mcp.server.update_support_ticket", side_effect=ValidationError("At least one ticket field must be provided for update.")):
        with pytest.raises(ValidationError, match="At least one ticket field must be provided for update"):
            update_support_ticket_tool(ticket_number="TCK-5043", customer_id=1)

    mock_db.close.assert_called_once()


def test_update_support_ticket_tool_propagates_database_error() -> None:
    mock_db = MagicMock()

    with patch("src.mcp.server.SessionLocal", return_value=mock_db), patch("src.mcp.server.update_support_ticket", side_effect=DatabaseError("Database operation failed.")):
        with pytest.raises(DatabaseError, match="Database operation failed"):
            update_support_ticket_tool(ticket_number="TCK-5043", customer_id=1, status="RESOLVED")

    mock_db.close.assert_called_once()