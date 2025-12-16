import pytest
from unittest.mock import patch, AsyncMock
import alibaba_cloud_ops_mcp_server

def test_main_calls_server_main():
    with patch('alibaba_cloud_ops_mcp_server.server.main', new_callable=AsyncMock) as mock_main:
        alibaba_cloud_ops_mcp_server.main()
        mock_main.assert_awaited_once()
