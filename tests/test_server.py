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
        server.main.callback(transport='stdio', port=12345, host='127.0.0.1', services='ecs')
        mock_FastMCP.assert_called_once_with(
            name='alibaba-cloud-ops-mcp-server',
            port=12345, host='127.0.0.1')
        assert mcp.add_tool.call_count == 7  # common_api_tools 4 + oss/oos/cms 各1
        mock_create_api_tools.assert_called_once()
        mcp.run.assert_called_once_with(transport='stdio')

def test_run_as_main(monkeypatch):
    import runpy, sys
    from alibaba_cloud_ops_mcp_server import server
    monkeypatch.setattr(server, 'main', lambda *a, **kw: None)
    monkeypatch.setattr(sys, 'argv', ['server.py'])
    import mcp.server.fastmcp
    monkeypatch.setattr(mcp.server.fastmcp.FastMCP, 'run', lambda self, **kwargs: None)
    import pytest
    with pytest.raises(SystemExit) as e:
        runpy.run_path('src/alibaba_cloud_ops_mcp_server/server.py', run_name='__main__')
    assert e.value.code == 0 