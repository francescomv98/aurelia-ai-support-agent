import pytest
from src.mcp.client import create_mcp_client, call_mcp_tool
from unittest.mock import AsyncMock, MagicMock
from src.services.exceptions import ExternalServiceError

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
    assert "get_product_tool" in tool_names


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


@pytest.mark.anyio
async def test_call_mcp_tool_returns_text_response() -> None:
    client = MagicMock()

    result = MagicMock()
    result.content = [MagicMock(text="Order ORD-10241 is DELIVERED.")]

    client.call_tool = AsyncMock(return_value=result)

    response = await call_mcp_tool(client=client, tool_name="get_order_status_tool", arguments={
            "order_id": "ORD-10241",
            "customer_id": 1
        }
    )

    assert response == "Order ORD-10241 is DELIVERED."

    client.call_tool.assert_awaited_once_with("get_order_status_tool",
        {
            "order_id": "ORD-10241",
            "customer_id": 1
        }
    )


@pytest.mark.anyio
async def test_call_mcp_tool_combines_multiple_text_contents() -> None:
    client = MagicMock()

    result = MagicMock()
    result.content = [MagicMock(text="First response."), MagicMock(text="Second response.")]

    client.call_tool = AsyncMock(return_value=result)

    response = await call_mcp_tool(client=client, tool_name="test_tool", arguments={})

    assert response == "First response.\nSecond response."


@pytest.mark.anyio
async def test_call_mcp_tool_raises_external_service_error_on_failure() -> None:
    client = MagicMock()

    client.call_tool = AsyncMock(side_effect=RuntimeError("Connection failed"))

    with pytest.raises(ExternalServiceError, match="MCP service is currently unavailable"):
        await call_mcp_tool(client=client, tool_name="get_order_status_tool",
            arguments={
                "order_id": "ORD-10241",
                "customer_id": 1
            }
        )


@pytest.mark.anyio
async def test_call_mcp_tool_raises_external_service_error_on_empty_response() -> None:
    client = MagicMock()

    result = MagicMock()
    result.content = []

    client.call_tool = AsyncMock(return_value=result)

    with pytest.raises(ExternalServiceError, match="MCP service returned an empty response"):
        await call_mcp_tool(client=client, tool_name="test_tool", arguments={})


@pytest.mark.anyio
async def test_mcp_client_can_call_product_tool() -> None:
    async with create_mcp_client() as client:
        result = await client.call_tool(
            "get_product_tool",
            {
                "product_code": "AIS-200"
            }
        )

    assert len(result.content) == 1
    assert result.content[0].text == (
        "Product PROD-200: AIS-200. "
        "Category: MACHINE. "
        "Capacity: 80 units per minute. "
        "Maintenance interval: 2000 operating hours."
    )


@pytest.mark.anyio
async def test_mcp_client_can_create_order() -> None:
    async with create_mcp_client() as client:
        result = await client.call_tool("create_order_tool",
            {
                "customer_id": 1,
                "items": [
                    {
                        "product_code": "PROD-200",
                        "quantity": 2
                    }
                ]
            }
        )

    assert len(result.content) == 1
    assert result.content[0].text.startswith("Order ORD-")
    assert result.content[0].text.endswith("was created successfully.")


@pytest.mark.anyio
async def test_mcp_client_can_cancel_order() -> None:
    async with create_mcp_client() as client:
        create_result = await client.call_tool("create_order_tool",
            {
                "customer_id": 1,
                "items": [
                    {
                        "product_code": "PROD-200",
                        "quantity": 1
                    }
                ]
            }
        )

        assert len(create_result.content) == 1

        order_number = create_result.content[0].text.split()[1]

        cancel_result = await client.call_tool("cancel_order_tool",
            {
                "order_id": order_number,
                "customer_id": 1
            }
        )

    assert len(cancel_result.content) == 1
    assert cancel_result.content[0].text == f"Order {order_number} was cancelled successfully."


@pytest.mark.anyio
async def test_mcp_client_can_create_support_ticket() -> None:
    async with create_mcp_client() as client:
        result = await client.call_tool("create_support_ticket_tool",
            {
                "customer_id": 1,
                "category": "TECHNICAL",
                "priority": "P3",
                "subject": "MCP integration test",
                "description": "Test support ticket created through MCP.",
                "machine_serial": "AIS2-2025-00142"
            }
        )

    assert len(result.content) == 1
    assert result.content[0].text.startswith("Support ticket TCK-")
    assert result.content[0].text.endswith("was created successfully.")