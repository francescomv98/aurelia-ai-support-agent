from src.auth.models import AuthenticatedUser
from src.database.models import UserRole
from src.services.order_service import OrderResult
from src.tools.order_tools import get_order_status_tool

def test_get_order_status_tool(monkeypatch) -> None:
    user = AuthenticatedUser(user_id=1, customer_id=1, role=UserRole.CUSTOMER)

    def fake_get_order_status(db, order_id: str, customer_id: int) -> OrderResult:
        assert order_id == "ORD-10245"
        assert customer_id == 1

        return OrderResult(
            status="FOUND",
            order_status="SHIPPED",
            message="Order ORD-10245 is SHIPPED."
        )

    monkeypatch.setattr("src.tools.order_tools.get_order_status", fake_get_order_status)

    result = get_order_status_tool(db=object(), order_id="ORD-10245", user=user)

    assert result == "Order ORD-10245 is SHIPPED."