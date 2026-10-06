from unittest.mock import MagicMock, patch
import pytest
from src.services.exceptions import DatabaseError
from datetime import datetime
from src.mcp.server import (get_customer_tool, get_machine_status_tool, get_order_status_tool, track_shipment_tool, get_maintenance_history_tool)
from src.services.machine_service import MachineResult
from src.services.shipment_service import ShipmentResult
from src.services.customer_service import CustomerResult
from src.services.order_service import OrderResult
from src.services.maintenance_service import MaintenanceHistoryResult

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