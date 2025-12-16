from fastmcp import FastMCP
import click
import logging

from alibaba_cloud_ops_mcp_server.tools.common_api_tools import set_custom_service_list
from alibaba_cloud_ops_mcp_server.config import config
from alibaba_cloud_ops_mcp_server.tools import cms_tools, oos_tools, oss_tools, api_tools, common_api_tools
from alibaba_cloud_ops_mcp_server.settings import settings

logger = logging.getLogger(__name__)

SUPPORTED_SERVICES_MAP = {
    "ecs": "Elastic Compute Service (ECS)",
    "oos": "Operations Orchestration Service (OOS)",
    "rds": "Relational Database Service (RDS)",
    "vpc": "Virtual Private Cloud (VPC)",
    "slb": "Server Load Balancer (SLB)",
    "ess": "Elastic Scaling (ESS)",
    "ros": "Resource Orchestration Service (ROS)",
    "cbn": "Cloud Enterprise Network (CBN)",
    "dds": "MongoDB Database Service (DDS)",
    "r-kvstore": "Cloud database Tair (compatible with Redis) (R-KVStore)",
    "bssopenapi": "Billing and Cost Management (BssOpenAPI)"
}


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
@click.option(
    "--services",
    type=str,
    default=None,
    help="Comma-separated list of supported services, e.g., 'ecs,vpc,rds'",
)
@click.option(
    "--headers-credential-only",
    type=bool,
    default=False,
    help="Whether to use credentials only from headers",
)
@click.option(
    "--env",
    type=click.Choice(["domestic", "international"]),
    default="domestic",
    help="Environment type: 'domestic' for domestic, 'international' for overseas (default: domestic)",
)
def main(transport: str, port: int, host: str, services: str, headers_credential_only: bool, env: str):
    # Create an MCP server
    mcp = FastMCP(
        name="alibaba-cloud-ops-mcp-server",
        port=port,
        host=host,
        stateless_http=True
    )
    if headers_credential_only:
        settings.headers_credential_only = headers_credential_only
    if env:
        settings.env = env
    if services:
        service_keys = [s.strip().lower() for s in services.split(",")]
        service_list = [(key, SUPPORTED_SERVICES_MAP.get(key, key)) for key in service_keys]
        set_custom_service_list(service_list)
        for tool in common_api_tools.tools:
            mcp.tool(tool)
    for tool in oos_tools.tools:
        mcp.tool(tool)
    for tool in cms_tools.tools:
        mcp.tool(tool)
    for tool in oss_tools.tools:
        mcp.tool(tool)
    api_tools.create_api_tools(mcp, config)

    # Initialize and run the server
    logger.debug(f'mcp server is running on {transport} mode.')
    mcp.run(transport=transport)


if __name__ == "__main__":
    main()
