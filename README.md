# Alibaba Cloud Ops MCP Server

[![GitHub stars](https://img.shields.io/github/stars/aliyun/alibaba-cloud-ops-mcp-server?style=social)](https://github.com/aliyun/alibaba-cloud-ops-mcp-server)

[中文版本](./README_zh.md)

Alibaba Cloud Ops MCP Server is a [Model Context Protocol (MCP)](https://modelcontextprotocol.io/introduction) server that provides seamless integration with Alibaba Cloud APIs, enabling AI assistants to operation resources on Alibaba Cloud, supporting ECS, Cloud Monitor, OOS andother widely used cloud products.

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

* [Cline](https://cline.bot/mcp-marketplace)
* [Cursor](https://docs.cursor.com/tools) [![Install MCP Server](https://cursor.com/deeplink/mcp-install-dark.svg)](https://cursor.com/install-mcp?name=alibaba-cloud-ops-mcp-server&config=eyJ0aW1lb3V0Ijo2MDAsImNvbW1hbmQiOiJ1dnggYWxpYmFiYS1jbG91ZC1vcHMtbWNwLXNlcnZlckBsYXRlc3QiLCJlbnYiOnsiQUxJQkFCQV9DTE9VRF9BQ0NFU1NfS0VZX0lEIjoiWW91ciBBY2Nlc3MgS2V5IElEIiwiQUxJQkFCQV9DTE9VRF9BQ0NFU1NfS0VZX1NFQ1JFVCI6IllvdXIgQWNjZXNzIEtleSBTRUNSRVQifX0%3D)
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

| **Product** | **Tool** | **Function** | **Implematation** | **Status** |
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

## Contact us

If you have any questions, please join the [Alibaba Cloud Ops MCP discussion group](https://qr.dingtalk.com/action/joingroup?code=v1,k1,iFxYG4jjLVh1jfmNAkkclji7CN5DSIdT+jvFsLyI60I=&_dt_no_comment=1&origin=11) (DingTalk group: 113455011677) for discussion.

<img src="https://oos-public-cn-hangzhou.oss-cn-hangzhou.aliyuncs.com/alibaba-cloud-ops-mcp-server/Alibaba-Cloud-Ops-MCP-User-Group-en.png" width="500">
