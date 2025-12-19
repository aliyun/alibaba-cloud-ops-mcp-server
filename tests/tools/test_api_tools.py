import pytest
from unittest.mock import patch, MagicMock
from alibaba_cloud_ops_mcp_server.tools import api_tools
import json
from alibaba_cloud_ops_mcp_server.tools import common_api_tools
from alibaba_cloud_ops_mcp_server.tools.common_api_tools import (
    PromptUnderstanding, ListAPIs, GetAPIInfo, CommonAPICaller
)

def fake_api_meta(post=False, no_summary=False):
    meta = {
        'parameters': [
            {'name': 'InstanceId', 'schema': {'type': 'string', 'description': '实例ID', 'example': 'i-123', 'required': True}},
            {'name': 'RegionId', 'schema': {'type': 'string', 'description': '地域ID', 'example': 'cn-hangzhou', 'required': False}},
            {'name': 'Ids', 'schema': {'type': 'array', 'description': 'ID列表', 'example': '"[\"a\",\"b\"]"', 'required': False}},
        ],
        'methods': ['post'] if post else ['get'],
        'path': '/test',
    }
    if not no_summary:
        meta['summary'] = '测试API'
    return meta, '2023-01-01'

class DummyMCP:
    def tool(self, name):
        def decorator(fn):
            return fn
        return decorator

def test_create_function_schemas():
    api_meta, _ = fake_api_meta()
    schemas = api_tools._create_function_schemas('ecs', 'DescribeInstances', api_meta)
    assert 'DescribeInstances' in schemas
    assert 'InstanceId' in schemas['DescribeInstances']
    assert schemas['DescribeInstances']['InstanceId'][0] == str
    assert schemas['DescribeInstances']['Ids'][0] == list

def test_create_parameter_schema():
    fields = {
        'foo': (str, MagicMock()),
        'bar': (int, MagicMock())
    }
    schema_cls = api_tools._create_parameter_schema(fields)
    inst = schema_cls(foo='a', bar=1)
    assert inst.foo == 'a' and inst.bar == 1

def test_create_tool_function_with_signature_required():
    api_meta, _ = fake_api_meta()
    schemas = api_tools._create_function_schemas('ecs', 'DescribeInstances', api_meta)
    fields = schemas['DescribeInstances']
    func = api_tools._create_tool_function_with_signature('ecs', 'DescribeInstances', fields, 'desc')
    # 检查参数名、类型、注释和default存在
    for name, (typ, field_info) in fields.items():
        param = func.__signature__.parameters[name]
        assert param.name == name
        assert param.annotation == typ
        assert hasattr(param, 'default')

def test_create_client_non_str_service():
    with patch('alibaba_cloud_ops_mcp_server.tools.api_tools.OpenApiClient') as mock_client, \
         patch('alibaba_cloud_ops_mcp_server.tools.api_tools.create_config') as mock_cfg:
        mock_cfg.return_value = MagicMock()
        client = api_tools.create_client(service=MagicMock(__str__=lambda self: 'ecs'), region_id='cn-test')
        assert mock_client.called
        assert mock_cfg.return_value.endpoint == 'ecs.cn-test.aliyuncs.com'

def test_tools_api_call_post():
    with patch('alibaba_cloud_ops_mcp_server.tools.api_tools.ApiMetaClient') as mock_ApiMetaClient, \
         patch('alibaba_cloud_ops_mcp_server.tools.api_tools.create_client') as mock_create_client, \
         patch('alibaba_cloud_ops_mcp_server.tools.api_tools.open_api_models') as mock_open_api_models, \
         patch('alibaba_cloud_ops_mcp_server.tools.api_tools.OpenApiUtilClient') as mock_OpenApiUtilClient, \
         patch('alibaba_cloud_ops_mcp_server.tools.api_tools.util_models') as mock_util_models:
        mock_ApiMetaClient.get_api_meta.return_value = fake_api_meta(post=True)
        mock_ApiMetaClient.get_service_version.return_value = '2023-01-01'
        mock_ApiMetaClient.get_service_style.return_value = 'RPC'
        mock_open_api_models.OpenApiRequest.return_value = MagicMock()
        mock_open_api_models.Params.return_value = MagicMock()
        mock_create_client.return_value.call_api.return_value = {'result': 'ok'}
        mock_OpenApiUtilClient.query.return_value = {}
        mock_util_models.RuntimeOptions.return_value = MagicMock()
        params = {'InstanceId': 'i-123', 'RegionId': 'cn-hangzhou'}
        result = api_tools._tools_api_call('ecs', 'DescribeInstances', params, None)
        assert result == {'result': 'ok'}

def test_create_and_decorate_tool_no_summary():
    with patch('alibaba_cloud_ops_mcp_server.tools.api_tools.ApiMetaClient.get_api_meta', return_value=fake_api_meta(no_summary=True)):
        mcp = DummyMCP()
        fn = api_tools._create_and_decorate_tool(mcp, 'ecs', 'DescribeInstances')
        assert callable(fn)

def test_create_api_tools():
    with patch('alibaba_cloud_ops_mcp_server.tools.api_tools._create_and_decorate_tool') as mock_create:
        mcp = DummyMCP()
        config = {'ecs': ['DescribeInstances', 'StartInstance'], 'rds': ['DescribeDBInstances']}
        api_tools.create_api_tools(mcp, config)
        assert mock_create.call_count == 3

def test_create_function_schemas_ignore_dot():
    api_meta = {
        'parameters': [
            {'name': 'foo.bar', 'schema': {'type': 'string'}},
            {'name': 'baz', 'schema': {'type': 'string'}},
        ]
    }
    schemas = api_tools._create_function_schemas('ecs', 'TestApi', api_meta)
    assert 'foo.bar' not in schemas['TestApi']
    assert 'baz' in schemas['TestApi']

def test_create_function_schemas_no_regionid():
    api_meta = {
        'parameters': [
            {'name': 'foo', 'schema': {'type': 'string'}},
        ]
    }
    schemas = api_tools._create_function_schemas('ecs', 'TestApi', api_meta)
    assert 'RegionId' in schemas['TestApi']

# 说明：由于 _create_tool_function_with_signature 生成的参数总有默认值，signature.bind 不会因缺参数抛 TypeError，故无法覆盖该异常分支。

def test_create_client_str_service():
    with patch('alibaba_cloud_ops_mcp_server.tools.api_tools.OpenApiClient') as mock_client, \
         patch('alibaba_cloud_ops_mcp_server.tools.api_tools.create_config') as mock_cfg:
        mock_cfg.return_value = MagicMock()
        client = api_tools.create_client(service='ecs', region_id='cn-test')
        assert mock_client.called
        assert mock_cfg.return_value.endpoint == 'ecs.cn-test.aliyuncs.com'

def test_create_and_decorate_tool_api_meta_exception():
    # 覆盖 _create_and_decorate_tool 的异常分支
    with patch('alibaba_cloud_ops_mcp_server.tools.api_tools.ApiMetaClient.get_api_meta', side_effect=Exception('meta-fail')):
        mcp = DummyMCP()
        with pytest.raises(Exception) as e:
            api_tools._create_and_decorate_tool(mcp, 'ecs', 'DescribeInstances')
        assert 'meta-fail' in str(e.value)

def test_create_function_schemas_ecs_list_parameters():
    # 测试ECS服务的特殊参数处理
    api_meta = {
        'parameters': [
            {'name': 'InstanceIds', 'schema': {'type': 'string', 'description': '实例ID列表', 'example': '["i-123", "i-456"]', 'required': True}},
            {'name': 'SecurityGroupIds', 'schema': {'type': 'string', 'description': '安全组ID列表', 'example': '["sg-123", "sg-456"]', 'required': False}},
            {'name': 'NormalParam', 'schema': {'type': 'string', 'description': '普通参数', 'example': 'test', 'required': False}},
        ],
        'methods': ['get'],
        'path': '/test',
        'summary': '测试API'
    }
    
    # 测试ECS服务
    schemas = api_tools._create_function_schemas('ecs', 'DescribeInstances', api_meta)
    assert schemas['DescribeInstances']['InstanceIds'][0] == list
    assert schemas['DescribeInstances']['SecurityGroupIds'][0] == list
    assert schemas['DescribeInstances']['NormalParam'][0] == str
    
    # 测试非ECS服务
    schemas = api_tools._create_function_schemas('rds', 'DescribeInstances', api_meta)
    assert schemas['DescribeInstances']['InstanceIds'][0] == str
    assert schemas['DescribeInstances']['SecurityGroupIds'][0] == str
    assert schemas['DescribeInstances']['NormalParam'][0] == str

def test_tools_api_call_ecs_list_parameters():
    with patch('alibaba_cloud_ops_mcp_server.tools.api_tools.ApiMetaClient') as mock_ApiMetaClient, \
         patch('alibaba_cloud_ops_mcp_server.tools.api_tools.create_client') as mock_create_client, \
         patch('alibaba_cloud_ops_mcp_server.tools.api_tools.open_api_models') as mock_open_api_models, \
         patch('alibaba_cloud_ops_mcp_server.tools.api_tools.OpenApiUtilClient') as mock_OpenApiUtilClient, \
         patch('alibaba_cloud_ops_mcp_server.tools.api_tools.util_models') as mock_util_models:
        
        mock_ApiMetaClient.get_api_meta.return_value = fake_api_meta()
        mock_ApiMetaClient.get_service_version.return_value = '2023-01-01'
        mock_ApiMetaClient.get_service_style.return_value = 'RPC'
        mock_open_api_models.OpenApiRequest.return_value = MagicMock()
        mock_open_api_models.Params.return_value = MagicMock()
        mock_create_client.return_value.call_api.return_value = {'result': 'ok'}
        mock_OpenApiUtilClient.query.return_value = {}
        mock_util_models.RuntimeOptions.return_value = MagicMock()

        # 测试ECS服务的列表参数转换
        params = {
            'InstanceIds': ['i-123', 'i-456'],
            'SecurityGroupIds': ['sg-123', 'sg-456'],
            'NormalParam': 'test',
            'RegionId': 'cn-hangzhou'
        }
        
        # 测试ECS服务
        result = api_tools._tools_api_call('ecs', 'DescribeInstances', params, None)
        # 验证传入query方法的参数
        query_args = mock_OpenApiUtilClient.query.call_args[0][0]
        assert isinstance(query_args['InstanceIds'], str)
        assert isinstance(query_args['SecurityGroupIds'], str)
        assert query_args['NormalParam'] == 'test'
        assert json.loads(query_args['InstanceIds']) == ['i-123', 'i-456']
        assert json.loads(query_args['SecurityGroupIds']) == ['sg-123', 'sg-456']
        
        # 重置mock
        mock_OpenApiUtilClient.query.reset_mock()
        
        # 测试非ECS服务
        result = api_tools._tools_api_call('rds', 'DescribeInstances', params, None)
        # 验证传入query方法的参数
        query_args = mock_OpenApiUtilClient.query.call_args[0][0]
        assert isinstance(query_args['InstanceIds'], list)
        assert isinstance(query_args['SecurityGroupIds'], list)
        assert query_args['InstanceIds'] == ['i-123', 'i-456']
        assert query_args['SecurityGroupIds'] == ['sg-123', 'sg-456']

def test_tools_api_call_ecs_list_parameters_non_list():
    with patch('alibaba_cloud_ops_mcp_server.tools.api_tools.ApiMetaClient') as mock_ApiMetaClient, \
         patch('alibaba_cloud_ops_mcp_server.tools.api_tools.create_client') as mock_create_client, \
         patch('alibaba_cloud_ops_mcp_server.tools.api_tools.open_api_models') as mock_open_api_models, \
         patch('alibaba_cloud_ops_mcp_server.tools.api_tools.OpenApiUtilClient') as mock_OpenApiUtilClient, \
         patch('alibaba_cloud_ops_mcp_server.tools.api_tools.util_models') as mock_util_models:
        
        mock_ApiMetaClient.get_api_meta.return_value = fake_api_meta()
        mock_ApiMetaClient.get_service_version.return_value = '2023-01-01'
        mock_ApiMetaClient.get_service_style.return_value = 'RPC'
        mock_open_api_models.OpenApiRequest.return_value = MagicMock()
        mock_open_api_models.Params.return_value = MagicMock()
        mock_create_client.return_value.call_api.return_value = {'result': 'ok'}
        mock_OpenApiUtilClient.query.return_value = {}
        mock_util_models.RuntimeOptions.return_value = MagicMock()

        # 测试非列表类型的特殊参数
        params = {
            'InstanceIds': 'i-123',  # 字符串而不是列表
            'SecurityGroupIds': None,  # None值
            'RegionId': 'cn-hangzhou'
        }
        
        # 测试ECS服务
        result = api_tools._tools_api_call('ecs', 'DescribeInstances', params, None)
        # 验证传入query方法的参数
        query_args = mock_OpenApiUtilClient.query.call_args[0][0]
        assert query_args['InstanceIds'] == 'i-123'

def test_create_tool_function_with_signature_bind_and_apply_defaults():
    """测试func_code函数中的signature.bind和apply_defaults调用"""
    api_meta = {
        'parameters': [
            {'name': 'param1', 'schema': {'type': 'string', 'required': False}},
            {'name': 'param2', 'schema': {'type': 'integer', 'required': True}}
        ],
        'summary': 'Test function'
    }
    
    schemas = api_tools._create_function_schemas('test', 'TestApi', api_meta)
    fields = schemas['TestApi']
    
    # 创建函数
    func = api_tools._create_tool_function_with_signature('test', 'TestApi', fields, 'Test function')
    
    # 测试函数调用，确保执行到signature.bind和apply_defaults
    with patch('alibaba_cloud_ops_mcp_server.tools.api_tools._tools_api_call') as mock_call:
        mock_call.return_value = {'result': 'success'}
        
        # 调用函数，传入部分参数，让apply_defaults生效
        result = func(param2=123)  # 只传入required参数，让param1使用默认值
        
        # 验证_tools_api_call被调用
        mock_call.assert_called_once()
        call_args = mock_call.call_args[1]['parameters']
        
        # 验证参数绑定和默认值应用
        assert 'param1' in call_args  # 默认值被应用
        assert call_args['param2'] == 123  # 传入的参数

def test_create_tool_function_with_signature_bind_with_all_args():
    """测试func_code函数中传入所有参数的情况"""
    api_meta = {
        'parameters': [
            {'name': 'param1', 'schema': {'type': 'string', 'required': False}},
            {'name': 'param2', 'schema': {'type': 'integer', 'required': False}}
        ],
        'summary': 'Test function'
    }
    
    schemas = api_tools._create_function_schemas('test', 'TestApi', api_meta)
    fields = schemas['TestApi']
    
    # 创建函数
    func = api_tools._create_tool_function_with_signature('test', 'TestApi', fields, 'Test function')
    
    # 测试传入所有参数
    with patch('alibaba_cloud_ops_mcp_server.tools.api_tools._tools_api_call') as mock_call:
        mock_call.return_value = {'result': 'success'}
        
        # 传入所有参数
        result = func(param1='value1', param2=456)
        
        # 验证_tools_api_call被调用
        mock_call.assert_called_once()
        call_args = mock_call.call_args[1]['parameters']
        
        # 验证所有参数都被正确传递
        assert call_args['param1'] == 'value1'
        assert call_args['param2'] == 456

def test_create_tool_function_with_signature_bind_with_positional_args():
    """测试func_code函数中使用位置参数的情况"""
    api_meta = {
        'parameters': [
            {'name': 'param1', 'schema': {'type': 'string', 'required': False}},
            {'name': 'param2', 'schema': {'type': 'integer', 'required': False}}
        ],
        'summary': 'Test function'
    }
    
    schemas = api_tools._create_function_schemas('test', 'TestApi', api_meta)
    fields = schemas['TestApi']
    
    # 创建函数
    func = api_tools._create_tool_function_with_signature('test', 'TestApi', fields, 'Test function')
    
    # 测试使用位置参数
    with patch('alibaba_cloud_ops_mcp_server.tools.api_tools._tools_api_call') as mock_call:
        mock_call.return_value = {'result': 'success'}
        
        # 使用位置参数调用
        result = func('value1', 789)
        
        # 验证_tools_api_call被调用
        mock_call.assert_called_once()
        call_args = mock_call.call_args[1]['parameters']
        
        # 验证位置参数被正确绑定
        assert call_args['param1'] == 'value1'
        assert call_args['param2'] == 789

def test_prompt_understanding_default():
    # _CUSTOM_SERVICE_LIST 为空
    import alibaba_cloud_ops_mcp_server.tools.common_api_tools as ca
    ca._CUSTOM_SERVICE_LIST = None
    fn = ca.tools[0]  # PromptUnderstanding
    result = fn()
    assert isinstance(result, str)
    assert 'Supported Services' in result

def test_prompt_understanding_with_custom_service():
    # _CUSTOM_SERVICE_LIST 有值
    import alibaba_cloud_ops_mcp_server.tools.common_api_tools as ca
    ca._CUSTOM_SERVICE_LIST = [('ecs', 'ECS服务'), ('rds', 'RDS服务')]
    fn = ca.tools[0]  # PromptUnderstanding
    result = fn()
    assert 'ecs: ECS服务' in result and 'rds: RDS服务' in result

@patch('alibaba_cloud_ops_mcp_server.tools.common_api_tools.ApiMetaClient.get_apis_in_service')
def test_list_apis(mock_get):
    import alibaba_cloud_ops_mcp_server.tools.common_api_tools as ca
    fn = ca.tools[1]  # ListAPIs
    mock_get.return_value = ['DescribeInstances', 'StartInstance']
    result = fn('ecs')
    assert result == ['DescribeInstances', 'StartInstance']

@patch('alibaba_cloud_ops_mcp_server.tools.common_api_tools.ApiMetaClient.get_api_meta')
def test_get_api_info(mock_get):
    import alibaba_cloud_ops_mcp_server.tools.common_api_tools as ca
    fn = ca.tools[2]  # GetAPIInfo
    mock_get.return_value = ({'parameters': [{'name': 'foo'}]}, '2014-05-26')
    result = fn('ecs', 'DescribeInstances')
    assert result == [{'name': 'foo'}]

@patch('alibaba_cloud_ops_mcp_server.tools.common_api_tools._tools_api_call')
def test_common_api_caller(mock_call):
    import alibaba_cloud_ops_mcp_server.tools.common_api_tools as ca
    fn = ca.tools[3]  # CommonAPICaller
    mock_call.return_value = {'result': 'ok'}
    result = fn('ecs', 'DescribeInstances', {'foo': 'bar'})
    assert result == {'result': 'ok'}

@patch('alibaba_cloud_ops_mcp_server.tools.api_tools.create_config')
@patch('alibaba_cloud_ops_mcp_server.tools.api_tools.OpenApiClient', autospec=True)
def test_create_client(mock_client, mock_create_config):
    from alibaba_cloud_ops_mcp_server.tools import api_tools
    mock_create_config.return_value = MagicMock()
    mock_client.return_value = 'client_obj'
    result = api_tools.create_client('ecs', 'cn-hangzhou')
    assert result == 'client_obj'

def test_get_service_endpoint_all_branches():
    from alibaba_cloud_ops_mcp_server.tools.api_tools import _get_service_endpoint
    # REGION_ENDPOINT_SERVICE 分支
    assert _get_service_endpoint('ecs', 'cn-hangzhou') == 'ecs.cn-hangzhou.aliyuncs.com'
    # DOUBLE_ENDPOINT_SERVICE 且 region 匹配
    assert _get_service_endpoint('rds', 'cn-hangzhou') == 'rds.aliyuncs.com'
    # CENTRAL_ENDPOINTS_SERVICE 分支
    assert _get_service_endpoint('cbn', 'cn-hangzhou') == 'cbn.aliyuncs.com'
    # 其它分支
    assert _get_service_endpoint('unknown', 'cn-test') == 'unknown.cn-test.aliyuncs.com'
