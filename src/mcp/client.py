from mcp import Client

MCP_SERVER_URL = "http://localhost:8001/mcp"


def create_mcp_client() -> Client:
    """Create an MCP client for the Aurelia MCP server."""
    return Client(MCP_SERVER_URL)