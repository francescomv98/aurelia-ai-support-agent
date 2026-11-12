import os
from mcp import Client
from src.app_logging.logger import logger
from src.services.exceptions import ExternalServiceError

MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8001/mcp")


class MCPConnection:
    """Async context manager around the MCP client that reports connection failures as ExternalServiceError.

    The client connects in __aenter__, outside call_mcp_tool's error handling:
    without this wrapper an unreachable server surfaced as a raw ExceptionGroup
    and the API answered 500 instead of 503.
    """

    def __init__(self, client: Client) -> None:
        self._client = client

    async def __aenter__(self) -> Client:
        try:
            return await self._client.__aenter__()
        except Exception as exc:
            logger.error("MCP server unreachable", url=MCP_SERVER_URL, error=repr(exc))
            raise ExternalServiceError("MCP service is currently unavailable.") from exc

    async def __aexit__(self, exc_type, exc, traceback) -> bool | None:
        try:
            return await self._client.__aexit__(exc_type, exc, traceback)
        except Exception as close_exc:
            if exc is not None:
                # A failure while closing must not hide the error that ended the session.
                return False

            logger.error("MCP connection closed with an error", url=MCP_SERVER_URL, error=repr(close_exc))
            raise ExternalServiceError("MCP service is currently unavailable.") from close_exc


def create_mcp_client() -> MCPConnection:
    """Create an MCP client for the Aurelia MCP server, used as "async with create_mcp_client() as client"."""
    return MCPConnection(Client(MCP_SERVER_URL))


async def call_mcp_tool(client: Client, tool_name: str, arguments: dict[str, object]) -> str:
    """Call an MCP tool and return its text response."""
    try:
        result = await client.call_tool(tool_name, arguments)
    except Exception as exc:
        raise ExternalServiceError("MCP service is currently unavailable.") from exc

    if not result.content:
        raise ExternalServiceError("MCP service returned an empty response.")

    text_content = [item.text for item in result.content if hasattr(item, "text")]

    if not text_content:
        raise ExternalServiceError("MCP service returned an invalid response.")

    # A tool that raised on the server side comes back as an error result.
    # Never hand its error text to the LLM as if it were enterprise data.
    if result.is_error:
        logger.error("MCP tool returned an error", tool_name=tool_name, error="\n".join(text_content))
        raise ExternalServiceError(f"MCP tool {tool_name} failed.")

    return "\n".join(text_content)
