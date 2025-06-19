# MCP Startup Parameters Guide

This document provides a detailed introduction to the available parameters for starting the Alibaba Cloud MCP Server, helping users configure the server according to their needs.

## Parameter Table

|   Parameter    | Required |  Type  |  Default   | Description                                                                                                                                                                                                                                                                                                                                                                                                                           |
|:--------------:|:--------:|:------:|:----------:|:--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `--transport`  |    No    | string |  `stdio`   | Transport protocol for MCP Server communication.<br>Options:<br>&nbsp;&nbsp;&nbsp;&nbsp;• `stdio` <br>&nbsp;&nbsp;&nbsp;&nbsp;• `sse` <br>&nbsp;&nbsp;&nbsp;&nbsp;• `streamable-http`                                                                                                                                                                                                                                                 |
| `--port`       |    No    |  int   |  `8000`    | Specifies the port number MCP Server listens on. Make sure the port is not occupied.                                                                                                                                                                                                                                                                                                                                                  |
| `--host`       |    No    | string | `127.0.0.1`| Specifies the host address MCP Server listens on. `0.0.0.0` means listening on all network interfaces.                                                                                                                                                                                                                                                                                                                                |
| `--services`   |    No    | string |   None     | Comma-separated services, e.g., `ecs,vpc`.<br>Supported services:<br>&nbsp;&nbsp;&nbsp;&nbsp;• `ecs`<br>&nbsp;&nbsp;&nbsp;&nbsp;• `oos`<br>&nbsp;&nbsp;&nbsp;&nbsp;• `rds`<br>&nbsp;&nbsp;&nbsp;&nbsp;• `vpc`<br>&nbsp;&nbsp;&nbsp;&nbsp;• `slb`<br>&nbsp;&nbsp;&nbsp;&nbsp;• `ess`<br>&nbsp;&nbsp;&nbsp;&nbsp;• `ros`<br>&nbsp;&nbsp;&nbsp;&nbsp;• `cbn`<br>&nbsp;&nbsp;&nbsp;&nbsp;• `dds`<br>&nbsp;&nbsp;&nbsp;&nbsp;• `r-kvstore` |

## Usage Example

```bash
uv run src/alibaba_cloud_ops_mcp_server/server.py --transport sse --port 8080 --host 0.0.0.0 --services ecs,vpc
```

---

For more help, please refer to the main project documentation or contact the maintainer. 