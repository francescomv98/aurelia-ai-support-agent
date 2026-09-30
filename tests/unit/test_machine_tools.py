from src.auth.models import AuthenticatedUser
from src.database.models import UserRole
from src.services.machine_service import MachineResult
from src.tools.machine_tools import get_machine_tool

def test_get_machine_tool(monkeypatch) -> None:
    user = AuthenticatedUser(user_id=1, customer_id=1, role=UserRole.CUSTOMER)

    def fake_get_machine(db, machine_serial: str, customer_id: int) -> MachineResult:
        assert machine_serial == "AIS2-2025-00142"
        assert customer_id == 1

        return MachineResult(
            status="FOUND",
            machine_serial="AIS2-2025-00142",
            model="AIS-200",
            operating_hours=1734,
            message=(
                "Machine AIS2-2025-00142 is an AIS-200 "
                "with 1734 operating hours."
            )
        )

    monkeypatch.setattr("src.tools.machine_tools.get_machine", fake_get_machine)

    result = get_machine_tool(db=object(), machine_serial="AIS2-2025-00142", user=user)

    assert isinstance(result, MachineResult)
    assert result.status == "FOUND"
    assert result.machine_serial == "AIS2-2025-00142"
    assert result.model == "AIS-200"
    assert result.operating_hours == 1734