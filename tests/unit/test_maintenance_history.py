import pytest
from datetime import datetime
from unittest.mock import MagicMock
from src.database.models import MaintenanceType
from src.services.exceptions import DatabaseError, ValidationError
from sqlalchemy.exc import SQLAlchemyError
from src.services.maintenance_service import (MaintenanceHistoryResult, MaintenanceResult, calculate_maintenance_status, get_maintenance_history)

def test_maintenance_is_not_due() -> None:
    result = calculate_maintenance_status(current_hours=1734, maintenance_interval=2000)

    assert isinstance(result, MaintenanceResult)
    assert result.status == "NOT_DUE"
    assert result.current_hours == 1734
    assert result.maintenance_interval == 2000
    assert result.remaining_hours == 266


def test_maintenance_is_overdue() -> None:
    result = calculate_maintenance_status(current_hours=5020, maintenance_interval=2500)

    assert isinstance(result, MaintenanceResult)
    assert result.status == "OVERDUE"
    assert result.current_hours == 5020
    assert result.maintenance_interval == 2500
    assert result.remaining_hours is None


def test_negative_operating_hours_are_rejected() -> None:
    with pytest.raises(ValidationError, match="cannot be negative"):
        calculate_maintenance_status(current_hours=-1, maintenance_interval=2000)


def test_invalid_maintenance_interval_is_rejected() -> None:
    with pytest.raises(ValidationError, match="greater than zero"):
        calculate_maintenance_status(current_hours=1000, maintenance_interval=0)


def test_get_maintenance_history_returns_records() -> None:
    db = MagicMock()

    machine = MagicMock()
    machine.id = 1
    machine.serial_number = "AIS2-2025-00142"

    latest_record = MagicMock()
    latest_record.maintenance_type = MaintenanceType.PREVENTIVE
    latest_record.performed_at = datetime(2026, 8, 15, 10, 30)
    latest_record.operating_hours = 1500
    latest_record.notes = "Routine preventive maintenance completed."

    older_record = MagicMock()
    older_record.maintenance_type = MaintenanceType.CORRECTIVE
    older_record.performed_at = datetime(2026, 3, 10, 9, 0)
    older_record.operating_hours = 1000
    older_record.notes = "Cooling system inspected."

    db.scalar.return_value = machine
    db.scalars.return_value.all.return_value = [ latest_record, older_record ]

    result = get_maintenance_history(db=db, machine_serial="AIS2-2025-00142", customer_id=1)

    assert isinstance(result, MaintenanceHistoryResult)
    assert result.status == "FOUND"
    assert result.machine_serial == "AIS2-2025-00142"
    assert len(result.records) == 2

    assert "PREVENTIVE maintenance performed on 2026-08-15T10:30:00." in result.records[0]
    assert "Operating hours: 1500." in result.records[0]
    assert "Routine preventive maintenance completed." in result.records[0]

    assert "CORRECTIVE maintenance performed on 2026-03-10T09:00:00." in result.records[1]
    assert "Operating hours: 1000." in result.records[1]
    assert "Cooling system inspected." in result.records[1]

    assert "Maintenance history for machine AIS2-2025-00142:" in result.message
    assert "PREVENTIVE maintenance performed" in result.message
    assert "CORRECTIVE maintenance performed" in result.message

    db.scalar.assert_called_once()
    db.scalars.assert_called_once()


def test_get_maintenance_history_maps_database_error() -> None:
    db = MagicMock()
    db.scalar.side_effect = SQLAlchemyError("database failure")

    with pytest.raises(DatabaseError, match="Database operation failed."):
        get_maintenance_history(db=db, machine_serial="AIS2-2025-00142", customer_id=1)
