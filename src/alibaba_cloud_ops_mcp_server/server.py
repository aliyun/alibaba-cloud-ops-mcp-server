from mcp.server.fastmcp import FastMCP
import click
import logging

from alibaba_cloud_ops_mcp_server.config import config
from alibaba_cloud_ops_mcp_server.tools import cms_tools, oos_tools, oss_tools, api_tools

logger = logging.getLogger(__name__)


@click.command()
@click.option(
    "--transport",
    type=click.Choice(["stdio", "sse", "streamable-http"]),
    default="stdio",
    help="Transport type",
)
@click.option(
    "--port",
    type=int,
    default=8000,
    help="Port number",
)
@click.option(
    "--host",
    type=str,
    default="127.0.0.1",
    help="Host",
)
def main(transport: str, port: int, host: str):
    # Create an MCP server
    mcp = FastMCP(
        name="alibaba-cloud-ops-mcp-server",
        port=port,
        host=host
    )
    for tool in oos_tools.tools:
        mcp.add_tool(tool)
    for tool in cms_tools.tools:
        mcp.add_tool(tool)
    for tool in oss_tools.tools:
        mcp.add_tool(tool)
    a = 1
    b = 1
    if a == b:
        print("a == b")
    api_tools.create_api_tools(mcp, config)

    # Initialize and run the server
    logger.debug(f'mcp server is running on {transport} mode.')
    mcp.run(transport=transport)


if __name__ == "__main__":
    main()
