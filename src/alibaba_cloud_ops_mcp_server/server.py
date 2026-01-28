import sys
import copy
import json
import ast

from fastmcp import FastMCP
import click
import logging

from alibaba_cloud_ops_mcp_server.tools.common_api_tools import set_custom_service_list
from alibaba_cloud_ops_mcp_server.config import config
from alibaba_cloud_ops_mcp_server.tools import cms_tools, oos_tools, oss_tools, api_tools, common_api_tools, local_tools, application_management_tools
from alibaba_cloud_ops_mcp_server.settings import settings


logger = logging.getLogger(__name__)


def _setup_logging():
    root_logger = logging.getLogger()
    if not root_logger.handlers:
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        formatter = logging.Formatter(log_format)

        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setFormatter(formatter)

        root_logger.setLevel(logging.INFO)
        root_logger.addHandler(console_handler)
    else:
        root_logger.setLevel(logging.INFO)


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


def _register_tools_with_filter(mcp: FastMCP, visible_tools_set: set, visible_tools_original: dict, services: str, extra_config: str):
    """
    Register tools based on visible_tools whitelist (case-insensitive).
    
    Args:
        mcp: FastMCP instance
        visible_tools_set: Set of allowed tool names (lowercase for case-insensitive matching)
        visible_tools_original: Dict mapping lowercase names to original names
        services: Services parameter for common_api_tools
        extra_config: Extra config parameter
    """
    registered_tools = set()
    
    # 1. Register common_api_tools if services is specified
    if services:
        service_keys = [s.strip().lower() for s in services.split(",")]
        service_list = [(key, SUPPORTED_SERVICES_MAP.get(key, key)) for key in service_keys]
        set_custom_service_list(service_list)
        for tool in common_api_tools.tools:
            if tool.__name__.lower() in visible_tools_set:
                mcp.tool(tool)
                registered_tools.add(tool.__name__.lower())
    
    # 2. Register static tools from all modules
    static_tool_modules = [
        oos_tools,
        application_management_tools,
        cms_tools,
        oss_tools,
        local_tools
    ]
    
    for tool_module in static_tool_modules:
        for tool in tool_module.tools:
            if tool.__name__.lower() in visible_tools_set:
                mcp.tool(tool)
                registered_tools.add(tool.__name__.lower())
    
    # 3. Handle dynamic API tools
    # Parse tool names in visible_tools that follow SERVICE_API format
    # Use original names to preserve API case (important for Alibaba Cloud APIs)
    dynamic_tools_config = {}
    
    for tool_name_lower in visible_tools_set:
        if '_' in tool_name_lower and tool_name_lower not in registered_tools:
            # Get original name to preserve API case
            original_name = visible_tools_original.get(tool_name_lower, tool_name_lower)
            parts = original_name.split('_', 1)
            if len(parts) == 2:
                service_code = parts[0].lower()
                api_name = parts[1]  # Preserve original case
                if service_code not in dynamic_tools_config:
                    dynamic_tools_config[service_code] = []
                if api_name not in dynamic_tools_config[service_code]:
                    dynamic_tools_config[service_code].append(api_name)
    
    # 4. Merge with extra_config (only tools in visible_tools whitelist)
    if extra_config:
        try:
            try:
                extra = json.loads(extra_config)
            except json.JSONDecodeError:
                extra = ast.literal_eval(extra_config)
            
            for service_code, apis in extra.items():
                for api in apis:
                    tool_name_lower = f"{service_code.lower()}_{api.lower()}"
                    if tool_name_lower in visible_tools_set:
                        if service_code not in dynamic_tools_config:
                            dynamic_tools_config[service_code] = []
                        if api not in dynamic_tools_config[service_code]:
                            dynamic_tools_config[service_code].append(api)
            logger.info(f'Merged extra config with visible tools filter: {dynamic_tools_config}')
        except Exception as e:
            logger.error(f'Failed to parse extra-config: {e}')
    
    # 5. Create dynamic API tools
    if dynamic_tools_config:
        api_tools.create_api_tools(mcp, dynamic_tools_config)
        for service_code, apis in dynamic_tools_config.items():
            for api in apis:
                registered_tools.add(f"{service_code.lower()}_{api.lower()}")
    
    # 6. Log results
    unregistered_tools = visible_tools_set - registered_tools
    if unregistered_tools:
        logger.warning(f"The following tools were not found and not registered: {unregistered_tools}")
    
    logger.info(f"Visible tools mode: registered {len(registered_tools)} tools: {registered_tools}")


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
@click.option(
    "--code-deploy",
    is_flag=True,
    default=False,
    help="Enable code deploy mode, only load 6 specific tools: OOS_CodeDeploy, OOS_GetDeployStatus, OOS_GetLastDeploymentInfo, LOCAL_ListDirectory, LOCAL_RunShellScript, LOCAL_AnalyzeDeployStack",
)
@click.option(
    "--extra-config",
    type=str,
    default=None,
    help="Add extra services and APIs to config, e.g., \"{'sls': ['GetProject', 'ListProject'], 'ecs': ['StartInstance']}\"",
)
@click.option(
    "--visible-tools",
    type=str,
    default=None,
    help="Comma-separated list of tool names to make visible (whitelist mode). Only these tools will be registered when specified, e.g., 'OOS_RunCommand,ECS_DescribeInstances,LOCAL_ListDirectory'",
)
def main(transport: str, port: int, host: str, services: str, headers_credential_only: bool, env: str, code_deploy: bool, extra_config: str, visible_tools: str):
    _setup_logging()
    # Create an MCP server
    mcp = FastMCP(
        name="alibaba-cloud-ops-mcp-server",
        instructions='''
            智能运维场景：
            你可以使用该MCP帮助用户完成智能运维
            通过MCP提供的各种资源运维的功能来进行实现
            
            应用部署场景：
            你可以使用该MCP帮助用户完成项目的分析和部署
            当进入该场景时，请只使用以下列表中的Tool
            【 OOS_CodeDeploy OOS_GetLastDeploymentInfo OOS_GetDeployStatus LOCAL_ListDirectory LOCAL_RunShellScript LOCAL_AnalyzeDeployStack】
            注意：不要擅自决定部署的目标ecs，需要用户提供，若未提供务必询问用户，不允许直接调用DescribeInstances查找ECS实例，必须使用由用户提供的ECS实例

            不要创建部署脚本文件，直接使用 mcp tool: Code Deploy 进行构建
            
            流程如下：
             完整部署流程（在调用此工具之前）：

                步骤 1：识别部署方式 AnalyzeDeployStack
                - 通过本地文件操作工具读取项目文件（package.json、requirements.txt、pom.xml 等）
                - 识别项目的部署方式和技术栈（npm、python、java、go 等）
                - 生成构建命令，注意，该构建命令不需要生成构建脚本，不要因此新增sh文件，任何情况下都不要，因为构建命令是CodeDeploy的参数，不需要生成文件

                步骤 2：构建或压缩文件，并记录文件路径
                - 在本地执行构建命令，生成部署产物（tar.gz、zip 等压缩包）
                - 记录文件路径，留待后续CodeDeploy使用

                步骤 3：调用CodeDeploy进行部署
                - 此工具会依次调用：CreateApplication（如果不存在）、CreateApplicationGroup（如果不存在）、
                  TagResources（可选，如果是已有资源需要打 tag 导入应用分组）、DeployApplicationGroup

                步骤 4：如果用户的实例为第一次部署，缺乏对应代码运行环境，可以调用InstallDeploymentEnvironment为用户安装环境
                - 目前支持：
                    Docker：Docker 社区版
                    Java：Java 编程语言环境
                    Python：Python 编程语言环境
                    Nodejs：Node.js 运行环境
                    Golang：Go 编程语言环境
                    Nginx：高性能 HTTP 及反向代理服务器
                    Git：分布式版本控制系统

                重要提示：
                1. 启动脚本（application_start）必须与上传的产物对应。如果产物是压缩包（tar、tar.gz、zip等），
                   需要先解压并进入对应目录后再执行启动命令。
                2. 示例：如果上传的是 app.tar.gz，启动脚本应该类似，一般压缩包就在当前目录下，直接解压即可：
                   "tar -xzf app.tar.gz && ./start.sh"
                   或者如果解压后是Java应用：
                   "tar -xzf app.tar.gz && java -jar app.jar"
                3. 确保启动命令能够正确找到并执行解压后的可执行文件或脚本，避免部署失败。启动命令应该将程序运行在后台并打印日志到指定文件，
                    注意使用非交互式命令，比如unzip -o等自动覆盖的命令，无需交互
                例如：
                   - npm 程序示例：
                     "tar -xzf app.tar.gz && nohup npm start > /root/app.log 2>&1 &"
                     或者分别输出标准输出和错误日志：
                     "tar -xzf app.tar.gz && nohup npm start > /root/app.log 2> /root/app.error.log &"
                   - Java 程序示例：
                     "tar -xzf app.tar.gz && nohup java -jar app.jar > /root/app.log 2>&1 &"
                   - Python 程序示例：
                     "tar -xzf app.tar.gz && nohup python app.py > /root/app.log 2>&1 &"
                   说明：使用 nohup 命令可以让程序在后台运行，即使终端关闭也不会终止；> 重定向标准输出到日志文件；2>&1 将标准错误也重定向到同一文件；& 符号让命令在后台执行。
                4. 应用和应用分组会自动检查是否存在，如果存在则跳过创建，避免重复创建错误。''',
        port=port,
        host=host,
        stateless_http=True
    )
    if headers_credential_only:
        settings.headers_credential_only = headers_credential_only
    if env:
        settings.env = env
    
    # Handle mutual exclusivity between code_deploy and visible_tools
    if code_deploy and visible_tools:
        logger.warning("--code-deploy and --visible-tools are mutually exclusive. Using --code-deploy mode.")
        visible_tools = None
    
    if code_deploy:
        # Code deploy mode: only load 6 specific tools
        code_deploy_tools = {
            'OOS_CodeDeploy',
            'OOS_GetDeployStatus',
            'OOS_GetLastDeploymentInfo',
            'ECS_DescribeInstances',
            'LOCAL_ListDirectory',
            'LOCAL_RunShellScript',
            'LOCAL_AnalyzeDeployStack'
        }
        
        # Load from application_management_tools
        for tool in application_management_tools.tools:
            if tool.__name__ in code_deploy_tools:
                mcp.tool(tool)
        
        # Load from local_tools
        for tool in local_tools.tools:
            if tool.__name__ in code_deploy_tools:
                mcp.tool(tool)
    elif visible_tools:
        # Visible tools mode: only load tools in whitelist (case-insensitive)
        # Build both lowercase set and original name mapping
        visible_tools_list = [tool.strip() for tool in visible_tools.split(",") if tool.strip()]
        visible_tools_set = set(t.lower() for t in visible_tools_list)
        visible_tools_original = {t.lower(): t for t in visible_tools_list}
        if visible_tools_set:
            logger.info(f"Visible tools mode enabled (case-insensitive). Allowed tools: {visible_tools_set}")
            _register_tools_with_filter(mcp, visible_tools_set, visible_tools_original, services, extra_config)
        else:
            logger.warning("--visible-tools is empty, falling back to normal mode.")
            # Fall through to normal mode by setting a flag
            visible_tools = None
    
    if not code_deploy and not visible_tools:
        # Normal mode: load all tools
        if services:
            service_keys = [s.strip().lower() for s in services.split(",")]
            service_list = [(key, SUPPORTED_SERVICES_MAP.get(key, key)) for key in service_keys]
            set_custom_service_list(service_list)
            for tool in common_api_tools.tools:
                mcp.tool(tool)
        for tool in oos_tools.tools:
            mcp.tool(tool)
        for tool in application_management_tools.tools:
            # Skip ECS_DescribeInstances in normal mode
            if tool.__name__ != 'ECS_DescribeInstances':
                mcp.tool(tool)
        for tool in cms_tools.tools:
            mcp.tool(tool)
        for tool in oss_tools.tools:
            mcp.tool(tool)
        # Merge extra_config into the existing config
        merged_config = copy.deepcopy(config)
        if extra_config:
            try:
                # Try JSON first, then fallback to ast.literal_eval for single quotes
                try:
                    extra = json.loads(extra_config)
                except json.JSONDecodeError:
                    extra = ast.literal_eval(extra_config)
                for service_code, apis in extra.items():
                    if service_code in merged_config:
                        # Add new APIs to existing service (avoid duplicates)
                        existing_apis = set(merged_config[service_code])
                        for api in apis:
                            if api not in existing_apis:
                                merged_config[service_code].append(api)
                    else:
                        # Add new service with its APIs
                        merged_config[service_code] = apis
                logger.info(f'Merged extra config: {extra}')
            except Exception as e:
                logger.error(f'Failed to parse extra-config: {e}')
        api_tools.create_api_tools(mcp, merged_config)
        for tool in local_tools.tools:
            mcp.tool(tool)

    # Initialize and run the server
    logger.debug(f'mcp server is running on {transport} mode.')
    mcp.run(transport=transport)


if __name__ == "__main__":
    main()
