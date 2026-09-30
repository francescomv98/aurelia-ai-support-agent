from src.tools.machine_tools import get_machine_tool

def test_get_machine_tool(monkeypatch) -> None:
    def fake_get_machine(db, machine_serial: str, customer_id: int) -> dict:
        assert machine_serial == "AIS2-2025-00142"
        assert customer_id == 1

        return {
            "status": "FOUND",
            "machine_serial": "AIS2-2025-00142",
            "model": "AIS-200",
            "operating_hours": 1734
        }

    monkeypatch.setattr("src.tools.machine_tools.get_machine", fake_get_machine)

    result = get_machine_tool(db=object(), machine_serial="AIS2-2025-00142", customer_id=1)

    assert result == ("Machine AIS2-2025-00142 is an AIS-200 with 1734 operating hours.")