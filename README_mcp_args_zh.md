# MCP 启动参数说明

本文档详细介绍 Alibaba Cloud MCP Server 的可用启动参数，帮助用户根据需求配置服务器。

## 参数列表

|          参数               | 是否必需 |  类型   |    默认值    | 说明                                                                                                                                                                                                                                                                                                                                                                                                                           |
|:---------------------------:|:-------:|:-------:|:------------:|:-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `--transport`               |    否    | string  |   `stdio`    | MCP Server 通信传输协议。<br>可选值：<br>&nbsp;&nbsp;&nbsp;&nbsp;• `stdio` <br>&nbsp;&nbsp;&nbsp;&nbsp;• `sse` <br>&nbsp;&nbsp;&nbsp;&nbsp;• `streamable-http`                                                                                                                                                                                                                                                                  |
| `--port`                    |    否    |  int    |   `8000`     | MCP Server 监听的端口号，请确保端口未被占用。                                                                                                                                                                                                                                                                                                                                                                                  |
| `--host`                    |    否    | string  | `127.0.0.1`  | MCP Server 监听的主机地址。`0.0.0.0` 表示监听所有网络接口。                                                                                                                                                                                                                                                                                                                                                                     |
| `--services`                |    否    | string  |    None      | 逗号分隔的服务列表，例如 `ecs,vpc`。<br>支持的服务：<br>&nbsp;&nbsp;&nbsp;&nbsp;• `ecs` - 弹性计算服务<br>&nbsp;&nbsp;&nbsp;&nbsp;• `oos` - 运维编排服务<br>&nbsp;&nbsp;&nbsp;&nbsp;• `rds` - 关系型数据库<br>&nbsp;&nbsp;&nbsp;&nbsp;• `vpc` - 专有网络<br>&nbsp;&nbsp;&nbsp;&nbsp;• `slb` - 负载均衡<br>&nbsp;&nbsp;&nbsp;&nbsp;• `ess` - 弹性伸缩<br>&nbsp;&nbsp;&nbsp;&nbsp;• `ros` - 资源编排<br>&nbsp;&nbsp;&nbsp;&nbsp;• `cbn` - 云企业网<br>&nbsp;&nbsp;&nbsp;&nbsp;• `dds` - MongoDB 数据库<br>&nbsp;&nbsp;&nbsp;&nbsp;• `r-kvstore` - Tair (兼容 Redis)<br>&nbsp;&nbsp;&nbsp;&nbsp;• `bssopenapi` - 费用中心 |
| `--headers-credential-only` |    否    |  bool   |   `false`    | 是否仅使用 HTTP 请求头中的凭证。启用后，凭证必须通过请求头提供，而非环境变量。                                                                                                                                                                                                                                                                                                                                                   |
| `--env`                     |    否    | string  |  `domestic`  | API 端点的环境类型。<br>可选值：<br>&nbsp;&nbsp;&nbsp;&nbsp;• `domestic` - 使用国内端点<br>&nbsp;&nbsp;&nbsp;&nbsp;• `international` - 使用国际端点                                                                                                                                                                                                                                                                              |
| `--code-deploy`             |    否    |  flag   |   `false`    | 启用代码部署模式。启用后，仅加载以下 6 个工具：<br>&nbsp;&nbsp;&nbsp;&nbsp;• `OOS_CodeDeploy`<br>&nbsp;&nbsp;&nbsp;&nbsp;• `OOS_GetDeployStatus`<br>&nbsp;&nbsp;&nbsp;&nbsp;• `OOS_GetLastDeploymentInfo`<br>&nbsp;&nbsp;&nbsp;&nbsp;• `LOCAL_ListDirectory`<br>&nbsp;&nbsp;&nbsp;&nbsp;• `LOCAL_RunShellScript`<br>&nbsp;&nbsp;&nbsp;&nbsp;• `LOCAL_AnalyzeDeployStack`                                                         |
| `--extra-config`            |    否    | string  |    None      | 动态添加额外的服务和 API（累加模式，不会替换现有配置）。支持 JSON 格式或 Python 字典格式（单引号）。<br>示例：`"{'sls': ['GetProject', 'ListProject'], 'ecs': ['StartInstance']}"`                                                                                                                                                                                                                                               |
| `--visible-tools`           |    否    | string  |    None      | 工具白名单模式。逗号分隔的工具名称列表，仅注册指定的工具。<br>示例：`OOS_RunCommand,ECS_DescribeInstances,LOCAL_ListDirectory`                                                                                                                                                                                                                                                                                                   |

## 使用示例

### 基本用法
```bash
uv run src/alibaba_cloud_ops_mcp_server/server.py --transport sse --port 8080 --host 0.0.0.0 --services ecs,vpc
```

### 代码部署模式
```bash
uv run src/alibaba_cloud_ops_mcp_server/server.py --code-deploy
```

### 通过 MCP 配置动态添加 API
使用 `--extra-config` 动态添加服务和 API：

```bash
# JSON 格式（内部使用双引号）
uv run src/alibaba_cloud_ops_mcp_server/server.py --extra-config '{"sls": ["GetProject", "ListProject"], "ecs": ["StartInstance"]}'

# Python 字典格式（内部使用单引号）
uv run src/alibaba_cloud_ops_mcp_server/server.py --extra-config "{'sls': ['GetProject', 'ListProject'], 'ecs': ['StartInstance']}"
```

### 白名单模式
使用 `--visible-tools` 仅暴露指定的工具：

```bash
uv run src/alibaba_cloud_ops_mcp_server/server.py --visible-tools "OOS_RunCommand,ECS_DescribeInstances,LOCAL_ListDirectory"
```

### 国际环境
```bash
uv run src/alibaba_cloud_ops_mcp_server/server.py --env international --services ecs,vpc
```

### MCP JSON 配置示例

您可以在 MCP 客户端的 JSON 配置文件中设置这些参数：

```json
{
  "mcpServers": {
    "alibabacloud": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/alibabacloud-mcp-server",
        "run",
        "src/alibaba_cloud_ops_mcp_server/server.py",
        "--extra-config",
        "{\"sls\": [\"GetProject\", \"ListProject\"], \"ecs\": [\"StartInstance\"]}"
      ],
      "env": {
        "ALIBABA_CLOUD_ACCESS_KEY_ID": "您的 Access Key ID",
        "ALIBABA_CLOUD_ACCESS_KEY_SECRET": "您的 Access Key Secret",
        "ALIBABA_CLOUD_REGION": "cn-hangzhou"
      }
    }
  }
}
```

---

如需更多帮助，请参考项目主文档或联系维护者。
