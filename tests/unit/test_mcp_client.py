import pytest
from src.mcp.client import create_mcp_client

@pytest.mark.anyio
async def test_mcp_client_can_list_tools() -> None:
    async with create_mcp_client() as client:
        result = await client.list_tools()

    tool_names = {tool.name for tool in result.tools}

    assert "get_order_status_tool" in tool_names
    assert "get_customer_tool" in tool_names
    assert "track_shipment_tool" in tool_names
    assert "get_machine_status_tool" in tool_names
    assert "get_maintenance_history_tool" in tool_names
    assert "get_support_ticket_tool" in tool_names
    assert "create_order_tool" in tool_names
    assert "cancel_order_tool" in tool_names
    assert "create_support_ticket_tool" in tool_names
    assert "update_support_ticket_tool" in tool_names


@pytest.mark.anyio
async def test_mcp_client_can_call_order_status_tool() -> None:
    async with create_mcp_client() as client:
        result = await client.call_tool(
            "get_order_status_tool",
            {
                "order_id": "ORD-10241",
                "customer_id": 1
            }
        )

    assert len(result.content) == 1
    assert result.content[0].text == "Order ORD-10241 is DELIVERED."