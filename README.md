# Alibaba Cloud MCP Server

[![GitHub stars](https://img.shields.io/github/stars/aliyun/alibaba-cloud-ops-mcp-server?style=social)](https://github.com/aliyun/alibaba-cloud-ops-mcp-server)

[中文版本](README_zh.md)

This repository contains two [Model Context Protocol (MCP)](https://modelcontextprotocol.io/introduction) servers that provide seamless integration with Alibaba Cloud services:

1. **Alibaba Cloud Ops MCP Server** - Enables AI assistants to operate resources on Alibaba Cloud, supporting ECS, Cloud Monitor, OOS, OSS, VPC, RDS and other widely used cloud products.
2. **Alibaba Cloud Application Management MCP Server** - Enables AI assistants to analyze, build, and deploy applications to Alibaba Cloud ECS instances.

## Features

### Alibaba Cloud Ops MCP Server

- **ECS Management**: Create, start, stop, reboot, delete instances, run commands, view instances, regions, zones, images, security groups, and more
- **VPC Management**: View VPCs and VSwitches
- **RDS Management**: List, start, stop, and restart RDS instances
- **OSS Management**: List, create, delete buckets, and view objects
- **Cloud Monitor**: Get CPU usage, load average, memory usage, and disk usage metrics for ECS instances
- **Dynamic API Tools**: Support for Alibaba Cloud OpenAPI operations

### Alibaba Cloud Application Management MCP Server

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

### Alibaba Cloud Ops MCP Server

To use `alibaba-cloud-ops-mcp-server` MCP Server with any other MCP Client, you can manually add this configuration and restart for changes to take effect:

```json
{
  "mcpServers": {
    "alibaba-cloud-ops-mcp-server": {
      "timeout": 600,
      "command": "uvx",
      "args": [
        "alibaba-cloud-ops-mcp-server@latest"
      ],
      "env": {
        "ALIBABA_CLOUD_ACCESS_KEY_ID": "Your Access Key ID",
        "ALIBABA_CLOUD_ACCESS_KEY_SECRET": "Your Access Key SECRET"
      }
    }
  }
}
```

### Alibaba Cloud Application Management MCP Server

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

## MCP Marketplace Integration

* [Cline](https://cline.bot/mcp-marketplace)
* [Cursor](https://docs.cursor.com/tools) [![Install MCP Server](https://cursor.com/deeplink/mcp-install-dark.svg)](https://cursor.com/en/install-mcp?name=alibaba-cloud-ops-mcp-server&config=eyJ0aW1lb3V0Ijo2MDAsImNvbW1hbmQiOiJ1dnggYWxpYmFiYS1jbG91ZC1vcHMtbWNwLXNlcnZlckBsYXRlc3QiLCJlbnYiOnsiQUxJQkFCQV9DTE9VRF9BQ0NFU1NfS0VZX0lEIjoiWW91ciBBY2Nlc3MgS2V5IElkIiwiQUxJQkFCQV9DTE9VRF9BQ0NFU1NfS0VZX1NFQ1JFVCI6IllvdXIgQWNjZXNzIEtleSBTZWNyZXQifX0%3D)
* [ModelScope](https://www.modelscope.cn/mcp/servers/@aliyun/alibaba-cloud-ops-mcp-server?lang=en_US)
* [Lingma](https://lingma.aliyun.com/)
* [Smithery AI](https://smithery.ai/server/@aliyun/alibaba-cloud-ops-mcp-server)
* [FC-Function AI](https://cap.console.aliyun.com/template-detail?template=237)
* [Alibaba Cloud Model Studio](https://bailian.console.aliyun.com/?tab=mcp#/mcp-market/detail/alibaba-cloud-ops)

## Know More

* [Alibaba Cloud Ops MCP Server is ready to use out of the box!](https://developer.aliyun.com/article/1661348)
* [Setup Alibaba Cloud Ops MCP Server on Bailian](https://developer.aliyun.com/article/1662120)
* [Build your own Alibaba Cloud OpenAPI MCP Server with 10 lines of code](https://developer.aliyun.com/article/1662202)
* [Alibaba Cloud Ops MCP Server is officially available on the Alibaba Cloud Model Studio Platform MCP Marketplace](https://developer.aliyun.com/article/1665019)

## Tools

### Alibaba Cloud Ops MCP Server Tools

| **Product** | **Tool** | **Function** | **Implementation** | **Status** |
| --- | --- | --- | --- | --- |
| ECS | RunCommand | Run Command | OOS | Done |
| | StartInstances | Start Instances | OOS | Done |
| | StopInstances | Stop Instances | OOS | Done |
| | RebootInstances | Reboot Instances | OOS | Done |
| | DescribeInstances | View Instances | API | Done |
| | DescribeRegions | View Regions | API | Done |
| | DescribeZones | View Zones | API | Done |
| | DescribeAvailableResource | View Resource Inventory | API | Done |
| | DescribeImages | View Images | API | Done |
| | DescribeSecurityGroups | View Security Groups | API | Done |
| | RunInstances | Create Instances | OOS | Done |
| | DeleteInstances | Delete Instances | API | Done |
| | ResetPassword | Modify Password | OOS | Done |
| | ReplaceSystemDisk | Replace Operating System | OOS | Done |
| VPC | DescribeVpcs | View VPCs | API | Done |
| | DescribeVSwitches | View VSwitches | API | Done |
| RDS | DescribeDBInstances | List RDS Instances | API | Done |
|  | StartDBInstances | Start the RDS instance | OOS | Done |
|  | StopDBInstances | Stop the RDS instance | OOS | Done |
|  | RestartDBInstances | Restart the RDS instance | OOS | Done |
| OSS | ListBuckets | List Bucket | API | Done |
|  | PutBucket | Create Bucket | API | Done |
|  | DeleteBucket | Delete Bucket | API | Done |
|  | ListObjects | View object information in the bucket | API | Done |
| CloudMonitor | GetCpuUsageData | Get CPU Usage Data for ECS Instances | API | Done |
| | GetCpuLoadavgData | Get CPU One-Minute Average Load Metric Data | API | Done |
| | GetCpuloadavg5mData | Get CPU Five-Minute Average Load Metric Data | API | Done |
| | GetCpuloadavg15mData | Get CPU Fifteen-Minute Average Load Metric Data | API | Done |
| | GetMemUsedData | Get Memory Usage Metric Data | API | Done |
| | GetMemUsageData | Get Memory Utilization Metric Data | API | Done |
| | GetDiskUsageData | Get Disk Utilization Metric Data | API | Done |
| | GetDiskTotalData | Get Total Disk Partition Capacity Metric Data | API | Done |
| | GetDiskUsedData | Get Disk Partition Usage Metric Data | API | Done |

### Alibaba Cloud Application Management MCP Server Tools

#### Application Management Tools

| **Tool** | **Function** | **Status** |
| --- | --- | --- |
| CodeDeploy | Deploy applications to ECS instances with automatic artifact upload to OSS | Done |
| GetDeployStatus | Query deployment status of application groups | Done |
| GetLastDeploymentInfo | Retrieve information about the last deployment | Done |

#### Local Tools

| **Tool** | **Function** | **Status** |
| --- | --- | --- |
| ListDirectory | List files and subdirectories in a directory | Done |
| RunShellScript | Execute shell scripts or commands | Done |
| AnalyzeDeployStack | Identify project deployment methods and technology stack | Done |

#### OOS Tools

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

<img src="src/alibaba_cloud_ops_mcp_server/image/Alibaba-Cloud-Ops-MCP-User-Group-en.png" width="500">

