# Build your own Alibaba Cloud OpenAPI MCP Server with 10 lines of code
# https://developer.aliyun.com/article/1662202
# example codes
from mcp.server.fastmcp import FastMCP
from alibaba_cloud_ops_mcp_server.tools import api_tools

def main():
    mcp = FastMCP("Example MCP server")
    config = {
        'ecs': ['DescribeInstances', 'DescribeRegions'],
        'vpc': ['DescribeVpcs', 'DescribeVSwitches']
    }
    api_tools.create_api_tools(mcp, config)
    mcp.run(transport='sse')

if __name__ == "__main__":
    main()
