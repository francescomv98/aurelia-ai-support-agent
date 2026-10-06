from src.mcp.server import get_order_status_tool

def test_get_order_status_tool_with_real_database():
    result = get_order_status_tool(order_id="ORD-10241", customer_id=1)

    assert result == "Order ORD-10241 is DELIVERED."