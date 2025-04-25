# alibaba-cloud-ops-mcp-server
[中文版本](./README_zh.md)

[![smithery badge](https://smithery.ai/badge/@aliyun/alibaba-cloud-ops-mcp-server)](https://smithery.ai/server/@aliyun/alibaba-cloud-ops-mcp-server)

## Prepare

Install [uv](https://github.com/astral-sh/uv)

```bash
# On macOS and Linux.
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Configuration

Use [VS Code](https://code.visualstudio.com/) + [Cline](https://cline.bot/) to config MCP Server.

### Installing via Smithery

To install Alibaba Cloud Operations Server for Claude Desktop automatically via [Smithery](https://smithery.ai/server/@aliyun/alibaba-cloud-ops-mcp-server):

```bash
npx -y @smithery/cli install @aliyun/alibaba-cloud-ops-mcp-server --client claude
```

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

<img src="https://github.com/aliyun/alibaba-cloud-ops-mcp-server/blob/master/image/Alibaba-Cloud-Ops-MCP-User-Group-en.png?raw=true" width="500">

## Know More

- [Alibaba Cloud MCP Server is ready to use out of the box!！](https://developer.aliyun.com/article/1661348)
