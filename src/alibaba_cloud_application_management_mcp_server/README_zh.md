# Alibaba Cloud Application Management MCP Server

[![GitHub stars](https://img.shields.io/github/stars/aliyun/alibaba-cloud-ops-mcp-server?style=social)](https://github.com/aliyun/alibaba-cloud-ops-mcp-server)

[English README](README.md)

Alibaba Cloud Application Management MCP Server 是一个[模型上下文协议（MCP）](https://modelcontextprotocol.io/introduction)服务器，提供与阿里云应用管理服务的无缝集成，使 AI 助手能够分析、构建和部署应用到阿里云 ECS 实例。

## 功能特性

- **应用部署**：自动部署应用到 ECS 实例，支持自动创建应用和应用分组
- **项目分析**：自动识别项目技术栈和部署方式（npm、Python、Java、Go、Docker 等）
- **环境安装**：在 ECS 实例上安装部署环境（Docker、Java、Python、Node.js、Go、Nginx、Git）
- **部署管理**：查询部署状态和获取上次部署信息
- **OSS 集成**：将部署产物上传到 OSS 存储桶
- **本地文件操作**：列出目录、执行 shell 脚本、分析项目结构
- **动态 API 工具**：支持阿里云 OpenAPI 操作

## 准备

安装 [uv](https://github.com/astral-sh/uv)

```bash
# On macOS and Linux.
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## 配置

使用 [VS Code](https://code.visualstudio.com/) + [Cline](https://cline.bot/) 配置 MCP Server。

要将 `alibaba-cloud-application-management-mcp-server` MCP 服务器与任何其他 MCP 客户端一起使用，您可以手动添加此配置并重新启动以使更改生效：

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
## 功能点（Tool）

### 应用管理工具

| **工具** | **功能** | **状态** |
| --- | --- | --- |
| CodeDeploy | 部署应用到 ECS 实例，自动上传部署产物到 OSS | Done |
| GetDeployStatus | 查询应用分组的部署状态 | Done |
| GetLastDeploymentInfo | 获取上次部署的信息 | Done |

### 本地工具

| **工具** | **功能** | **状态** |
| --- | --- | --- |
| ListDirectory | 列出目录中的文件和子目录 | Done |
| RunShellScript | 执行 shell 脚本或命令 | Done |
| AnalyzeDeployStack | 识别项目部署方式和技术栈 | Done |

### OOS 工具

| **工具** | **功能** | **状态** |
| --- | --- | --- |
| InstallDeploymentEnvironment | 在 ECS 实例上安装部署环境（Docker、Java、Python、Node.js、Go、Nginx、Git） | Done |
| ListExecutions | 根据执行 ID 查询 OOS 执行状态 | Done |

## 部署流程

典型的部署流程包括：

1. **项目分析**：使用 `AnalyzeDeployStack` 识别项目的技术栈和部署方式
2. **构建产物**：在本地构建或打包应用（例如，创建 tar.gz 或 zip 文件）
3. **部署应用**：使用 `CodeDeploy` 将应用部署到 ECS 实例
   - 如果应用和应用分组不存在，会自动创建
   - 自动上传部署产物到 OSS
   - 部署到指定的 ECS 实例
4. **安装环境**（可选）：使用 `InstallDeploymentEnvironment` 在 ECS 实例上安装所需的运行时环境
5. **监控部署**：使用 `GetDeployStatus` 检查部署状态

## 重要提示

1. **启动脚本**：启动脚本（`application_start`）必须与上传的产物对应。如果产物是压缩包（tar、tar.gz、zip 等），需要先解压并进入对应目录后再执行启动命令。

2. **后台运行**：启动命令应该将程序运行在后台并打印日志到指定文件，使用非交互式命令（如 `unzip -o` 等自动覆盖的命令）。

3. **安全组配置**：部署完成后，需要在 ECS 实例的安全组中开放应用端口，否则应用无法从外部访问。

4. **ECS 实例**：部署前需要提供 ECS 实例 ID。如果未提供，工具会返回提示信息，引导用户到 ECS 控制台创建实例。

## 联系我们

如果您有任何疑问，欢迎加入 [Alibaba Cloud Ops MCP 交流群](https://qr.dingtalk.com/action/joingroup?code=v1,k1,iFxYG4jjLVh1jfmNAkkclji7CN5DSIdT+jvFsLyI60I=&_dt_no_comment=1&origin=11) (钉钉群：113455011677) 进行交流。

<img src="../alibaba_cloud_ops_mcp_server/image/Alibaba-Cloud-Ops-MCP-User-Group-zh.png" width="500">

