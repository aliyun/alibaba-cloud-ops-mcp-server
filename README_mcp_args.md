# MCP Startup Parameters Guide

This document provides a detailed introduction to the available parameters for starting the Alibaba Cloud MCP Server, helping users configure the server according to their needs.

## Parameter Table

| Parameter      | Required | Type   | Default     | Description |
|----------------|----------|--------|-------------|-------------|
| `--transport`  | No       | string | `stdio`     | Specifies the transport protocol for MCP Server communication.<br>Options:<br>• `stdio` (Standard input/output mode, suitable for local development and debugging)<br>• `sse` (Server-Sent Events, suitable for web push scenarios)<br>• `streamable-http` (Streamable HTTP, suitable for scenarios requiring streaming responses) |
| `--port`       | No       | int    | `8000`      | Specifies the port number MCP Server listens on. Make sure the port is not occupied. |
| `--host`       | No       | string | `127.0.0.1` | Specifies the host address MCP Server listens on. `0.0.0.0` means listening on all network interfaces. |
| `--services`   | No       | string | None        | Comma-separated list of services to enable, e.g., `ecs,vpc,rds`. Only loads the specified services, improving startup speed and security. **Supported services:** `ecs`, `oos`, `rds`, `vpc`, `slb`, `ess`, `ros`, `cbn`, `dds`, `r-kvstore`. Enables all if not specified. |

## Usage Example

```bash
python -m alibaba_cloud_ops_mcp_server.server --transport stdio --port 12345 --host 0.0.0.0 --services ecs,vpc
```

---

For more help, please refer to the main project documentation or contact the maintainer. 