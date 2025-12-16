import pytest
from unittest.mock import patch, MagicMock
from alibaba_cloud_ops_mcp_server.tools import cms_tools
import json

def get_tool_func(name):
    return [f for f in cms_tools.tools if f.__name__ == name][0]

def fake_client(*args, **kwargs):
    class FakeResp:
        class Body:
            datapoints = [{"value": 1}]
        body = Body()
        def __init__(self):
            pass
    class FakeClient:
        def describe_metric_last(self, req):
            return FakeResp()
    return FakeClient()

@patch('alibaba_cloud_ops_mcp_server.tools.cms_tools.create_client', fake_client)
def test_CMS_GetCpuUsageData():
    func = get_tool_func("CMS_GetCpuUsageData")
    result = func(RegionId='cn-test', InstanceIds=['i-1'])
    assert isinstance(result, list)
    assert result[0]["value"] == 1

@patch('alibaba_cloud_ops_mcp_server.tools.cms_tools.create_client', fake_client)
def test_CMS_GetCpuLoadavgData():
    func = get_tool_func("CMS_GetCpuLoadavgData")
    result = func(RegionId='cn-test', InstanceIds=['i-1'])
    assert isinstance(result, list)

@patch('alibaba_cloud_ops_mcp_server.tools.cms_tools.create_client', fake_client)
def test_CMS_GetCpuloadavg5mData():
    func = get_tool_func("CMS_GetCpuloadavg5mData")
    result = func(RegionId='cn-test', InstanceIds=['i-1'])
    assert isinstance(result, list)

@patch('alibaba_cloud_ops_mcp_server.tools.cms_tools.create_client', fake_client)
def test_CMS_GetCpuloadavg15mData():
    func = get_tool_func("CMS_GetCpuloadavg15mData")
    result = func(RegionId='cn-test', InstanceIds=['i-1'])
    assert isinstance(result, list)

@patch('alibaba_cloud_ops_mcp_server.tools.cms_tools.create_client', fake_client)
def test_CMS_GetMemUsedData():
    func = get_tool_func("CMS_GetMemUsedData")
    result = func(RegionId='cn-test', InstanceIds=['i-1'])
    assert isinstance(result, list)

@patch('alibaba_cloud_ops_mcp_server.tools.cms_tools.create_client', fake_client)
def test_CMS_GetMemUsageData():
    func = get_tool_func("CMS_GetMemUsageData")
    result = func(RegionId='cn-test', InstanceIds=['i-1'])
    assert isinstance(result, list)

@patch('alibaba_cloud_ops_mcp_server.tools.cms_tools.create_client', fake_client)
def test_CMS_GetDiskUsageData():
    func = get_tool_func("CMS_GetDiskUsageData")
    result = func(RegionId='cn-test', InstanceIds=['i-1'])
    assert isinstance(result, list)

@patch('alibaba_cloud_ops_mcp_server.tools.cms_tools.create_client', fake_client)
def test_CMS_GetDiskTotalData():
    func = get_tool_func("CMS_GetDiskTotalData")
    result = func(RegionId='cn-test', InstanceIds=['i-1'])
    assert isinstance(result, list)

@patch('alibaba_cloud_ops_mcp_server.tools.cms_tools.create_client', fake_client)
def test_CMS_GetDiskUsedData():
    func = get_tool_func("CMS_GetDiskUsedData")
    result = func(RegionId='cn-test', InstanceIds=['i-1'])
    assert isinstance(result, list)

def test_create_client_exception():
    with patch('alibaba_cloud_ops_mcp_server.tools.cms_tools.create_config', side_effect=Exception('fail')):
        with pytest.raises(Exception) as e:
            cms_tools.create_client('cn-test')
        assert 'fail' in str(e.value)

def test_get_cms_metric_data_empty_instance_ids():
    # instance_ids 为空
    class FakeResp:
        class Body:
            datapoints = []
        body = Body()
    class FakeClient:
        def describe_metric_last(self, req):
            return FakeResp()
    with patch('alibaba_cloud_ops_mcp_server.tools.cms_tools.create_client', return_value=FakeClient()):
        result = cms_tools._get_cms_metric_data('cn-test', [], 'cpu_total')
        assert result == []

def test_get_cms_metric_data_client_exception():
    class FakeClient:
        def describe_metric_last(self, req):
            raise Exception('fail-metric')
    with patch('alibaba_cloud_ops_mcp_server.tools.cms_tools.create_client', return_value=FakeClient()):
        with pytest.raises(Exception) as e:
            cms_tools._get_cms_metric_data('cn-test', ['i-1'], 'cpu_total')
        assert 'fail-metric' in str(e.value)

def test_get_cms_metric_data_multiple_instance_ids():
    # instance_ids 有多个元素，覆盖 for 循环
    class FakeResp:
        class Body:
            datapoints = [{'value': 1}, {'value': 2}]
        body = Body()
    class FakeClient:
        def describe_metric_last(self, req):
            # 检查 dimensions 是否包含多个 instanceId
            dims = json.loads(req.dimensions)
            assert isinstance(dims, list)
            assert {'instanceId': 'i-1'} in dims
            assert {'instanceId': 'i-2'} in dims
            return FakeResp()
    with patch('alibaba_cloud_ops_mcp_server.tools.cms_tools.create_client', return_value=FakeClient()):
        result = cms_tools._get_cms_metric_data('cn-test', ['i-1', 'i-2'], 'cpu_total')
        assert result == [{'value': 1}, {'value': 2}]

def test_create_client():
    """测试create_client函数的基本功能"""
    with patch('alibaba_cloud_ops_mcp_server.tools.cms_tools.create_config') as mock_create_config, \
         patch('alibaba_cloud_ops_mcp_server.tools.cms_tools.cms20190101Client') as mock_client:
        
        # 模拟配置对象
        mock_config = MagicMock()
        mock_create_config.return_value = mock_config
        
        # 模拟客户端对象
        mock_client_instance = MagicMock()
        mock_client.return_value = mock_client_instance
        
        # 调用函数
        region_id = 'cn-hangzhou'
        result = cms_tools.create_client(region_id)
        
        # 验证create_config被调用
        mock_create_config.assert_called_once()
        
        # 验证endpoint被正确设置
        assert mock_config.endpoint == f'metrics.{region_id}.aliyuncs.com'
        
        # 验证cms20190101Client被正确调用
        mock_client.assert_called_once_with(mock_config)
        
        # 验证返回的是客户端实例
        assert result == mock_client_instance


def test_create_client_different_regions():
    """测试create_client函数在不同region下的行为"""
    with patch('alibaba_cloud_ops_mcp_server.tools.cms_tools.create_config') as mock_create_config, \
         patch('alibaba_cloud_ops_mcp_server.tools.cms_tools.cms20190101Client') as mock_client:
        
        mock_config = MagicMock()
        mock_create_config.return_value = mock_config
        mock_client_instance = MagicMock()
        mock_client.return_value = mock_client_instance
        
        # 测试不同的region
        test_regions = ['cn-hangzhou', 'cn-beijing', 'us-west-1']
        
        for region_id in test_regions:
            # 重置mock
            mock_config.reset_mock()
            mock_client.reset_mock()
            
            # 调用函数
            result = cms_tools.create_client(region_id)
            
            # 验证endpoint格式正确
            expected_endpoint = f'metrics.{region_id}.aliyuncs.com'
            assert mock_config.endpoint == expected_endpoint
            
            # 验证客户端被创建
            mock_client.assert_called_once_with(mock_config)
            assert result == mock_client_instance
