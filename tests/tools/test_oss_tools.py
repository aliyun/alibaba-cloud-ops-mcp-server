import pytest
from unittest.mock import patch, MagicMock
from alibaba_cloud_ops_mcp_server.tools import oss_tools

def get_tool_func(name):
    return [f for f in oss_tools.tools if f.__name__ == name][0]

def fake_client(*args, **kwargs):
    class FakePaginator:
        def iter_page(self, req):
            class Page:
                buckets = [MagicMock(__str__=lambda self: 'bucket1')]
                contents = [MagicMock(__str__=lambda self: 'obj1')]
            yield Page()
    class FakeClient:
        def list_buckets_paginator(self):
            return FakePaginator()
        def list_objects_v2_paginator(self):
            return FakePaginator()
        def put_bucket(self, req):
            return MagicMock(__str__=lambda self: 'put_bucket')
        def delete_bucket(self, req):
            return MagicMock(__str__=lambda self: 'delete_bucket')
    return FakeClient()

@patch('alibaba_cloud_ops_mcp_server.tools.oss_tools.create_client', fake_client)
def test_OSS_ListBuckets():
    func = get_tool_func("OSS_ListBuckets")
    result = func(RegionId='cn-test', Prefix='prefix')
    assert result == ['bucket1']

@patch('alibaba_cloud_ops_mcp_server.tools.oss_tools.create_client', fake_client)
def test_OSS_ListObjects():
    func = get_tool_func("OSS_ListObjects")
    result = func(RegionId='cn-test', BucketName='bucket', Prefix='prefix')
    assert result == ['obj1']

@patch('alibaba_cloud_ops_mcp_server.tools.oss_tools.create_client', fake_client)
def test_OSS_ListObjects_no_bucket():
    func = get_tool_func("OSS_ListObjects")
    with pytest.raises(ValueError):
        func(RegionId='cn-test', BucketName='', Prefix='prefix')

@patch('alibaba_cloud_ops_mcp_server.tools.oss_tools.create_client', fake_client)
def test_OSS_PutBucket():
    func = get_tool_func("OSS_PutBucket")
    result = func(RegionId='cn-test', BucketName='bucket')
    assert result == 'put_bucket'

@patch('alibaba_cloud_ops_mcp_server.tools.oss_tools.create_client', fake_client)
def test_OSS_DeleteBucket():
    func = get_tool_func("OSS_DeleteBucket")
    result = func(RegionId='cn-test', BucketName='bucket')
    assert result == 'delete_bucket'

# 新增底层构造相关测试
@patch('alibaba_cloud_ops_mcp_server.tools.oss_tools.CredClient')
def test_CredentialsProvider_and_get_credentials(mock_cred_client):
    # mock credentials client返回的credential对象
    cred = MagicMock()
    cred.access_key_id = 'id'
    cred.access_key_secret = 'secret'
    cred.security_token = 'token'
    mock_cred_client.return_value.get_credential.return_value = cred
    provider = oss_tools.CredentialsProvider()
    credentials = provider.get_credentials()
    assert credentials.access_key_id == 'id'
    assert credentials.access_key_secret == 'secret'
    assert credentials.security_token == 'token'

@patch('alibaba_cloud_ops_mcp_server.alibabacloud.utils.get_credentials_from_header')
def test_CredentialsProvider_with_header_credentials(mock_get_creds):
    """测试从header获取凭证的CredentialsProvider"""
    mock_get_creds.return_value = {
        'AccessKeyId': 'header_id',
        'AccessKeySecret': 'header_secret',
        'SecurityToken': 'header_token'
    }
    provider = oss_tools.CredentialsProvider()
    credentials = provider.get_credentials()
    assert credentials.access_key_id == 'header_id'
    assert credentials.access_key_secret == 'header_secret'
    assert credentials.security_token == 'header_token'

@patch('alibaba_cloud_ops_mcp_server.tools.oss_tools.CredentialsProvider')
@patch('alibaba_cloud_ops_mcp_server.tools.oss_tools.oss')
def test_create_client(mock_oss, mock_provider):
    # mock config和Client
    mock_cfg = MagicMock()
    mock_oss.config.load_default.return_value = mock_cfg
    mock_client = MagicMock()
    mock_oss.Client.return_value = mock_client
    mock_provider.return_value = MagicMock()
    client = oss_tools.create_client('cn-test')
    assert client is mock_client
    assert mock_cfg.user_agent == 'alibaba-cloud-ops-mcp-server'
    assert mock_cfg.region == 'cn-test'
    assert mock_cfg.credentials_provider == mock_provider.return_value 


@patch('alibaba_cloud_ops_mcp_server.tools.oss_tools.create_client')
def test_OSS_PutObject_success(mock_create_client):
    """测试 OSS_PutObject 成功上传"""
    import tempfile
    import os
    
    # 创建临时文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write('test content')
        temp_file = f.name
    
    try:
        # mock client
        mock_client = MagicMock()
        mock_result = MagicMock()
        mock_result.status_code = 200
        mock_result.etag = 'test-etag'
        mock_result.version_id = 'v1'
        mock_client.put_object.return_value = mock_result
        mock_create_client.return_value = mock_client
        
        result = oss_tools.OSS_PutObject(
            BucketName='test-bucket',
            ObjectKey='test/file.txt',
            FilePath=temp_file,
            RegionId='cn-hangzhou',
            ContentType=None
        )
        
        assert result['status_code'] == 200
        assert result['etag'] == 'test-etag'
        assert 'Successfully uploaded' in result['message']
    finally:
        os.unlink(temp_file)


@patch('alibaba_cloud_ops_mcp_server.tools.oss_tools.create_client')
def test_OSS_PutObject_missing_bucket(mock_create_client):
    """测试 OSS_PutObject 缺少 BucketName"""
    with pytest.raises(ValueError, match="Bucket name is required"):
        oss_tools.OSS_PutObject(
            BucketName='',
            ObjectKey='test/file.txt',
            FilePath='/tmp/test.txt',
            RegionId='cn-hangzhou'
        )


@patch('alibaba_cloud_ops_mcp_server.tools.oss_tools.create_client')
def test_OSS_PutObject_missing_object_key(mock_create_client):
    """测试 OSS_PutObject 缺少 ObjectKey"""
    with pytest.raises(ValueError, match="Object key is required"):
        oss_tools.OSS_PutObject(
            BucketName='test-bucket',
            ObjectKey='',
            FilePath='/tmp/test.txt',
            RegionId='cn-hangzhou'
        )


@patch('alibaba_cloud_ops_mcp_server.tools.oss_tools.create_client')
def test_OSS_PutObject_missing_file_path(mock_create_client):
    """测试 OSS_PutObject 缺少 FilePath"""
    with pytest.raises(ValueError, match="File path is required"):
        oss_tools.OSS_PutObject(
            BucketName='test-bucket',
            ObjectKey='test/file.txt',
            FilePath='',
            RegionId='cn-hangzhou'
        )


@patch('alibaba_cloud_ops_mcp_server.tools.oss_tools.create_client')
def test_OSS_PutObject_file_not_found(mock_create_client):
    """测试 OSS_PutObject 文件不存在"""
    with pytest.raises(FileNotFoundError, match="File not found"):
        oss_tools.OSS_PutObject(
            BucketName='test-bucket',
            ObjectKey='test/file.txt',
            FilePath='/nonexistent/file.txt',
            RegionId='cn-hangzhou'
        )


@patch('alibaba_cloud_ops_mcp_server.tools.oss_tools.create_client')
def test_OSS_PutObject_path_is_directory(mock_create_client):
    """测试 OSS_PutObject 路径是目录"""
    import tempfile
    
    with tempfile.TemporaryDirectory() as tmpdir:
        with pytest.raises(ValueError, match="Path is not a file"):
            oss_tools.OSS_PutObject(
                BucketName='test-bucket',
                ObjectKey='test/file.txt',
                FilePath=tmpdir,
                RegionId='cn-hangzhou'
            )


@patch('alibaba_cloud_ops_mcp_server.tools.oss_tools.create_client')
def test_OSS_PutObject_with_content_type(mock_create_client):
    """测试 OSS_PutObject 指定 ContentType"""
    import tempfile
    import os
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        f.write('{"test": "data"}')
        temp_file = f.name
    
    try:
        mock_client = MagicMock()
        mock_result = MagicMock()
        mock_result.status_code = 200
        mock_result.etag = 'test-etag'
        mock_result.version_id = None
        mock_client.put_object.return_value = mock_result
        mock_create_client.return_value = mock_client
        
        result = oss_tools.OSS_PutObject(
            BucketName='test-bucket',
            ObjectKey='test/data.json',
            FilePath=temp_file,
            RegionId='cn-hangzhou',
            ContentType='application/json'
        )
        
        assert result['content_type'] == 'application/json'
    finally:
        os.unlink(temp_file)


@patch('alibaba_cloud_ops_mcp_server.tools.oss_tools.create_client')
def test_OSS_PutObject_infer_content_type(mock_create_client):
    """测试 OSS_PutObject 自动推断 ContentType"""
    import tempfile
    import os
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
        f.write('<html></html>')
        temp_file = f.name
    
    try:
        mock_client = MagicMock()
        mock_result = MagicMock()
        mock_result.status_code = 200
        mock_result.etag = 'test-etag'
        mock_result.version_id = None
        mock_client.put_object.return_value = mock_result
        mock_create_client.return_value = mock_client
        
        result = oss_tools.OSS_PutObject(
            BucketName='test-bucket',
            ObjectKey='test/page.html',
            FilePath=temp_file,
            RegionId='cn-hangzhou',
            ContentType=None
        )
        
        # html 文件应该被识别为 text/html
        assert 'text/html' in result['content_type']
    finally:
        os.unlink(temp_file)