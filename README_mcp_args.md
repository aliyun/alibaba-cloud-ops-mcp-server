# MCP Startup Parameters Guide

This document provides a detailed introduction to the available parameters for starting the Alibaba Cloud MCP Server, helping users configure the server according to their needs.

## Parameter Table

|       Parameter             | Required |  Type   |   Default    | Description                                                                                                                                                                                                                                                                                                                                                                                                                           |
|:---------------------------:|:--------:|:-------:|:------------:|:--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `--transport`               |    No    | string  |   `stdio`    | Transport protocol for MCP Server communication.<br>Options:<br>&nbsp;&nbsp;&nbsp;&nbsp;• `stdio` <br>&nbsp;&nbsp;&nbsp;&nbsp;• `sse` <br>&nbsp;&nbsp;&nbsp;&nbsp;• `streamable-http`                                                                                                                                                                                                                                                 |
| `--port`                    |    No    |  int    |   `8000`     | Specifies the port number MCP Server listens on. Make sure the port is not occupied.                                                                                                                                                                                                                                                                                                                                                  |
| `--host`                    |    No    | string  | `127.0.0.1`  | Specifies the host address MCP Server listens on. `0.0.0.0` means listening on all network interfaces.                                                                                                                                                                                                                                                                                                                                |
| `--services`                |    No    | string  |    None      | Comma-separated services, e.g., `ecs,vpc`.<br>Supported services:<br>&nbsp;&nbsp;&nbsp;&nbsp;• `ecs`<br>&nbsp;&nbsp;&nbsp;&nbsp;• `oos`<br>&nbsp;&nbsp;&nbsp;&nbsp;• `rds`<br>&nbsp;&nbsp;&nbsp;&nbsp;• `vpc`<br>&nbsp;&nbsp;&nbsp;&nbsp;• `slb`<br>&nbsp;&nbsp;&nbsp;&nbsp;• `ess`<br>&nbsp;&nbsp;&nbsp;&nbsp;• `ros`<br>&nbsp;&nbsp;&nbsp;&nbsp;• `cbn`<br>&nbsp;&nbsp;&nbsp;&nbsp;• `dds`<br>&nbsp;&nbsp;&nbsp;&nbsp;• `r-kvstore`<br>&nbsp;&nbsp;&nbsp;&nbsp;• `bssopenapi` |
| `--headers-credential-only` |    No    |  bool   |   `false`    | Whether to use credentials only from HTTP headers. When enabled, credentials must be provided via request headers instead of environment variables.                                                                                                                                                                                                                                                                                   |
| `--env`                     |    No    | string  |  `domestic`  | Environment type for API endpoints.<br>Options:<br>&nbsp;&nbsp;&nbsp;&nbsp;• `domestic` - Use domestic (China) endpoints<br>&nbsp;&nbsp;&nbsp;&nbsp;• `international` - Use international (overseas) endpoints                                                                                                                                                                                                                        |
| `--code-deploy`             |    No    |  flag   |   `false`    | Enable code deploy mode. When enabled, only loads 6 specific tools:<br>&nbsp;&nbsp;&nbsp;&nbsp;• `OOS_CodeDeploy`<br>&nbsp;&nbsp;&nbsp;&nbsp;• `OOS_GetDeployStatus`<br>&nbsp;&nbsp;&nbsp;&nbsp;• `OOS_GetLastDeploymentInfo`<br>&nbsp;&nbsp;&nbsp;&nbsp;• `LOCAL_ListDirectory`<br>&nbsp;&nbsp;&nbsp;&nbsp;• `LOCAL_RunShellScript`<br>&nbsp;&nbsp;&nbsp;&nbsp;• `LOCAL_AnalyzeDeployStack`                                          |
| `--extra-config`            |    No    | string  |    None      | Add extra services and APIs to config (additive, does not replace existing config). Supports JSON format or Python dict format with single quotes.<br>Example: `"{'sls': ['GetProject', 'ListProject'], 'ecs': ['StartInstance']}"`                                                                                                                                                                                                  |
| `--visible-tools`           |    No    | string  |    None      | Comma-separated list of tool names to make visible (whitelist mode). Only these specified tools will be registered when this parameter is provided.<br>Example: `OOS_RunCommand,ECS_DescribeInstances,LOCAL_ListDirectory`                                                                                                                                                                                                            |

## Usage Examples

### Basic Usage
```bash
uv run src/alibaba_cloud_ops_mcp_server/server.py --transport sse --port 8080 --host 0.0.0.0 --services ecs,vpc
```

### Code Deploy Mode
```bash
uv run src/alibaba_cloud_ops_mcp_server/server.py --code-deploy
```

### Add Extra APIs via MCP Config
Using `--extra-config` to dynamically add services and APIs:

```bash
# JSON format (double quotes inside)
uv run src/alibaba_cloud_ops_mcp_server/server.py --extra-config '{"sls": ["GetProject", "ListProject"], "ecs": ["StartInstance"]}'

# Python dict format (single quotes inside)
uv run src/alibaba_cloud_ops_mcp_server/server.py --extra-config "{'sls': ['GetProject', 'ListProject'], 'ecs': ['StartInstance']}"
```

### Whitelist Mode
Using `--visible-tools` to only expose specific tools:

```bash
uv run src/alibaba_cloud_ops_mcp_server/server.py --visible-tools "OOS_RunCommand,ECS_DescribeInstances,LOCAL_ListDirectory"
```

### International Environment
```bash
uv run src/alibaba_cloud_ops_mcp_server/server.py --env international --services ecs,vpc
```

### MCP JSON Configuration Example

You can configure these parameters in your MCP client's JSON configuration file:

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
        "ALIBABA_CLOUD_ACCESS_KEY_ID": "your-access-key-id",
        "ALIBABA_CLOUD_ACCESS_KEY_SECRET": "your-access-key-secret",
        "ALIBABA_CLOUD_REGION": "cn-hangzhou"
      }
    }
  }
}
```

---

For more help, please refer to the main project documentation or contact the maintainer. 