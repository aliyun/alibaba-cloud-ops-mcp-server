# Alibaba Cloud Ops MCP Server

[![GitHub stars](https://img.shields.io/github/stars/aliyun/alibaba-cloud-ops-mcp-server?style=social)](https://github.com/aliyun/alibaba-cloud-ops-mcp-server)

[English README](./README.md)

Alibaba Cloud Ops MCP Server是一个[模型上下文协议（MCP）](https://modelcontextprotocol.io/introduction)服务器，提供与阿里云API的无缝集成，使AI助手能够操作阿里云上的资源，支持ECS、云监控、OOS、OSS、VPC、RDS等广泛使用的云产品。同时，它还使AI助手能够分析、构建和部署应用到阿里云ECS实例。

## 功能特性

- **ECS 管理**：创建、启动、停止、重启、删除实例，运行命令，查看实例、地域、可用区、镜像、安全组等
- **VPC 管理**：查看 VPC 和 VSwitch
- **RDS 管理**：查询、启动、停止、重启 RDS 实例
- **OSS 管理**：查看、创建、删除存储桶，查看对象信息
- **云监控**：获取 ECS 实例的 CPU 使用率、负载平均值、内存使用率和磁盘使用率指标
- **应用部署**：自动部署应用到 ECS 实例，支持自动创建应用和应用分组
- **项目分析**：自动识别项目技术栈和部署方式（npm、Python、Java、Go、Docker 等）
- **本地文件操作**：列出目录、执行 shell 脚本、分析项目结构
- **动态 API 工具**：支持阿里云 OpenAPI 操作

## 准备

安装[uv](https://github.com/astral-sh/uv)

```bash
# On macOS and Linux.
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## 配置

使用 [VS Code](https://code.visualstudio.com/) + [Cline](https://cline.bot/) 配置MCP Server

要将 `alibaba-cloud-ops-mcp-server` MCP 服务器与任何其他 MCP 服务器一起使用，您可以手动添加此配置并重新启动以使更改生效：

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

[详细参数说明见 MCP 启动参数文档](./README_mcp_args.md)

## MCP市场集成

* [Qoder](https://qoder.com) <a href="qoder://aicoding.aicoding-deeplink/mcp/add?name=alibaba-cloud-ops-mcp-server&config=JTdCJTIyY29tbWFuZCUyMiUzQSUyMnV2eCUyMiUyQyUyMmFyZ3MlMjIlM0ElNUIlMjJhbGliYWJhLWNsb3VkLW9wcy1tY3Atc2VydmVyJTQwbGF0ZXN0JTIyJTVEJTJDJTIyZW52JTIyJTNBJTdCJTIyQUxJQkFCQV9DTE9VRF9BQ0NFU1NfS0VZX0lEJTIyJTNBJTIyWW91ciUyMEFjY2VzcyUyMEtleSUyMElkJTIyJTJDJTIyQUxJQkFCQV9DTE9VRF9BQ0NFU1NfS0VZX1NFQ1JFVCUyMiUzQSUyMllvdXIlMjBBY2Nlc3MlMjBLZXklMjBTRUNSRVQlMjIlN0QlN0Q%3D"><img src="./image/qoder.svg" alt="Install MCP Server" height="20"></a>
* [Cursor](https://docs.cursor.com/tools) [![Install MCP Server](https://cursor.com/deeplink/mcp-install-dark.svg)](https://cursor.com/en/install-mcp?name=alibaba-cloud-ops-mcp-server&config=eyJ0aW1lb3V0Ijo2MDAsImNvbW1hbmQiOiJ1dnggYWxpYmFiYS1jbG91ZC1vcHMtbWNwLXNlcnZlckBsYXRlc3QiLCJlbnYiOnsiQUxJQkFCQV9DTE9VRF9BQ0NFU1NfS0VZX0lEIjoiWW91ciBBY2Nlc3MgS2V5IElkIiwiQUxJQkFCQV9DTE9VRF9BQ0NFU1NfS0VZX1NFQ1JFVCI6IllvdXIgQWNjZXNzIEtleSBTZWNyZXQifX0%3D)
* [Cline](https://cline.bot/mcp-marketplace)
* [魔搭](https://www.modelscope.cn/mcp/servers/@aliyun/alibaba-cloud-ops-mcp-server)
* [通义灵码](https://lingma.aliyun.com/)
* [Smithery AI](https://smithery.ai/server/@aliyun/alibaba-cloud-ops-mcp-server)
* [FC-Function AI](https://cap.console.aliyun.com/template-detail?template=237)
* [阿里云百炼平台](https://bailian.console.aliyun.com/?tab=mcp#/mcp-market/detail/alibaba-cloud-ops)

## 了解更多

* [阿里云 MCP Server 开箱即用！](https://developer.aliyun.com/article/1661348)
* [在百炼平台配置您的自定义阿里云MCP Server](https://developer.aliyun.com/article/1662120)
* [10行代码，实现你的专属阿里云OpenAPI MCP Server](https://developer.aliyun.com/article/1662202)
* [阿里云CloudOps MCP正式上架百炼平台MCP市场](https://developer.aliyun.com/article/1665019)

## 功能点（Tool）

| **产品** | **工具** | **功能** | **实现方式** | **状态** |
| --- | --- | --- | --- | --- |
| ECS | RunCommand | 运行命令 | OOS | Done |
|  | StartInstances | 启动实例 | OOS | Done |
|  | StopInstances | 停止实例 | OOS | Done |
|  | RebootInstances | 重启实例 | OOS | Done |
|  | DescribeInstances | 查看实例 | API | Done |
|  | DescribeRegions | 查看地域 | API | Done |
|  | DescribeZones | 查看可用区 | API | Done |
|  | DescribeAvailableResource | 查看资源库存 | API | Done |
|  | DescribeImages | 查看镜像 | API | Done |
|  | DescribeSecurityGroups | 查看安全组 | API | Done |
|  | RunInstances | 创建实例 | OOS | Done |
|  | DeleteInstances | 删除实例 | API | Done |
|  | ResetPassword | 修改密码 | OOS | Done |
|  | ReplaceSystemDisk | 更换操作系统 | OOS | Done |
| VPC | DescribeVpcs | 查看VPC | API | Done |
|  | DescribeVSwitches | 查看VSwitch | API | Done |
| RDS | DescribeDBInstances | 查询数据库实例列表 | API | Done |
|  | StartDBInstances | 启动RDS实例 | OOS | Done |
|  | StopDBInstances | 暂停RDS实例 | OOS | Done |
|  | RestartDBInstances | 重启RDS实例 | OOS | Done |
| OSS | ListBuckets | 查看存储空间 | API | Done |
|  | PutBucket | 创建存储空间 | API | Done |
|  | DeleteBucket | 删除存储空间 | API | Done |
|  | ListObjects | 查看存储空间中的文件信息 | API | Done |
| CloudMonitor | GetCpuUsageData | 获取ECS实例的CPU使用率数据 | API | Done |
|  | GetCpuLoadavgData | 获取CPU一分钟平均负载指标数据 | API | Done |
|  | GetCpuloadavg5mData | 获取CPU五分钟平均负载指标数据 | API | Done |
|  | GetCpuloadavg15mData | 获取CPU十五分钟平均负载指标数据 | API | Done |
|  | GetMemUsedData | 获取内存使用量指标数据 | API | Done |
|  | GetMemUsageData | 获取内存利用率指标数据 | API | Done |
|  | GetDiskUsageData | 获取磁盘利用率指标数据 | API | Done |
|  | GetDiskTotalData | 获取磁盘分区总容量指标数据 | API | Done |
|  | GetDiskUsedData | 获取磁盘分区使用量指标数据 | API | Done |
| 应用管理 | OOS_CodeDeploy | 部署应用到 ECS 实例，自动上传部署产物到 OSS | OOS | Done |
|  | OOS_GetDeployStatus | 查询应用分组的部署状态 | API | Done |
|  | OOS_GetLastDeploymentInfo | 获取上次部署的信息 | API | Done |
| 本地工具 | LOCAL_ListDirectory | 列出目录中的文件和子目录 | Local | Done |
|  | LOCAL_RunShellScript | 执行 shell 脚本或命令 | Local | Done |
|  | LOCAL_AnalyzeDeployStack | 识别项目部署方式和技术栈 | Local | Done |

## 部署流程

典型的部署流程包括：

1. **项目分析**：使用 `LOCAL_AnalyzeDeployStack` 识别项目的技术栈和部署方式
2. **构建产物**：在本地构建或打包应用（例如，创建 tar.gz 或 zip 文件）
3. **部署应用**：使用 `OOS_CodeDeploy` 将应用部署到 ECS 实例
   - 如果应用和应用分组不存在，会自动创建
   - 自动上传部署产物到 OSS
   - 部署到指定的 ECS 实例
4. **监控部署**：使用 `OOS_GetDeployStatus` 检查部署状态

## 重要提示

1. **启动脚本**：启动脚本（`application_start`）必须与上传的产物对应。如果产物是压缩包（tar、tar.gz、zip 等），需要先解压并进入对应目录后再执行启动命令。

2. **后台运行**：启动命令应该将程序运行在后台并打印日志到指定文件，使用非交互式命令（如 `unzip -o` 等自动覆盖的命令）。

3. **安全组配置**：部署完成后，需要在 ECS 实例的安全组中开放应用端口，否则应用无法从外部访问。

4. **ECS 实例**：部署前需要提供 ECS 实例 ID。如果未提供，工具会返回提示信息，引导用户到 ECS 控制台创建实例。

## 联系我们

如果您有任何疑问，欢迎加入 [Alibaba Cloud Ops MCP 交流群](https://qr.dingtalk.com/action/joingroup?code=v1,k1,iFxYG4jjLVh1jfmNAkkclji7CN5DSIdT+jvFsLyI60I=&_dt_no_comment=1&origin=11) (钉钉群：113455011677) 进行交流。

<img src="https://oos-public-cn-hangzhou.oss-cn-hangzhou.aliyuncs.com/alibaba-cloud-ops-mcp-server/Alibaba-Cloud-Ops-MCP-User-Group-zh.png" width="500">
