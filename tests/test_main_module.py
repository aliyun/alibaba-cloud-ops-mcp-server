import runpy
from unittest.mock import patch


def test_main_module_invokes_server_main():
    """以 __main__ 身份执行 __main__.py，验证入口点会调用 server.main"""
    with patch('alibaba_cloud_ops_mcp_server.server.main') as mock_main:
        runpy.run_module('alibaba_cloud_ops_mcp_server.__main__', run_name='__main__')
        mock_main.assert_called_once_with()
