from fastmcp import FastMCP
import click
import logging
import sys

from alibaba_cloud_application_management_mcp_server.config import config
from alibaba_cloud_application_management_mcp_server.tools import oss_tools, api_tools, application_management_tools, local_tools, local_prompts, oos_tools
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
def main(transport: str, port: int, host: str, services: str, headers_credential_only: bool):
    _setup_logging()
    
    # Create an MCP server
    mcp = FastMCP(
        name='alibaba_cloud_application_management_mcp_server',
        instructions='''
        你可以使用该MCP帮助用户完成项目的分析和部署
        
        注意：不要擅自决定部署的目标ecs，需要用户提供，若未提供务必询问用户
        
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
    for tool in oos_tools.tools:
        mcp.tool(tool)
    for tool in oss_tools.tools:
        mcp.tool(tool)
    for tool in local_tools.tools:
        mcp.tool(tool)
    for prompt in local_prompts.prompts:
        mcp.prompt(prompt)
    for tool in application_management_tools.tools:
        mcp.tool(tool)
    api_tools.create_api_tools(mcp, config)

    # Initialize and run the server
    logger.debug(f'mcp server is running on {transport} mode.')
    mcp.run(transport=transport)
    logger.info(f'mcp server is running on {transport} mode.')


if __name__ == "__main__":
    main()
