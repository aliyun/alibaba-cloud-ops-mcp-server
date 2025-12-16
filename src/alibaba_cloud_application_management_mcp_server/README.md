# Alibaba Cloud Application Management MCP Server

[![GitHub stars](https://img.shields.io/github/stars/aliyun/alibaba-cloud-ops-mcp-server?style=social)](https://github.com/aliyun/alibaba-cloud-ops-mcp-server)

[中文版本](README_zh.md)

Alibaba Cloud Application Management MCP Server is a [Model Context Protocol (MCP)](https://modelcontextprotocol.io/introduction) server that provides seamless integration with Alibaba Cloud Application Management services, enabling AI assistants to analyze, build, and deploy applications to Alibaba Cloud ECS instances.

## Features

- **Application Deployment**: Deploy applications to ECS instances with automatic application and application group management
- **Project Analysis**: Automatically identify project technology stack and deployment methods (npm, Python, Java, Go, Docker, etc.)
- **Environment Installation**: Install deployment environments (Docker, Java, Python, Node.js, Go, Nginx, Git) on ECS instances
- **Deployment Management**: Query deployment status and retrieve last deployment information
- **OSS Integration**: Upload deployment artifacts to OSS buckets
- **Local File Operations**: List directories, run shell scripts, and analyze project structures
- **Dynamic API Tools**: Support for Alibaba Cloud OpenAPI operations

## Prepare

Install [uv](https://github.com/astral-sh/uv)

```bash
# On macOS and Linux.
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Configuration

Use [VS Code](https://code.visualstudio.com/) + [Cline](https://cline.bot/) to config MCP Server.

To use `alibaba-cloud-application-management-mcp-server` MCP Server with any other MCP Client, you can manually add this configuration and restart for changes to take effect:

```json
{
  "mcpServers": {
    "alibaba-cloud-application-management-mcp-server": {
      "timeout": 600,
      "command": "uvx",
      "args": [
        "alibaba-cloud-application-management-mcp-server@latest"
      ],
      "env": {
        "ALIBABA_CLOUD_ACCESS_KEY_ID": "Your Access Key ID",
        "ALIBABA_CLOUD_ACCESS_KEY_SECRET": "Your Access Key SECRET"
      }
    }
  }
}
```
## Tools

### Application Management Tools

| **Tool** | **Function** | **Status** |
| --- | --- | --- |
| CodeDeploy | Deploy applications to ECS instances with automatic artifact upload to OSS | Done |
| GetDeployStatus | Query deployment status of application groups | Done |
| GetLastDeploymentInfo | Retrieve information about the last deployment | Done |

### Local Tools

| **Tool** | **Function** | **Status** |
| --- | --- | --- |
| ListDirectory | List files and subdirectories in a directory | Done |
| RunShellScript | Execute shell scripts or commands | Done |
| AnalyzeDeployStack | Identify project deployment methods and technology stack | Done |

### OOS Tools

| **Tool** | **Function** | **Status** |
| --- | --- | --- |
| InstallDeploymentEnvironment | Install deployment environments (Docker, Java, Python, Node.js, Go, Nginx, Git) on ECS instances | Done |
| ListExecutions | Query OOS execution status by execution ID | Done |

## Deployment Workflow

The typical deployment workflow includes:

1. **Project Analysis**: Use `AnalyzeDeployStack` to identify the project's technology stack and deployment method
2. **Build Artifacts**: Build or package the application locally (e.g., create tar.gz or zip files)
3. **Deploy Application**: Use `CodeDeploy` to deploy the application to ECS instances
   - Automatically creates application and application group if they don't exist
   - Uploads artifacts to OSS
   - Deploys to specified ECS instances
4. **Install Environment** (Optional): Use `InstallDeploymentEnvironment` to install required runtime environments on ECS instances
5. **Monitor Deployment**: Use `GetDeployStatus` to check deployment status

## Contact us

If you have any questions, please join the [Alibaba Cloud Ops MCP discussion group](https://qr.dingtalk.com/action/joingroup?code=v1,k1,iFxYG4jjLVh1jfmNAkkclji7CN5DSIdT+jvFsLyI60I=&_dt_no_comment=1&origin=11) (DingTalk group: 113455011677) for discussion.

<img src="../alibaba_cloud_ops_mcp_server/image/Alibaba-Cloud-Ops-MCP-User-Group-en.png" width="500">
