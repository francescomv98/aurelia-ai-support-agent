from src.tools.order_tools import get_order_status_tool

def test_get_order_status_tool(monkeypatch) -> None:
    def fake_get_order_status(db, order_id: str, customer_id: int) -> dict[str, str]:
        assert order_id == "ORD-10245"
        assert customer_id == 1

        return {
            "status": "SHIPPED",
            "message": "Order ORD-10245 is SHIPPED."
        }

    monkeypatch.setattr("src.tools.order_tools.get_order_status", fake_get_order_status)

    result = get_order_status_tool(db=object(), order_id="ORD-10245", customer_id=1)

    assert result == "Order ORD-10245 is SHIPPED."