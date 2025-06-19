# MCP Startup Parameters Guide

This document provides a detailed introduction to the available parameters for starting the Alibaba Cloud MCP Server, helping users configure the server according to their needs.

## Parameter List

### --transport
- **Type**: string
- **Options**: `stdio`, `sse`, `streamable-http`
- **Default**: `stdio`
- **Description**: Specifies the transport protocol for MCP Server communication.

### --port
- **Type**: int
- **Default**: `8000`
- **Description**: Specifies the port number MCP Server listens on.

### --host
- **Type**: string
- **Default**: `127.0.0.1`
- **Description**: Specifies the host address MCP Server listens on.

### --services
- **Type**: string
- **Default**: `None`
- **Description**: Comma-separated list of services to enable. For example: `ecs,vpc,rds`. If not specified, all supported services are enabled.

## Usage Example

```bash
python -m alibaba_cloud_ops_mcp_server.server --transport stdio --port 12345 --host 0.0.0.0 --services ecs,vpc
```

## Parameter Details

- `--transport`:
  - `stdio`: Standard input/output mode, suitable for local development and debugging.
  - `sse`: Server-Sent Events, suitable for web push scenarios.
  - `streamable-http`: Streamable HTTP, suitable for scenarios requiring streaming responses.

- `--port`:
  - Specifies the port the service listens on. Make sure the port is not occupied.

- `--host`:
  - Specifies the host address. `0.0.0.0` means listening on all network interfaces.

- `--services`:
  - Only loads the specified services, improving startup speed and security.
  - Supported services include: ecs, oos, rds, vpc, slb, ess, ros, cbn, dds, r-kvstore.

---

For more help, please refer to the main project documentation or contact the maintainer. 