"""Connection error handling of the MCP client; no MCP server needed."""

import pytest
from src.mcp import client as mcp_client
from src.mcp.client import MCPConnection, create_mcp_client
from src.services.exceptions import ExternalServiceError


class FakeClient:
    def __init__(self, enter_error: Exception | None = None, exit_error: Exception | None = None) -> None:
        self.enter_error = enter_error
        self.exit_error = exit_error
        self.closed = False

    async def __aenter__(self) -> "FakeClient":
        if self.enter_error:
            raise self.enter_error
        return self

    async def __aexit__(self, exc_type, exc, traceback) -> None:
        self.closed = True
        if self.exit_error:
            raise self.exit_error


@pytest.mark.anyio
async def test_connection_yields_the_client() -> None:
    fake = FakeClient()

    async with MCPConnection(fake) as client:
        assert client is fake

    assert fake.closed


@pytest.mark.anyio
async def test_unreachable_server_raises_external_service_error() -> None:
    connection_error = ExceptionGroup("unhandled errors in a TaskGroup", [ConnectionError("All connection attempts failed")])

    with pytest.raises(ExternalServiceError, match="MCP service is currently unavailable."):
        async with MCPConnection(FakeClient(enter_error=connection_error)):
            pass


@pytest.mark.anyio
async def test_error_while_closing_raises_external_service_error() -> None:
    with pytest.raises(ExternalServiceError):
        async with MCPConnection(FakeClient(exit_error=ConnectionError("connection reset"))):
            pass


@pytest.mark.anyio
async def test_error_while_closing_does_not_hide_the_original_error() -> None:
    with pytest.raises(ExternalServiceError, match="MCP tool get_order_status_tool failed."):
        async with MCPConnection(FakeClient(exit_error=ConnectionError("connection reset"))):
            raise ExternalServiceError("MCP tool get_order_status_tool failed.")


@pytest.mark.anyio
async def test_real_client_against_a_closed_port_raises_external_service_error(monkeypatch: pytest.MonkeyPatch) -> None:
    # Nothing listens on port 9 (discard) locally: the real client fails to connect.
    monkeypatch.setattr(mcp_client, "MCP_SERVER_URL", "http://127.0.0.1:9/mcp")

    with pytest.raises(ExternalServiceError):
        async with create_mcp_client():
            pass
