import pytest
from src.services.maintenance_service import (MaintenanceResult, calculate_maintenance_status)


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
    with pytest.raises(ValueError, match="cannot be negative"):
        calculate_maintenance_status(current_hours=-1, maintenance_interval=2000)


def test_invalid_maintenance_interval_is_rejected() -> None:
    with pytest.raises(ValueError, match="greater than zero"):
        calculate_maintenance_status(current_hours=1000, maintenance_interval=0)