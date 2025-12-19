import pytest
from unittest.mock import patch, MagicMock
from alibaba_cloud_ops_mcp_server.tools import oos_tools

def get_tool_func(name):
    return [f for f in oos_tools.tools if f.__name__ == name][0]

def fake_client(*args, **kwargs):
    class FakeExecution:
        execution_id = 'exec-1'
        status = 'Success'
        status_message = 'ok'
    class FakeBody:
        executions = [FakeExecution()]
    class FakeListResp:
        body = FakeBody()
    class FakeStartResp:
        class Body:
            class Execution:
                execution_id = 'exec-1'
            execution = Execution()
        body = Body()
    class FakeClient:
        def start_execution(self, req):
            return FakeStartResp()
        def list_executions(self, req):
            return FakeListResp()
    return FakeClient()

@patch('alibaba_cloud_ops_mcp_server.tools.oos_tools.create_client', fake_client)
def test_OOS_RunCommand():
    func = get_tool_func("OOS_RunCommand")
    result = func(RegionId='cn-test', InstanceIds=['i-1'], CommandType='RunShellScript', Command='echo hello')
    assert hasattr(result, 'executions')

@patch('alibaba_cloud_ops_mcp_server.tools.oos_tools.create_client', fake_client)
def test_OOS_StartInstances():
    func = get_tool_func("OOS_StartInstances")
    result = func(RegionId='cn-test', InstanceIds=['i-1'])
    assert hasattr(result, 'executions')

@patch('alibaba_cloud_ops_mcp_server.tools.oos_tools.create_client', fake_client)
def test_OOS_StopInstances():
    func = get_tool_func("OOS_StopInstances")
    result = func(RegionId='cn-test', InstanceIds=['i-1'], ForeceStop=True)
    assert hasattr(result, 'executions')

@patch('alibaba_cloud_ops_mcp_server.tools.oos_tools.create_client', fake_client)
def test_OOS_RebootInstances():
    func = get_tool_func("OOS_RebootInstances")
    result = func(RegionId='cn-test', InstanceIds=['i-1'], ForeceStop=True)
    assert hasattr(result, 'executions')

@patch('alibaba_cloud_ops_mcp_server.tools.oos_tools.create_client', fake_client)
def test_OOS_RunInstances():
    func = get_tool_func("OOS_RunInstances")
    result = func(
        RegionId='cn-test',
        ImageId='img',
        InstanceType='ecs.t1',
        SecurityGroupId='sg',
        VSwitchId='vsw',
        InternetMaxBandwidthOut=0,
        Amount=1,
        InstanceName='test',
        SystemDiskCategory='',
        SystemDiskSize='',
        SystemDiskName='',
        SystemDiskDescription='',
        SystemDiskPerformanceLevel='1',
        PrivateIpAddress='102',
        SystemDiskAutoSnapshotPolicyId='1',
        DataDiskParameters='[]',
        Tags='',
        ResourceGroupId='1',
        Description='',
        HostName='test',
        ZoneId='cn-hangzhou-a'
    )
    assert hasattr(result, 'executions')

@patch('alibaba_cloud_ops_mcp_server.tools.oos_tools.create_client', fake_client)
def test_OOS_ResetPassword():
    func = get_tool_func("OOS_ResetPassword")
    result = func(RegionId='cn-test', InstanceIds=['i-1'], Password='Abcd1234!')
    assert hasattr(result, 'executions')

@patch('alibaba_cloud_ops_mcp_server.tools.oos_tools.create_client', fake_client)
def test_OOS_ReplaceSystemDisk():
    func = get_tool_func("OOS_ReplaceSystemDisk")
    result = func(RegionId='cn-test', InstanceIds=['i-1'], ImageId='img')
    assert hasattr(result, 'executions')

@patch('alibaba_cloud_ops_mcp_server.tools.oos_tools.create_client', fake_client)
def test_OOS_StartRDSInstances():
    func = get_tool_func("OOS_StartRDSInstances")
    result = func(RegionId='cn-test', InstanceIds=['rds-1'])
    assert hasattr(result, 'executions')

@patch('alibaba_cloud_ops_mcp_server.tools.oos_tools.create_client', fake_client)
def test_OOS_StopRDSInstances():
    func = get_tool_func("OOS_StopRDSInstances")
    result = func(RegionId='cn-test', InstanceIds=['rds-1'])
    assert hasattr(result, 'executions')

@patch('alibaba_cloud_ops_mcp_server.tools.oos_tools.create_client', fake_client)
def test_OOS_RebootRDSInstances():
    func = get_tool_func("OOS_RebootRDSInstances")
    result = func(RegionId='cn-test', InstanceIds=['rds-1'])
    assert hasattr(result, 'executions')

def test_create_client_exception():
    with patch('alibaba_cloud_ops_mcp_server.tools.oos_tools.create_config', side_effect=Exception('fail')):
        with pytest.raises(Exception) as e:
            oos_tools.create_client('cn-test')
        assert 'fail' in str(e.value)

def test_start_execution_sync_failed():
    # FakeClient 返回 status==FAILED
    class FakeExecution:
        execution_id = 'exec-1'
        status = 'Failed'
        status_message = 'fail-reason'
    class FakeBody:
        executions = [FakeExecution()]
    class FakeListResp:
        body = FakeBody()
    class FakeStartResp:
        class Body:
            class Execution:
                execution_id = 'exec-1'
            execution = Execution()
        body = Body()
    class FakeClient:
        def start_execution(self, req):
            return FakeStartResp()
        def list_executions(self, req):
            return FakeListResp()
    with patch('alibaba_cloud_ops_mcp_server.tools.oos_tools.create_client', return_value=FakeClient()):
        with pytest.raises(Exception) as e:
            oos_tools._start_execution_sync('cn-test', 'tpl', {})
        assert 'fail-reason' in str(e.value)

def test_start_execution_sync_loop():
    # status 既不是 FAILED 也不是 END_STATUSES，触发 time.sleep(1)
    class FakeExecution:
        execution_id = 'exec-1'
        status = 'Running'
        status_message = 'running'
    class FakeBody:
        executions = [FakeExecution()]
    class FakeListResp:
        body = FakeBody()
    class FakeStartResp:
        class Body:
            class Execution:
                execution_id = 'exec-1'
            execution = Execution()
        body = Body()
    class FakeClient:
        def __init__(self):
            self.calls = 0
        def start_execution(self, req):
            return FakeStartResp()
        def list_executions(self, req):
            # 前两次返回 Running，第三次返回 Success
            self.calls += 1
            if self.calls < 3:
                return FakeListResp()
            else:
                class DoneExecution:
                    execution_id = 'exec-1'
                    status = 'Success'
                    status_message = 'ok'
                class DoneBody:
                    executions = [DoneExecution()]
                class DoneListResp:
                    body = DoneBody()
                return DoneListResp()
    with patch('alibaba_cloud_ops_mcp_server.tools.oos_tools.create_client', return_value=FakeClient()), \
         patch('time.sleep', return_value=None) as mock_sleep:
        result = oos_tools._start_execution_sync('cn-test', 'tpl', {})
        assert hasattr(result, 'executions')
        assert mock_sleep.call_count >= 1

def test_create_client():
    """测试create_client函数的基本功能"""
    with patch('alibaba_cloud_ops_mcp_server.tools.oos_tools.create_config') as mock_create_config, \
         patch('alibaba_cloud_ops_mcp_server.tools.oos_tools.oos20190601Client') as mock_client:
        
        # 模拟配置对象
        mock_config = MagicMock()
        mock_create_config.return_value = mock_config
        
        # 模拟客户端对象
        mock_client_instance = MagicMock()
        mock_client.return_value = mock_client_instance
        
        # 调用函数
        region_id = 'cn-hangzhou'
        result = oos_tools.create_client(region_id)
        
        # 验证create_config被调用
        mock_create_config.assert_called_once()
        
        # 验证endpoint被正确设置
        assert mock_config.endpoint == f'oos.{region_id}.aliyuncs.com'
        
        # 验证oos20190601Client被正确调用
        mock_client.assert_called_once_with(mock_config)
        
        # 验证返回的是客户端实例
        assert result == mock_client_instance


def test_create_client_different_regions():
    """测试create_client函数在不同region下的行为"""
    with patch('alibaba_cloud_ops_mcp_server.tools.oos_tools.create_config') as mock_create_config, \
         patch('alibaba_cloud_ops_mcp_server.tools.oos_tools.oos20190601Client') as mock_client:
        
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
            result = oos_tools.create_client(region_id)
            
            # 验证endpoint格式正确
            expected_endpoint = f'oos.{region_id}.aliyuncs.com'
            assert mock_config.endpoint == expected_endpoint
            
            # 验证客户端被创建
            mock_client.assert_called_once_with(mock_config)
            assert result == mock_client_instance
