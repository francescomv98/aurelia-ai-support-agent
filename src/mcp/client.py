import os
from mcp import Client
from src.app_logging.logger import logger
from src.services.exceptions import ExternalServiceError

MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8001/mcp")


def create_mcp_client() -> Client:
    """Create an MCP client for the Aurelia MCP server."""
    return Client(MCP_SERVER_URL)


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
