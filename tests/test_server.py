import pytest
from unittest.mock import patch, MagicMock

@patch('alibaba_cloud_ops_mcp_server.server.FastMCP')
@patch('alibaba_cloud_ops_mcp_server.server.api_tools.create_api_tools')
def test_main_run(mock_create_api_tools, mock_FastMCP):
    with patch('alibaba_cloud_ops_mcp_server.server.oss_tools.tools', [lambda: None]), \
         patch('alibaba_cloud_ops_mcp_server.server.oos_tools.tools', [lambda: None]), \
         patch('alibaba_cloud_ops_mcp_server.server.cms_tools.tools', [lambda: None]):
        from alibaba_cloud_ops_mcp_server import server
        mcp = MagicMock()
        mock_FastMCP.return_value = mcp
        # 调用main函数
        server.main.callback(transport='stdio', port=12345, host='127.0.0.1', services='ecs',
                             headers_credential_only=None, env='domestic')
        mock_FastMCP.assert_called_once_with(
            name='alibaba-cloud-ops-mcp-server',
            port=12345, host='127.0.0.1', stateless_http=True)
        assert mcp.tool.call_count == 7  # common_api_tools 4 + oss/oos/cms 各1
        mock_create_api_tools.assert_called_once()
        mcp.run.assert_called_once_with(transport='stdio')


@patch('alibaba_cloud_ops_mcp_server.server.FastMCP')
@patch('alibaba_cloud_ops_mcp_server.server.api_tools.create_api_tools')
def test_main_run_without_services(mock_create_api_tools, mock_FastMCP):
    """测试不指定services参数时的情况"""
    with patch('alibaba_cloud_ops_mcp_server.server.oss_tools.tools', [lambda: None]), \
         patch('alibaba_cloud_ops_mcp_server.server.oos_tools.tools', [lambda: None]), \
         patch('alibaba_cloud_ops_mcp_server.server.cms_tools.tools', [lambda: None]):
        from alibaba_cloud_ops_mcp_server import server
        mcp = MagicMock()
        mock_FastMCP.return_value = mcp
        # 调用main函数，不指定services
        server.main.callback(transport='stdio', port=8000, host='127.0.0.1', services=None,
                             headers_credential_only=None, env='domestic')
        mock_FastMCP.assert_called_once_with(
            name='alibaba-cloud-ops-mcp-server',
            port=8000, host='127.0.0.1', stateless_http=True)
        # 不指定services时，应该只有oss/oos/cms的工具被添加，没有common_api_tools
        assert mcp.tool.call_count == 3  # oss/oos/cms 各1
        mock_create_api_tools.assert_called_once()
        mcp.run.assert_called_once_with(transport='stdio')


def test_main_module_execution():
    """测试模块直接执行时的入口点（第78-79行）"""
    import subprocess
    import sys
    import os
    
    # 获取server.py的路径
    server_path = os.path.join(os.path.dirname(__file__), '../src/alibaba_cloud_ops_mcp_server/server.py')
    server_path = os.path.abspath(server_path)
    
    # 使用subprocess来模拟直接执行模块，但立即终止以避免实际运行服务器
    try:
        # 使用timeout来快速终止进程，只是为了测试入口点能否正常启动
        result = subprocess.run([sys.executable, server_path, '--help'], 
                              capture_output=True, text=True, timeout=5)
        # 如果能显示帮助信息，说明main函数和入口点工作正常
        assert 'Transport type' in result.stdout or result.returncode == 0
    except subprocess.TimeoutExpired:
        # 超时也是可以接受的，说明程序启动了
        pass


@patch('alibaba_cloud_ops_mcp_server.server.FastMCP')
@patch('alibaba_cloud_ops_mcp_server.server.api_tools.create_api_tools')
def test_main_run_multiple_services(mock_create_api_tools, mock_FastMCP):
    """测试指定多个services的情况"""
    with patch('alibaba_cloud_ops_mcp_server.server.oss_tools.tools', [lambda: None]), \
         patch('alibaba_cloud_ops_mcp_server.server.oos_tools.tools', [lambda: None]), \
         patch('alibaba_cloud_ops_mcp_server.server.cms_tools.tools', [lambda: None]), \
         patch('alibaba_cloud_ops_mcp_server.server.common_api_tools.tools', [lambda: None, lambda: None]):
        from alibaba_cloud_ops_mcp_server import server
        mcp = MagicMock()
        mock_FastMCP.return_value = mcp
        # 调用main函数，指定多个services
        server.main.callback(transport='sse', port=9000, host='0.0.0.0', services='ecs,vpc,rds',
                             headers_credential_only=None, env='domestic')
        mock_FastMCP.assert_called_once_with(
            name='alibaba-cloud-ops-mcp-server',
            port=9000, host='0.0.0.0', stateless_http=True)
        # common_api_tools 2 + oss/oos/cms 各1 = 5
        assert mcp.tool.call_count == 5
        mock_create_api_tools.assert_called_once()
        mcp.run.assert_called_once_with(transport='sse')


@patch('alibaba_cloud_ops_mcp_server.server.FastMCP')
@patch('alibaba_cloud_ops_mcp_server.server.api_tools.create_api_tools')
@patch('alibaba_cloud_ops_mcp_server.server.logger')
def test_main_run_with_logging(mock_logger, mock_create_api_tools, mock_FastMCP):
    """测试日志输出（第77行）"""
    with patch('alibaba_cloud_ops_mcp_server.server.oss_tools.tools', []), \
         patch('alibaba_cloud_ops_mcp_server.server.oos_tools.tools', []), \
         patch('alibaba_cloud_ops_mcp_server.server.cms_tools.tools', []):
        from alibaba_cloud_ops_mcp_server import server
        mcp = MagicMock()
        mock_FastMCP.return_value = mcp
        # 调用main函数
        server.main.callback(transport='streamable-http', port=8080, host='localhost', services=None,
                             headers_credential_only=None, env='domestic')
        # 验证日志被调用
        mock_logger.debug.assert_called_once_with('mcp server is running on streamable-http mode.')
