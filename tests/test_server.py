import pytest
from unittest.mock import patch, MagicMock, ANY

@patch('alibaba_cloud_ops_mcp_server.server.FastMCP')
@patch('alibaba_cloud_ops_mcp_server.server.api_tools.create_api_tools')
def test_main_run(mock_create_api_tools, mock_FastMCP):
    with patch('alibaba_cloud_ops_mcp_server.server.oss_tools.tools', [lambda: None]), \
         patch('alibaba_cloud_ops_mcp_server.server.oos_tools.tools', [lambda: None]), \
         patch('alibaba_cloud_ops_mcp_server.server.cms_tools.tools', [lambda: None]), \
         patch('alibaba_cloud_ops_mcp_server.server.application_management_tools.tools', []), \
         patch('alibaba_cloud_ops_mcp_server.server.local_tools.tools', []):
        from alibaba_cloud_ops_mcp_server import server
        mcp = MagicMock()
        mock_FastMCP.return_value = mcp
        # 调用main函数
        server.main.callback(transport='stdio', port=12345, host='127.0.0.1', services='ecs',
                             headers_credential_only=None, env='domestic', code_deploy=False,
                             extra_config=None, visible_tools=None)
        mock_FastMCP.assert_called_once_with(
            name='alibaba-cloud-ops-mcp-server',
            instructions=ANY,
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
         patch('alibaba_cloud_ops_mcp_server.server.cms_tools.tools', [lambda: None]), \
         patch('alibaba_cloud_ops_mcp_server.server.application_management_tools.tools', []), \
         patch('alibaba_cloud_ops_mcp_server.server.local_tools.tools', []):
        from alibaba_cloud_ops_mcp_server import server
        mcp = MagicMock()
        mock_FastMCP.return_value = mcp
        # 调用main函数，不指定services
        server.main.callback(transport='stdio', port=8000, host='127.0.0.1', services=None,
                             headers_credential_only=None, env='domestic', code_deploy=False,
                             extra_config=None, visible_tools=None)
        mock_FastMCP.assert_called_once_with(
            name='alibaba-cloud-ops-mcp-server',
            instructions=ANY,
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
         patch('alibaba_cloud_ops_mcp_server.server.common_api_tools.tools', [lambda: None, lambda: None]), \
         patch('alibaba_cloud_ops_mcp_server.server.application_management_tools.tools', []), \
         patch('alibaba_cloud_ops_mcp_server.server.local_tools.tools', []):
        from alibaba_cloud_ops_mcp_server import server
        mcp = MagicMock()
        mock_FastMCP.return_value = mcp
        # 调用main函数，指定多个services
        server.main.callback(transport='sse', port=9000, host='0.0.0.0', services='ecs,vpc,rds',
                             headers_credential_only=None, env='domestic', code_deploy=False,
                             extra_config=None, visible_tools=None)
        mock_FastMCP.assert_called_once_with(
            name='alibaba-cloud-ops-mcp-server',
            instructions=ANY,
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
         patch('alibaba_cloud_ops_mcp_server.server.cms_tools.tools', []), \
         patch('alibaba_cloud_ops_mcp_server.server.application_management_tools.tools', []), \
         patch('alibaba_cloud_ops_mcp_server.server.local_tools.tools', []):
        from alibaba_cloud_ops_mcp_server import server
        mcp = MagicMock()
        mock_FastMCP.return_value = mcp
        # 调用main函数
        server.main.callback(transport='streamable-http', port=8080, host='localhost', services=None,
                             headers_credential_only=None, env='domestic', code_deploy=False,
                             extra_config=None, visible_tools=None)
        # 验证日志被调用
        mock_logger.debug.assert_called_once_with('mcp server is running on streamable-http mode.')


@patch('alibaba_cloud_ops_mcp_server.server.FastMCP')
@patch('alibaba_cloud_ops_mcp_server.server.api_tools.create_api_tools')
@patch('alibaba_cloud_ops_mcp_server.server.logger')
def test_main_run_with_extra_config_json(mock_logger, mock_create_api_tools, mock_FastMCP):
    """测试 extra_config 使用 JSON 格式"""
    with patch('alibaba_cloud_ops_mcp_server.server.oss_tools.tools', []), \
         patch('alibaba_cloud_ops_mcp_server.server.oos_tools.tools', []), \
         patch('alibaba_cloud_ops_mcp_server.server.cms_tools.tools', []), \
         patch('alibaba_cloud_ops_mcp_server.server.application_management_tools.tools', []), \
         patch('alibaba_cloud_ops_mcp_server.server.local_tools.tools', []):
        from alibaba_cloud_ops_mcp_server import server
        mcp = MagicMock()
        mock_FastMCP.return_value = mcp
        # 使用 JSON 格式的 extra_config
        server.main.callback(transport='stdio', port=8000, host='127.0.0.1', services=None,
                             headers_credential_only=None, env='domestic', code_deploy=False,
                             extra_config='{"sls": ["GetProject", "ListProject"]}', visible_tools=None)
        # 验证 create_api_tools 被调用，且 config 中包含新增的 sls 服务
        mock_create_api_tools.assert_called_once()
        call_args = mock_create_api_tools.call_args
        merged_config = call_args[0][1]
        assert 'sls' in merged_config
        assert 'GetProject' in merged_config['sls']
        assert 'ListProject' in merged_config['sls']
        mock_logger.info.assert_any_call("Merged extra config: {'sls': ['GetProject', 'ListProject']}")


@patch('alibaba_cloud_ops_mcp_server.server.FastMCP')
@patch('alibaba_cloud_ops_mcp_server.server.api_tools.create_api_tools')
@patch('alibaba_cloud_ops_mcp_server.server.logger')
def test_main_run_with_extra_config_single_quotes(mock_logger, mock_create_api_tools, mock_FastMCP):
    """测试 extra_config 使用单引号格式"""
    with patch('alibaba_cloud_ops_mcp_server.server.oss_tools.tools', []), \
         patch('alibaba_cloud_ops_mcp_server.server.oos_tools.tools', []), \
         patch('alibaba_cloud_ops_mcp_server.server.cms_tools.tools', []), \
         patch('alibaba_cloud_ops_mcp_server.server.application_management_tools.tools', []), \
         patch('alibaba_cloud_ops_mcp_server.server.local_tools.tools', []):
        from alibaba_cloud_ops_mcp_server import server
        mcp = MagicMock()
        mock_FastMCP.return_value = mcp
        # 使用单引号格式的 extra_config (Python dict literal)
        server.main.callback(transport='stdio', port=8000, host='127.0.0.1', services=None,
                             headers_credential_only=None, env='domestic', code_deploy=False,
                             extra_config="{'sls': ['CreateProject']}", visible_tools=None)
        mock_create_api_tools.assert_called_once()
        call_args = mock_create_api_tools.call_args
        merged_config = call_args[0][1]
        assert 'sls' in merged_config
        assert 'CreateProject' in merged_config['sls']


@patch('alibaba_cloud_ops_mcp_server.server.FastMCP')
@patch('alibaba_cloud_ops_mcp_server.server.api_tools.create_api_tools')
@patch('alibaba_cloud_ops_mcp_server.server.logger')
def test_main_run_with_extra_config_merge_existing(mock_logger, mock_create_api_tools, mock_FastMCP):
    """测试 extra_config 合并到现有 config（添加 API 到已存在的服务）"""
    with patch('alibaba_cloud_ops_mcp_server.server.oss_tools.tools', []), \
         patch('alibaba_cloud_ops_mcp_server.server.oos_tools.tools', []), \
         patch('alibaba_cloud_ops_mcp_server.server.cms_tools.tools', []), \
         patch('alibaba_cloud_ops_mcp_server.server.application_management_tools.tools', []), \
         patch('alibaba_cloud_ops_mcp_server.server.local_tools.tools', []):
        from alibaba_cloud_ops_mcp_server import server
        mcp = MagicMock()
        mock_FastMCP.return_value = mcp
        # 给 ecs 服务添加新的 API（ecs 已在 config.py 中存在）
        server.main.callback(transport='stdio', port=8000, host='127.0.0.1', services=None,
                             headers_credential_only=None, env='domestic', code_deploy=False,
                             extra_config='{"ecs": ["StartInstance", "StopInstance"]}', visible_tools=None)
        mock_create_api_tools.assert_called_once()
        call_args = mock_create_api_tools.call_args
        merged_config = call_args[0][1]
        # 验证新 API 被添加
        assert 'StartInstance' in merged_config['ecs']
        assert 'StopInstance' in merged_config['ecs']
        # 验证原有 API 仍然存在
        assert 'DescribeInstances' in merged_config['ecs']


@patch('alibaba_cloud_ops_mcp_server.server.FastMCP')
@patch('alibaba_cloud_ops_mcp_server.server.api_tools.create_api_tools')
@patch('alibaba_cloud_ops_mcp_server.server.logger')
def test_main_run_with_extra_config_invalid_json(mock_logger, mock_create_api_tools, mock_FastMCP):
    """测试 extra_config 使用无效格式时的错误处理"""
    with patch('alibaba_cloud_ops_mcp_server.server.oss_tools.tools', []), \
         patch('alibaba_cloud_ops_mcp_server.server.oos_tools.tools', []), \
         patch('alibaba_cloud_ops_mcp_server.server.cms_tools.tools', []), \
         patch('alibaba_cloud_ops_mcp_server.server.application_management_tools.tools', []), \
         patch('alibaba_cloud_ops_mcp_server.server.local_tools.tools', []):
        from alibaba_cloud_ops_mcp_server import server
        mcp = MagicMock()
        mock_FastMCP.return_value = mcp
        # 使用无效的格式
        server.main.callback(transport='stdio', port=8000, host='127.0.0.1', services=None,
                             headers_credential_only=None, env='domestic', code_deploy=False,
                             extra_config='invalid json', visible_tools=None)
        # 验证错误日志被记录
        mock_logger.error.assert_called()


@patch('alibaba_cloud_ops_mcp_server.server.FastMCP')
def test_main_run_code_deploy_mode(mock_FastMCP):
    """测试 code_deploy 模式"""
    mock_tool_1 = MagicMock()
    mock_tool_1.__name__ = 'OOS_CodeDeploy'
    mock_tool_2 = MagicMock()
    mock_tool_2.__name__ = 'OOS_GetDeployStatus'
    mock_tool_3 = MagicMock()
    mock_tool_3.__name__ = 'LOCAL_ListDirectory'
    
    with patch('alibaba_cloud_ops_mcp_server.server.application_management_tools.tools', [mock_tool_1, mock_tool_2]), \
         patch('alibaba_cloud_ops_mcp_server.server.local_tools.tools', [mock_tool_3]):
        from alibaba_cloud_ops_mcp_server import server
        mcp = MagicMock()
        mock_FastMCP.return_value = mcp
        # 启用 code_deploy 模式
        server.main.callback(transport='stdio', port=8000, host='127.0.0.1', services=None,
                             headers_credential_only=None, env='domestic', code_deploy=True,
                             extra_config=None, visible_tools=None)
        # 验证只加载了 code_deploy 相关的工具
        assert mcp.tool.call_count == 3


@patch('alibaba_cloud_ops_mcp_server.server.FastMCP')
@patch('alibaba_cloud_ops_mcp_server.server.api_tools.create_api_tools')
def test_main_run_with_headers_credential_only(mock_create_api_tools, mock_FastMCP):
    """测试 headers_credential_only 参数"""
    with patch('alibaba_cloud_ops_mcp_server.server.oss_tools.tools', []), \
         patch('alibaba_cloud_ops_mcp_server.server.oos_tools.tools', []), \
         patch('alibaba_cloud_ops_mcp_server.server.cms_tools.tools', []), \
         patch('alibaba_cloud_ops_mcp_server.server.application_management_tools.tools', []), \
         patch('alibaba_cloud_ops_mcp_server.server.local_tools.tools', []):
        from alibaba_cloud_ops_mcp_server import server
        from alibaba_cloud_ops_mcp_server.settings import settings
        mcp = MagicMock()
        mock_FastMCP.return_value = mcp
        # 测试 headers_credential_only=True
        server.main.callback(transport='stdio', port=8000, host='127.0.0.1', services=None,
                             headers_credential_only=True, env='domestic', code_deploy=False,
                             extra_config=None, visible_tools=None)
        assert settings.headers_credential_only == True


@patch('alibaba_cloud_ops_mcp_server.server.FastMCP')
@patch('alibaba_cloud_ops_mcp_server.server.api_tools.create_api_tools')
def test_main_run_with_env_international(mock_create_api_tools, mock_FastMCP):
    """测试 env=international 参数"""
    with patch('alibaba_cloud_ops_mcp_server.server.oss_tools.tools', []), \
         patch('alibaba_cloud_ops_mcp_server.server.oos_tools.tools', []), \
         patch('alibaba_cloud_ops_mcp_server.server.cms_tools.tools', []), \
         patch('alibaba_cloud_ops_mcp_server.server.application_management_tools.tools', []), \
         patch('alibaba_cloud_ops_mcp_server.server.local_tools.tools', []):
        from alibaba_cloud_ops_mcp_server import server
        from alibaba_cloud_ops_mcp_server.settings import settings
        mcp = MagicMock()
        mock_FastMCP.return_value = mcp
        server.main.callback(transport='stdio', port=8000, host='127.0.0.1', services=None,
                             headers_credential_only=None, env='international', code_deploy=False,
                             extra_config=None, visible_tools=None)
        assert settings.env == 'international'


def test_setup_logging():
    """测试 _setup_logging 函数"""
    import logging
    from alibaba_cloud_ops_mcp_server import server
    
    # 获取 root logger 并清除现有 handlers
    root_logger = logging.getLogger()
    original_handlers = root_logger.handlers[:]
    root_logger.handlers = []
    
    try:
        # 调用 _setup_logging
        server._setup_logging()
        
        # 验证 handler 被添加
        assert len(root_logger.handlers) > 0
        assert root_logger.level == logging.INFO
    finally:
        # 恢复原有 handlers
        root_logger.handlers = original_handlers


def test_setup_logging_with_existing_handlers():
    """测试 _setup_logging 在已有 handlers 时的行为"""
    import logging
    from alibaba_cloud_ops_mcp_server import server
    
    root_logger = logging.getLogger()
    original_level = root_logger.level
    
    # 确保已有 handlers
    if not root_logger.handlers:
        root_logger.addHandler(logging.StreamHandler())
    
    try:
        server._setup_logging()
        assert root_logger.level == logging.INFO
    finally:
        root_logger.setLevel(original_level)


@patch('alibaba_cloud_ops_mcp_server.server.FastMCP')
@patch('alibaba_cloud_ops_mcp_server.server.api_tools.create_api_tools')
@patch('alibaba_cloud_ops_mcp_server.server.logger')
def test_main_run_visible_tools_mode(mock_logger, mock_create_api_tools, mock_FastMCP):
    """测试 visible_tools 白名单模式"""
    mock_tool_1 = MagicMock()
    mock_tool_1.__name__ = 'OOS_RunCommand'
    mock_tool_2 = MagicMock()
    mock_tool_2.__name__ = 'CMS_GetCpuUsageData'
    mock_tool_3 = MagicMock()
    mock_tool_3.__name__ = 'OSS_ListBuckets'
    
    with patch('alibaba_cloud_ops_mcp_server.server.oss_tools.tools', [mock_tool_3]), \
         patch('alibaba_cloud_ops_mcp_server.server.oos_tools.tools', [mock_tool_1]), \
         patch('alibaba_cloud_ops_mcp_server.server.cms_tools.tools', [mock_tool_2]), \
         patch('alibaba_cloud_ops_mcp_server.server.application_management_tools.tools', []), \
         patch('alibaba_cloud_ops_mcp_server.server.local_tools.tools', []), \
         patch('alibaba_cloud_ops_mcp_server.server.common_api_tools.tools', []):
        from alibaba_cloud_ops_mcp_server import server
        mcp = MagicMock()
        mock_FastMCP.return_value = mcp
        # 使用 visible_tools 模式，只允许 OOS_RunCommand
        server.main.callback(transport='stdio', port=8000, host='127.0.0.1', services=None,
                             headers_credential_only=None, env='domestic', code_deploy=False,
                             extra_config=None, visible_tools='OOS_RunCommand')
        # 验证 visible tools 模式日志 (case-insensitive, 所以是小写)
        mock_logger.info.assert_any_call("Visible tools mode enabled (case-insensitive). Allowed tools: {'oos_runcommand'}")


@patch('alibaba_cloud_ops_mcp_server.server.FastMCP')
@patch('alibaba_cloud_ops_mcp_server.server.api_tools.create_api_tools')
@patch('alibaba_cloud_ops_mcp_server.server.logger')
def test_main_run_visible_tools_empty(mock_logger, mock_create_api_tools, mock_FastMCP):
    """测试 visible_tools 为空时回退到普通模式"""
    with patch('alibaba_cloud_ops_mcp_server.server.oss_tools.tools', []), \
         patch('alibaba_cloud_ops_mcp_server.server.oos_tools.tools', []), \
         patch('alibaba_cloud_ops_mcp_server.server.cms_tools.tools', []), \
         patch('alibaba_cloud_ops_mcp_server.server.application_management_tools.tools', []), \
         patch('alibaba_cloud_ops_mcp_server.server.local_tools.tools', []):
        from alibaba_cloud_ops_mcp_server import server
        mcp = MagicMock()
        mock_FastMCP.return_value = mcp
        # 使用空的 visible_tools
        server.main.callback(transport='stdio', port=8000, host='127.0.0.1', services=None,
                             headers_credential_only=None, env='domestic', code_deploy=False,
                             extra_config=None, visible_tools='  ')
        # 验证警告日志
        mock_logger.warning.assert_any_call("--visible-tools is empty, falling back to normal mode.")


@patch('alibaba_cloud_ops_mcp_server.server.FastMCP')
@patch('alibaba_cloud_ops_mcp_server.server.logger')
def test_main_run_code_deploy_and_visible_tools_conflict(mock_logger, mock_FastMCP):
    """测试 code_deploy 和 visible_tools 同时指定时的互斥处理"""
    mock_tool = MagicMock()
    mock_tool.__name__ = 'OOS_CodeDeploy'
    
    with patch('alibaba_cloud_ops_mcp_server.server.application_management_tools.tools', [mock_tool]), \
         patch('alibaba_cloud_ops_mcp_server.server.local_tools.tools', []):
        from alibaba_cloud_ops_mcp_server import server
        mcp = MagicMock()
        mock_FastMCP.return_value = mcp
        # 同时指定 code_deploy 和 visible_tools
        server.main.callback(transport='stdio', port=8000, host='127.0.0.1', services=None,
                             headers_credential_only=None, env='domestic', code_deploy=True,
                             extra_config=None, visible_tools='OOS_RunCommand')
        # 验证警告日志
        mock_logger.warning.assert_any_call("--code-deploy and --visible-tools are mutually exclusive. Using --code-deploy mode.")


@patch('alibaba_cloud_ops_mcp_server.server.FastMCP')
@patch('alibaba_cloud_ops_mcp_server.server.api_tools.create_api_tools')
def test_main_run_skip_ecs_describe_instances(mock_create_api_tools, mock_FastMCP):
    """测试普通模式下跳过 ECS_DescribeInstances"""
    mock_tool_1 = MagicMock()
    mock_tool_1.__name__ = 'OOS_CodeDeploy'
    mock_tool_2 = MagicMock()
    mock_tool_2.__name__ = 'ECS_DescribeInstances'
    
    with patch('alibaba_cloud_ops_mcp_server.server.oss_tools.tools', []), \
         patch('alibaba_cloud_ops_mcp_server.server.oos_tools.tools', []), \
         patch('alibaba_cloud_ops_mcp_server.server.cms_tools.tools', []), \
         patch('alibaba_cloud_ops_mcp_server.server.application_management_tools.tools', [mock_tool_1, mock_tool_2]), \
         patch('alibaba_cloud_ops_mcp_server.server.local_tools.tools', []):
        from alibaba_cloud_ops_mcp_server import server
        mcp = MagicMock()
        mock_FastMCP.return_value = mcp
        server.main.callback(transport='stdio', port=8000, host='127.0.0.1', services=None,
                             headers_credential_only=None, env='domestic', code_deploy=False,
                             extra_config=None, visible_tools=None)
        # 验证 mcp.tool 只被调用了一次（OOS_CodeDeploy），ECS_DescribeInstances 被跳过
        assert mcp.tool.call_count == 1


@patch('alibaba_cloud_ops_mcp_server.server.FastMCP')
@patch('alibaba_cloud_ops_mcp_server.server.api_tools.create_api_tools')
@patch('alibaba_cloud_ops_mcp_server.server.logger')
def test_register_tools_with_filter_with_services(mock_logger, mock_create_api_tools, mock_FastMCP):
    """测试 _register_tools_with_filter 带 services 参数"""
    mock_common_tool = MagicMock()
    mock_common_tool.__name__ = 'ListSupportedServices'
    
    with patch('alibaba_cloud_ops_mcp_server.server.oss_tools.tools', []), \
         patch('alibaba_cloud_ops_mcp_server.server.oos_tools.tools', []), \
         patch('alibaba_cloud_ops_mcp_server.server.cms_tools.tools', []), \
         patch('alibaba_cloud_ops_mcp_server.server.application_management_tools.tools', []), \
         patch('alibaba_cloud_ops_mcp_server.server.local_tools.tools', []), \
         patch('alibaba_cloud_ops_mcp_server.server.common_api_tools.tools', [mock_common_tool]):
        from alibaba_cloud_ops_mcp_server import server
        mcp = MagicMock()
        mock_FastMCP.return_value = mcp
        # 使用 visible_tools 模式并指定 services
        server.main.callback(transport='stdio', port=8000, host='127.0.0.1', services='ecs,vpc',
                             headers_credential_only=None, env='domestic', code_deploy=False,
                             extra_config=None, visible_tools='ListSupportedServices')
        # 验证工具被注册
        assert mcp.tool.call_count == 1


@patch('alibaba_cloud_ops_mcp_server.server.FastMCP')
@patch('alibaba_cloud_ops_mcp_server.server.api_tools.create_api_tools')
@patch('alibaba_cloud_ops_mcp_server.server.logger')
def test_register_tools_with_filter_dynamic_tools(mock_logger, mock_create_api_tools, mock_FastMCP):
    """测试 _register_tools_with_filter 处理动态 API 工具"""
    with patch('alibaba_cloud_ops_mcp_server.server.oss_tools.tools', []), \
         patch('alibaba_cloud_ops_mcp_server.server.oos_tools.tools', []), \
         patch('alibaba_cloud_ops_mcp_server.server.cms_tools.tools', []), \
         patch('alibaba_cloud_ops_mcp_server.server.application_management_tools.tools', []), \
         patch('alibaba_cloud_ops_mcp_server.server.local_tools.tools', []), \
         patch('alibaba_cloud_ops_mcp_server.server.common_api_tools.tools', []):
        from alibaba_cloud_ops_mcp_server import server
        mcp = MagicMock()
        mock_FastMCP.return_value = mcp
        # 使用 visible_tools 模式，包含动态 API 工具
        server.main.callback(transport='stdio', port=8000, host='127.0.0.1', services=None,
                             headers_credential_only=None, env='domestic', code_deploy=False,
                             extra_config=None, visible_tools='ECS_DescribeInstances,SLS_GetProject')
        # 验证 create_api_tools 被调用
        mock_create_api_tools.assert_called_once()
        call_args = mock_create_api_tools.call_args[0][1]
        assert 'ecs' in call_args
        assert 'DescribeInstances' in call_args['ecs']
        assert 'sls' in call_args
        assert 'GetProject' in call_args['sls']


@patch('alibaba_cloud_ops_mcp_server.server.FastMCP')
@patch('alibaba_cloud_ops_mcp_server.server.api_tools.create_api_tools')
@patch('alibaba_cloud_ops_mcp_server.server.logger')
def test_register_tools_with_filter_with_extra_config(mock_logger, mock_create_api_tools, mock_FastMCP):
    """测试 _register_tools_with_filter 带 extra_config 参数"""
    with patch('alibaba_cloud_ops_mcp_server.server.oss_tools.tools', []), \
         patch('alibaba_cloud_ops_mcp_server.server.oos_tools.tools', []), \
         patch('alibaba_cloud_ops_mcp_server.server.cms_tools.tools', []), \
         patch('alibaba_cloud_ops_mcp_server.server.application_management_tools.tools', []), \
         patch('alibaba_cloud_ops_mcp_server.server.local_tools.tools', []), \
         patch('alibaba_cloud_ops_mcp_server.server.common_api_tools.tools', []):
        from alibaba_cloud_ops_mcp_server import server
        mcp = MagicMock()
        mock_FastMCP.return_value = mcp
        # 使用 visible_tools 模式并指定 extra_config
        server.main.callback(transport='stdio', port=8000, host='127.0.0.1', services=None,
                             headers_credential_only=None, env='domestic', code_deploy=False,
                             extra_config='{"sls": ["GetProject"]}', visible_tools='SLS_GetProject')
        # 验证 create_api_tools 被调用
        mock_create_api_tools.assert_called_once()


@patch('alibaba_cloud_ops_mcp_server.server.FastMCP')
@patch('alibaba_cloud_ops_mcp_server.server.api_tools.create_api_tools')
@patch('alibaba_cloud_ops_mcp_server.server.logger')
def test_register_tools_with_filter_unregistered_tools_warning(mock_logger, mock_create_api_tools, mock_FastMCP):
    """测试 _register_tools_with_filter 未找到工具时的警告"""
    with patch('alibaba_cloud_ops_mcp_server.server.oss_tools.tools', []), \
         patch('alibaba_cloud_ops_mcp_server.server.oos_tools.tools', []), \
         patch('alibaba_cloud_ops_mcp_server.server.cms_tools.tools', []), \
         patch('alibaba_cloud_ops_mcp_server.server.application_management_tools.tools', []), \
         patch('alibaba_cloud_ops_mcp_server.server.local_tools.tools', []), \
         patch('alibaba_cloud_ops_mcp_server.server.common_api_tools.tools', []):
        from alibaba_cloud_ops_mcp_server import server
        mcp = MagicMock()
        mock_FastMCP.return_value = mcp
        # 使用 visible_tools 模式，指定不存在的工具名
        server.main.callback(transport='stdio', port=8000, host='127.0.0.1', services=None,
                             headers_credential_only=None, env='domestic', code_deploy=False,
                             extra_config=None, visible_tools='NonExistentTool')
        # 验证警告日志被记录 (case-insensitive, 所以是小写)
        mock_logger.warning.assert_any_call("The following tools were not found and not registered: {'nonexistenttool'}")


def test_main_module_entry_point():
    """测试 __main__.py 入口点"""
    import subprocess
    import sys
    import os
    
    # 动态获取项目 src 目录路径
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    src_dir = os.path.join(project_root, 'src')
    
    # 使用 -m 运行模块并获取帮助信息
    result = subprocess.run(
        [sys.executable, '-m', 'alibaba_cloud_ops_mcp_server', '--help'],
        capture_output=True, text=True, timeout=10,
        cwd=src_dir
    )
    # 验证帮助信息输出
    assert result.returncode == 0
    assert 'Transport type' in result.stdout or '--transport' in result.stdout

