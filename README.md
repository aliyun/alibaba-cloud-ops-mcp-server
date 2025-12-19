# Alibaba Cloud Ops MCP Server

[![GitHub stars](https://img.shields.io/github/stars/aliyun/alibaba-cloud-ops-mcp-server?style=social)](https://github.com/aliyun/alibaba-cloud-ops-mcp-server)

[中文版本](./README_zh.md)

Alibaba Cloud Ops MCP Server is a [Model Context Protocol (MCP)](https://modelcontextprotocol.io/introduction) server that provides seamless integration with Alibaba Cloud APIs, enabling AI assistants to operate resources on Alibaba Cloud, supporting ECS, Cloud Monitor, OOS, OSS, VPC, RDS and other widely used cloud products. It also enables AI assistants to analyze, build, and deploy applications to Alibaba Cloud ECS instances.

## Features

- **ECS Management**: Create, start, stop, reboot, delete instances, run commands, view instances, regions, zones, images, security groups, and more
- **VPC Management**: View VPCs and VSwitches
- **RDS Management**: List, start, stop, and restart RDS instances
- **OSS Management**: List, create, delete buckets, and view objects
- **Cloud Monitor**: Get CPU usage, load average, memory usage, and disk usage metrics for ECS instances
- **Application Deployment**: Deploy applications to ECS instances with automatic application and application group management
- **Project Analysis**: Automatically identify project technology stack and deployment methods (npm, Python, Java, Go, Docker, etc.)
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

[For detailed parameter description, see MCP startup parameter document](./README_mcp_args.md)

## MCP Maketplace Integration

* [Qoder](https://qoder.com) <a href="qoder://aicoding.aicoding-deeplink/mcp/add?name=alibaba-cloud-ops-mcp-server&config=JTdCJTIyY29tbWFuZCUyMiUzQSUyMnV2eCUyMiUyQyUyMmFyZ3MlMjIlM0ElNUIlMjJhbGliYWJhLWNsb3VkLW9wcy1tY3Atc2VydmVyJTQwbGF0ZXN0JTIyJTVEJTJDJTIyZW52JTIyJTNBJTdCJTIyQUxJQkFCQV9DTE9VRF9BQ0NFU1NfS0VZX0lEJTIyJTNBJTIyWW91ciUyMEFjY2VzcyUyMEtleSUyMElkJTIyJTJDJTIyQUxJQkFCQV9DTE9VRF9BQ0NFU1NfS0VZX1NFQ1JFVCUyMiUzQSUyMllvdXIlMjBBY2Nlc3MlMjBLZXklMjBTRUNSRVQlMjIlN0QlN0Q%3D"><img src="./image/qoder.svg" alt="Install MCP Server" height="20"></a>
* [Cursor](https://docs.cursor.com/tools) [![Install MCP Server](https://cursor.com/deeplink/mcp-install-dark.svg)](https://cursor.com/en/install-mcp?name=alibaba-cloud-ops-mcp-server&config=eyJ0aW1lb3V0Ijo2MDAsImNvbW1hbmQiOiJ1dnggYWxpYmFiYS1jbG91ZC1vcHMtbWNwLXNlcnZlckBsYXRlc3QiLCJlbnYiOnsiQUxJQkFCQV9DTE9VRF9BQ0NFU1NfS0VZX0lEIjoiWW91ciBBY2Nlc3MgS2V5IElkIiwiQUxJQkFCQV9DTE9VRF9BQ0NFU1NfS0VZX1NFQ1JFVCI6IllvdXIgQWNjZXNzIEtleSBTZWNyZXQifX0%3D)
* [Cline](https://cline.bot/mcp-marketplace)
* [ModelScope](https://www.modelscope.cn/mcp/servers/@aliyun/alibaba-cloud-ops-mcp-server?lang=en_US)
* [Lingma](https://lingma.aliyun.com/)
* [Smithery AI](https://smithery.ai/server/@aliyun/alibaba-cloud-ops-mcp-server)
* [FC-Function AI](https://cap.console.aliyun.com/template-detail?template=237)
* [Alibaba Cloud Model Studio](https://bailian.console.aliyun.com/?tab=mcp#/mcp-market/detail/alibaba-cloud-ops)

## Know More

* [Alibaba Cloud Ops MCP Server is ready to use out of the box!！](https://developer.aliyun.com/article/1661348)
* [Setup Alibaba Cloud Ops MCP Server on Bailian](https://developer.aliyun.com/article/1662120)
* [Build your own Alibaba Cloud OpenAPI MCP Server with 10 lines of code](https://developer.aliyun.com/article/1662202)
* [Alibaba Cloud Ops MCP Server is officially available on the Alibaba Cloud Model Studio Platform MCP Marketplace](https://developer.aliyun.com/article/1665019)

## Tools

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
| Application Management | OOS_CodeDeploy | Deploy applications to ECS instances with automatic artifact upload to OSS | OOS | Done |
| | OOS_GetDeployStatus | Query deployment status of application groups | API | Done |
| | OOS_GetLastDeploymentInfo | Retrieve information about the last deployment | API | Done |
| Local | LOCAL_ListDirectory | List files and subdirectories in a directory | Local | Done |
| | LOCAL_RunShellScript | Execute shell scripts or commands | Local | Done |
| | LOCAL_AnalyzeDeployStack | Identify project deployment methods and technology stack | Local | Done |

## Deployment Workflow

The typical deployment workflow includes:

1. **Project Analysis**: Use `LOCAL_AnalyzeDeployStack` to identify the project's technology stack and deployment method
2. **Build Artifacts**: Build or package the application locally (e.g., create tar.gz or zip files)
3. **Deploy Application**: Use `OOS_CodeDeploy` to deploy the application to ECS instances
   - Automatically creates application and application group if they don't exist
   - Uploads artifacts to OSS
   - Deploys to specified ECS instances
4. **Monitor Deployment**: Use `OOS_GetDeployStatus` to check deployment status

## Contact us

If you have any questions, please join the [Alibaba Cloud Ops MCP discussion group](https://qr.dingtalk.com/action/joingroup?code=v1,k1,iFxYG4jjLVh1jfmNAkkclji7CN5DSIdT+jvFsLyI60I=&_dt_no_comment=1&origin=11) (DingTalk group: 113455011677) for discussion.

<img src="https://oos-public-cn-hangzhou.oss-cn-hangzhou.aliyuncs.com/alibaba-cloud-ops-mcp-server/Alibaba-Cloud-Ops-MCP-User-Group-en.png" width="500">
