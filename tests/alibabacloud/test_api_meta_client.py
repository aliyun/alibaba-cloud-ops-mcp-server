import pytest
from unittest.mock import patch, MagicMock
from alibaba_cloud_ops_mcp_server.alibabacloud import api_meta_client

@patch('alibaba_cloud_ops_mcp_server.alibabacloud.api_meta_client.requests.get')
def test_get_response_from_pop_api_success(mock_get):
    mock_get.return_value.json.return_value = [{"code": "ecs", "defaultVersion": "2014-05-26", "style": "RPC"}]
    data = api_meta_client.ApiMetaClient.get_response_from_pop_api('GetProductList')
    assert isinstance(data, list)
    assert data[0]["code"] == "ecs"

@patch('alibaba_cloud_ops_mcp_server.alibabacloud.api_meta_client.requests.get')
def test_get_response_from_pop_api_exception(mock_get):
    mock_get.side_effect = Exception('fail')
    with pytest.raises(Exception) as e:
        api_meta_client.ApiMetaClient.get_response_from_pop_api('GetProductList')
    assert 'Failed to get response' in str(e.value)

@patch('alibaba_cloud_ops_mcp_server.alibabacloud.api_meta_client.requests.get')
def test_get_service_version_and_style(mock_get):
    mock_get.return_value.json.return_value = [{"code": "ecs", "defaultVersion": "2014-05-26", "style": "RPC"}]
    v = api_meta_client.ApiMetaClient.get_service_version('ecs')
    s = api_meta_client.ApiMetaClient.get_service_style('ecs')
    assert v == "2014-05-26"
    assert s == "RPC"

@patch('alibaba_cloud_ops_mcp_server.alibabacloud.api_meta_client.requests.get')
def test_get_standard_service_and_api(mock_get):
    # 1st call: GetProductList, 2nd call: GetApiOverview
    mock_get.return_value.json.side_effect = [
        [{"code": "ecs", "defaultVersion": "2014-05-26"}],
        {"apis": {"DescribeInstances": {}}}
    ]
    service, api = api_meta_client.ApiMetaClient.get_standard_service_and_api('ecs', 'DescribeInstances', '2014-05-26')
    assert service == 'ecs'
    assert api == 'DescribeInstances'

@patch('alibaba_cloud_ops_mcp_server.alibabacloud.api_meta_client.requests.get')
def test_get_api_meta_invalid(mock_get):
    # 1st call: GetProductList returns empty list
    mock_get.return_value.json.return_value = []
    with pytest.raises(Exception) as e:
        api_meta_client.ApiMetaClient.get_api_meta('notexist', 'api')
    assert 'InvalidServiceName' in str(e.value) or 'object has no attribute' in str(e.value)

@patch('alibaba_cloud_ops_mcp_server.alibabacloud.api_meta_client.ApiMetaClient.get_service_version', return_value='2014-05-26')
@patch('alibaba_cloud_ops_mcp_server.alibabacloud.api_meta_client.ApiMetaClient.get_standard_service_and_api', return_value=(None, 'api'))
def test_get_api_meta_service_none(mock_get_std, mock_get_ver):
    with pytest.raises(Exception) as e:
        api_meta_client.ApiMetaClient.get_api_meta('ecs', 'DescribeInstances')
    assert 'InvalidServiceName' in str(e.value)

@patch('alibaba_cloud_ops_mcp_server.alibabacloud.api_meta_client.ApiMetaClient.get_service_version', return_value='2014-05-26')
@patch('alibaba_cloud_ops_mcp_server.alibabacloud.api_meta_client.ApiMetaClient.get_standard_service_and_api', return_value=('ecs', None))
def test_get_api_meta_api_none(mock_get_std, mock_get_ver):
    with pytest.raises(Exception) as e:
        api_meta_client.ApiMetaClient.get_api_meta('ecs', 'DescribeInstances')
    assert 'InvalidAPIName' in str(e.value)

@patch('alibaba_cloud_ops_mcp_server.alibabacloud.api_meta_client.ApiMetaClient.get_api_meta', return_value=({}, '2014-05-26'))
def test_get_response_from_api_meta_empty(mock_get_meta):
    prop, ver = api_meta_client.ApiMetaClient.get_response_from_api_meta('ecs', 'DescribeInstances')
    assert prop == {}
    assert ver == '2014-05-26'

@patch('alibaba_cloud_ops_mcp_server.alibabacloud.api_meta_client.ApiMetaClient.get_standard_service_and_api', return_value=('ecs', 'api'))
@patch('alibaba_cloud_ops_mcp_server.alibabacloud.api_meta_client.ApiMetaClient.get_response_from_pop_api')
def test_get_ref_api_meta_keyerror(mock_pop_api, mock_std):
    # ref_path指向不存在的key
    mock_pop_api.return_value = {'apis': {}}
    with pytest.raises(KeyError):
        api_meta_client.ApiMetaClient.get_ref_api_meta({'$ref': '#/notfound'}, 'ecs', '2014-05-26')

@patch('alibaba_cloud_ops_mcp_server.alibabacloud.api_meta_client.ApiMetaClient.get_api_meta')
def test_get_api_parameters_params_in_and_ref(mock_get_meta):
    # 测试params_in过滤和递归ref
    api_meta = {
        'parameters': [
            {'name': 'foo', 'in': 'query', 'schema': {'type': 'string'}},
            {'name': 'bar', 'in': 'body', 'schema': {'type': 'string', '$ref': '#/defs/bar'}}
        ]
    }
    # get_ref_api_meta返回递归结构
    with patch.object(api_meta_client.ApiMetaClient, 'get_ref_api_meta', return_value={'properties': {'baz': {}}}):
        mock_get_meta.return_value = (api_meta, '2014-05-26')
        params = api_meta_client.ApiMetaClient.get_api_parameters('ecs', 'DescribeInstances', params_in='query')
        assert params == ['foo']
        # 测试递归ref
        params2 = api_meta_client.ApiMetaClient.get_api_parameters('ecs', 'DescribeInstances')
        assert 'baz' in params2

@patch('alibaba_cloud_ops_mcp_server.alibabacloud.api_meta_client.ApiMetaClient.get_api_meta')
def test_get_api_parameters_circular_ref(mock_get_meta):
    # 测试循环引用
    api_meta = {
        'parameters': [
            {'name': 'foo', 'in': 'query', 'schema': {'type': 'string', '$ref': '#/defs/foo'}}
        ]
    }
    # get_ref_api_meta返回带$ref的结构，模拟循环
    def fake_get_ref(data, service, version):
        return {'$ref': '#/defs/foo'}
    with patch.object(api_meta_client.ApiMetaClient, 'get_ref_api_meta', side_effect=fake_get_ref):
        mock_get_meta.return_value = (api_meta, '2014-05-26')
        params = api_meta_client.ApiMetaClient.get_api_parameters('ecs', 'DescribeInstances')
        assert 'foo' in params

@patch('alibaba_cloud_ops_mcp_server.alibabacloud.api_meta_client.ApiMetaClient.get_api_meta', side_effect=Exception('fail'))
def test_get_api_field_exception(mock_get_meta):
    val = api_meta_client.ApiMetaClient.get_api_field('parameters', 'ecs', 'DescribeInstances', default='d')
    assert val == 'd'

def test_get_api_body_style_none():
    # get_api_field返回None
    with patch.object(api_meta_client.ApiMetaClient, 'get_api_field', return_value=None):
        val = api_meta_client.ApiMetaClient.get_api_body_style('ecs', 'DescribeInstances')
        assert val is None
    # get_api_field返回无STYLE参数
    with patch.object(api_meta_client.ApiMetaClient, 'get_api_field', return_value=[{'in': 'body'}]):
        val = api_meta_client.ApiMetaClient.get_api_body_style('ecs', 'DescribeInstances')
        assert val is None

@patch('alibaba_cloud_ops_mcp_server.alibabacloud.api_meta_client.requests.get')
def test_get_apis_in_service(mock_get):
    # 第一次调用 get_service_version 需要 list，第二次 get_response_from_pop_api 需要 dict
    mock_get.return_value.json.side_effect = [
        [{"code": "ecs", "defaultVersion": "2014-05-26"}],  # for get_service_version
        {"apis": {"A": {}, "B": {}}}  # for get_response_from_pop_api
    ]
    apis = api_meta_client.ApiMetaClient.get_apis_in_service('ecs')
    assert set(apis) == {"A", "B"}

@patch('alibaba_cloud_ops_mcp_server.alibabacloud.api_meta_client.requests.get')
def test_get_response_from_pop_api_keyerror(mock_get):
    # config 缺 key
    with patch.object(api_meta_client.ApiMetaClient, 'config', {'GetProductList': {}}):
        with pytest.raises(Exception) as e:
            api_meta_client.ApiMetaClient.get_response_from_pop_api('GetProductList')
        assert 'Failed to format path' in str(e.value)

@patch('alibaba_cloud_ops_mcp_server.alibabacloud.api_meta_client.ApiMetaClient.get_api_meta', return_value=({}, '2014-05-26'))
def test_get_response_from_api_meta_no_properties(mock_get_meta):
    # property_values 取不到属性
    with patch.dict('alibaba_cloud_ops_mcp_server.alibabacloud.api_meta_client.__dict__', {'RESPONSES': 'responses', 'HTTP_SUCCESS_CODE': '200', 'SCHEMA': 'schema', 'PROPERTIES': 'properties'}):
        prop, ver = api_meta_client.ApiMetaClient.get_response_from_api_meta('ecs', 'DescribeInstances')
        assert prop == {}
        assert ver == '2014-05-26'

def test_get_api_parameters_empty():
    # parameters 为空
    with patch.object(api_meta_client.ApiMetaClient, 'get_api_meta', return_value=({'parameters': []}, '2014-05-26')):
        params = api_meta_client.ApiMetaClient.get_api_parameters('ecs', 'DescribeInstances')
        assert params == []

@patch('alibaba_cloud_ops_mcp_server.alibabacloud.api_meta_client.requests.get')
def test_get_apis_in_service_no_apis(mock_get):
    mock_get.return_value.json.return_value = {}
    with pytest.raises(KeyError):
        api_meta_client.ApiMetaClient.get_apis_in_service('ecs')

@patch('alibaba_cloud_ops_mcp_server.alibabacloud.api_meta_client.requests.get')
def test_get_api_parameters_schema_not_dict(mock_get):
    # get_api_meta返回的schema不是dict
    api_meta = {
        'parameters': [
            {'name': 'foo', 'in': 'query', 'schema': None},
            {'name': 'bar', 'in': 'query', 'schema': 'notadict'}
        ]
    }
    with patch.object(api_meta_client.ApiMetaClient, 'get_api_meta', return_value=(api_meta, '2014-05-26')):
        params = api_meta_client.ApiMetaClient.get_api_parameters('ecs', 'DescribeInstances')
        # 两个参数都应该被返回
        assert 'foo' in params
        assert 'bar' in params

@patch('alibaba_cloud_ops_mcp_server.alibabacloud.api_meta_client.requests.get')
def test_get_apis_in_service_normal(mock_get):
    """测试get_apis_in_service方法正常返回API列表"""
    mock_get.return_value.json.side_effect = [
        [{"code": "ecs", "defaultVersion": "2014-05-26"}],  # for get_service_version
        {"apis": {"DescribeInstances": {}, "StartInstance": {}}}  # for get_response_from_pop_api
    ]
    apis = api_meta_client.ApiMetaClient.get_apis_in_service('ecs')
    assert set(apis) == {"DescribeInstances", "StartInstance"}
    assert len(apis) == 2

@patch('alibaba_cloud_ops_mcp_server.alibabacloud.api_meta_client.ApiMetaClient.get_service_version', return_value='2014-05-26')
@patch('alibaba_cloud_ops_mcp_server.alibabacloud.api_meta_client.ApiMetaClient.get_standard_service_and_api', return_value=(None, None))
@patch('alibaba_cloud_ops_mcp_server.alibabacloud.api_meta_client.ApiMetaClient.get_response_from_pop_api')
def test_get_api_meta_service_none_exception(mock_pop_api, mock_get_std, mock_get_ver):
    """测试get_api_meta方法中service_standard为None时抛出异常"""
    with pytest.raises(Exception) as e:
        api_meta_client.ApiMetaClient.get_api_meta('ecs', 'DescribeInstances')
    assert 'InvalidServiceName' in str(e.value)

@patch('alibaba_cloud_ops_mcp_server.alibabacloud.api_meta_client.ApiMetaClient.get_service_version', return_value='2014-05-26')
@patch('alibaba_cloud_ops_mcp_server.alibabacloud.api_meta_client.ApiMetaClient.get_standard_service_and_api', return_value=('ecs', None))
@patch('alibaba_cloud_ops_mcp_server.alibabacloud.api_meta_client.ApiMetaClient.get_response_from_pop_api')
def test_get_api_meta_api_none_exception(mock_pop_api, mock_get_std, mock_get_ver):
    """测试get_api_meta方法中api_standard为None时抛出异常"""
    with pytest.raises(Exception) as e:
        api_meta_client.ApiMetaClient.get_api_meta('ecs', 'DescribeInstances')
    assert 'InvalidAPIName' in str(e.value)

@patch('alibaba_cloud_ops_mcp_server.alibabacloud.api_meta_client.ApiMetaClient.get_api_meta')
def test_get_api_parameters_schema_not_dict_more_cases(mock_get_meta):
    """测试get_api_parameters中更多非dict类型的schema"""
    api_meta = {
        'parameters': [
            {'name': 'foo', 'in': 'query', 'schema': 'string'},  # 字符串
            {'name': 'bar', 'in': 'query', 'schema': 123},       # 数字
            {'name': 'baz', 'in': 'query', 'schema': []},        # 列表
            {'name': 'qux', 'in': 'query', 'schema': None},      # None
        ]
    }
    mock_get_meta.return_value = (api_meta, '2014-05-26')
    params = api_meta_client.ApiMetaClient.get_api_parameters('ecs', 'DescribeInstances')
    assert 'foo' in params
    assert 'bar' in params
    assert 'baz' in params
    assert 'qux' in params

@patch('alibaba_cloud_ops_mcp_server.alibabacloud.api_meta_client.requests.get')
def test_get_apis_in_service_normal(mock_get):
    """测试get_apis_in_service方法正常返回API列表"""
    mock_get.return_value.json.side_effect = [
        [{"code": "ecs", "defaultVersion": "2014-05-26"}],  # for get_service_version
        {"apis": {"DescribeInstances": {}, "StartInstance": {}}}  # for get_response_from_pop_api
    ]
    apis = api_meta_client.ApiMetaClient.get_apis_in_service('ecs')
    assert set(apis) == {"DescribeInstances", "StartInstance"}
    assert len(apis) == 2


@patch('alibaba_cloud_ops_mcp_server.alibabacloud.api_meta_client.ApiMetaClient.get_standard_service_and_api', return_value=('ecs', 'api'))
@patch('alibaba_cloud_ops_mcp_server.alibabacloud.api_meta_client.ApiMetaClient.get_response_from_pop_api')
def test_get_ref_api_meta_invalid_path(mock_pop_api, mock_std):
    # 模拟 ref_path 指向不存在的 key
    mock_pop_api.return_value = {'apis': {'DescribeInstances': {}}}
    with pytest.raises(KeyError):
        api_meta_client.ApiMetaClient.get_ref_api_meta({'$ref': '#/notfound'}, 'ecs', '2014-05-26')

@patch('alibaba_cloud_ops_mcp_server.alibabacloud.api_meta_client.ApiMetaClient.get_standard_service_and_api', return_value=('ecs', 'api'))
@patch('alibaba_cloud_ops_mcp_server.alibabacloud.api_meta_client.ApiMetaClient.get_response_from_pop_api')
def test_get_ref_api_meta_invalid_path(mock_pop_api, mock_std):
    # 模拟 ref_path 指向不存在的 key
    mock_pop_api.return_value = {'apis': {'DescribeInstances': {}}}
    with pytest.raises(KeyError):
        api_meta_client.ApiMetaClient.get_ref_api_meta({'$ref': '#/notfound'}, 'ecs', '2014-05-26')

@patch('alibaba_cloud_ops_mcp_server.alibabacloud.api_meta_client.ApiMetaClient.get_api_meta')
def test_get_api_field_default_value(mock_get_meta):
    # 模拟 get_api_meta 返回无 field_type 的数据
    mock_get_meta.return_value = ({}, '2014-05-26')
    val = api_meta_client.ApiMetaClient.get_api_field('parameters', 'ecs', 'DescribeInstances', default='default_val')
    assert val == 'default_val'

@patch('alibaba_cloud_ops_mcp_server.alibabacloud.api_meta_client.ApiMetaClient.get_api_meta')
def test_get_api_parameters_nested_ref(mock_get_meta):
    # 模拟嵌套 $ref
    api_meta = {
        'parameters': [
            {'name': 'foo', 'in': 'query', 'schema': {'$ref': '#/defs/A'}}
        ]
    }
    def fake_get_ref(data, service, version):
        if '#/defs/A' in data.get('$ref', ''):
            return {'properties': {'a': {'$ref': '#/defs/B'}}}
        elif '#/defs/B' in data.get('$ref', ''):
            return {'properties': {'b': {}}}
        return {}
    with patch.object(api_meta_client.ApiMetaClient, 'get_ref_api_meta', side_effect=fake_get_ref):
        mock_get_meta.return_value = (api_meta, '2014-05-26')
        params = api_meta_client.ApiMetaClient.get_api_parameters('ecs', 'DescribeInstances')
        assert 'a' in params and 'b' in params  # 深层嵌套属性应被提取

@patch('alibaba_cloud_ops_mcp_server.alibabacloud.api_meta_client.ApiMetaClient.get_standard_service_and_api', return_value=('ecs', 'api'))
@patch('alibaba_cloud_ops_mcp_server.alibabacloud.api_meta_client.ApiMetaClient.get_response_from_pop_api')
def test_get_ref_api_meta_valid_path(mock_pop_api, mock_std):
    # 模拟 get_response_from_pop_api 返回包含 defs/A 的结构
    mock_pop_api.return_value = {
        'defs': {
            'A': {
                'properties': {
                    'prop1': {'type': 'string'},
                    'prop2': {'type': 'integer'}
                }
            }
        }
    }

    # 调用 get_ref_api_meta，传入 $ref 指向 #/defs/A
    result = api_meta_client.ApiMetaClient.get_ref_api_meta({'$ref': '#/defs/A'}, 'ecs', '2014-05-26')

    # 验证返回结果是否与 defs/A 的结构一致
    expected = {
        'properties': {
            'prop1': {'type': 'string'},
            'prop2': {'type': 'integer'}
        }
    }
    assert result == expected

@patch('alibaba_cloud_ops_mcp_server.alibabacloud.api_meta_client.requests.get')
def test_get_all_service_info(mock_get):
    mock_get.return_value.json.return_value = [
        {"code": "ecs", "name": "Elastic Compute Service"},
        {"code": "rds", "name": "Relational Database Service"}
    ]
    result = api_meta_client.ApiMetaClient.get_all_service_info()
    assert result == [
        {"code": "ecs", "name": "Elastic Compute Service"},
        {"code": "rds", "name": "Relational Database Service"}
    ]



@patch('alibaba_cloud_ops_mcp_server.alibabacloud.api_meta_client.ApiMetaClient.get_service_version', return_value='2014-05-26')
@patch('alibaba_cloud_ops_mcp_server.alibabacloud.api_meta_client.ApiMetaClient.get_standard_service_and_api', return_value=('ecs', 'DescribeInstances'))
@patch('alibaba_cloud_ops_mcp_server.alibabacloud.api_meta_client.ApiMetaClient.get_response_from_pop_api')
def test_get_api_meta_success(mock_pop_api, mock_get_std, mock_get_ver):
    """测试get_api_meta方法的正常成功路径，覆盖第90-91行"""
    # 模拟get_response_from_pop_api返回的API元数据
    mock_api_data = {
        'parameters': [
            {'name': 'InstanceIds', 'in': 'query', 'schema': {'type': 'string'}}
        ],
        'responses': {
            '200': {
                'schema': {
                    'properties': {
                        'Instances': {'type': 'array'}
                    }
                }
            }
        }
    }
    mock_pop_api.return_value = mock_api_data
    
    # 调用get_api_meta
    data, version = api_meta_client.ApiMetaClient.get_api_meta('ecs', 'DescribeInstances')
    
    # 验证返回值
    assert data == mock_api_data
    assert version == '2014-05-26'
    
    # 验证调用了正确的方法
    mock_get_ver.assert_called_once_with('ecs')
    mock_get_std.assert_called_once_with('ecs', 'DescribeInstances', '2014-05-26')
    mock_pop_api.assert_called_once_with(
        api_meta_client.ApiMetaClient.GET_API_INFO, 
        'ecs', 
        'DescribeInstances', 
        '2014-05-26'
    )
