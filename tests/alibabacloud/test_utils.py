from unittest.mock import patch, MagicMock
from alibaba_cloud_ops_mcp_server.alibabacloud import utils
import tempfile
import os
import json

def test_create_config():
    with patch('alibaba_cloud_ops_mcp_server.alibabacloud.utils.CredClient') as mock_cred, \
         patch('alibaba_cloud_ops_mcp_server.alibabacloud.utils.Config') as mock_cfg:
        cred = MagicMock()
        mock_cred.return_value = cred
        cfg = MagicMock()
        mock_cfg.return_value = cfg
        result = utils.create_config()
        assert result is cfg
        assert cfg.user_agent == 'alibaba-cloud-ops-mcp-server'
        mock_cred.assert_called_once()
        mock_cfg.assert_called_once_with(credential=cred)

def test_get_credentials_from_header_success():
    """测试从header成功获取凭证的情况"""
    with patch('alibaba_cloud_ops_mcp_server.alibabacloud.utils.get_http_request') as mock_get_request:
        mock_request = MagicMock()
        mock_request.headers = {
            'x-acs-accesskey-id': 'test_id',
            'x-acs-accesskey-secret': 'test_secret',
            'x-acs-security-token': 'test_token'
        }
        mock_get_request.return_value = mock_request
        
        result = utils.get_credentials_from_header()
        expected = {
            'AccessKeyId': 'test_id',
            'AccessKeySecret': 'test_secret',
            'SecurityToken': 'test_token'
        }
        assert result == expected

def test_get_credentials_from_header_no_access_key():
    """测试header中没有access_key_id的情况"""
    with patch('alibaba_cloud_ops_mcp_server.alibabacloud.utils.get_http_request') as mock_get_request:
        mock_request = MagicMock()
        mock_request.headers = {}
        mock_get_request.return_value = mock_request
        
        result = utils.get_credentials_from_header()
        assert result is None

def test_get_credentials_from_header_exception():
    """测试get_http_request抛出异常的情况"""
    with patch('alibaba_cloud_ops_mcp_server.alibabacloud.utils.get_http_request') as mock_get_request, \
         patch('alibaba_cloud_ops_mcp_server.alibabacloud.utils.logger') as mock_logger:
        mock_get_request.side_effect = Exception('test error')
        
        result = utils.get_credentials_from_header()
        assert result is None
        mock_logger.info.assert_called_once_with('get_credentials_from_header error: test error')

def test_create_config_with_credentials():
    """测试使用header中的凭证创建config的情况"""
    with patch('alibaba_cloud_ops_mcp_server.alibabacloud.utils.get_credentials_from_header') as mock_get_creds, \
         patch('alibaba_cloud_ops_mcp_server.alibabacloud.utils.Config') as mock_cfg:
        mock_get_creds.return_value = {
            'AccessKeyId': 'test_id',
            'AccessKeySecret': 'test_secret',
            'SecurityToken': 'test_token'
        }
        cfg = MagicMock()
        mock_cfg.return_value = cfg
        
        result = utils.create_config()
        assert result is cfg
        assert cfg.user_agent == 'alibaba-cloud-ops-mcp-server'
        mock_cfg.assert_called_once_with(
            access_key_id='test_id',
            access_key_secret='test_secret',
            security_token='test_token'
        ) 


def test_create_config_headers_credential_only():
    """测试 headers_credential_only 模式"""
    with patch('alibaba_cloud_ops_mcp_server.alibabacloud.utils.get_credentials_from_header') as mock_get_creds, \
         patch('alibaba_cloud_ops_mcp_server.alibabacloud.utils.Config') as mock_cfg, \
         patch('alibaba_cloud_ops_mcp_server.alibabacloud.utils.settings') as mock_settings:
        mock_get_creds.return_value = None
        mock_settings.headers_credential_only = True
        cfg = MagicMock()
        mock_cfg.return_value = cfg
        
        result = utils.create_config()
        assert result is cfg
        mock_cfg.assert_called_once_with()


def test_set_project_path():
    """测试设置项目路径"""
    from pathlib import Path
    with tempfile.TemporaryDirectory() as tmpdir:
        utils.set_project_path(tmpdir)
        assert utils._project_path is not None
        # 解决 /var -> /private/var 符号链接问题
        assert utils._project_path.resolve() == Path(tmpdir).resolve()
        
        # 重置
        utils.set_project_path(None)
        assert utils._project_path is None


def test_get_code_deploy_base_dir_with_project_path():
    """测试获取 code_deploy 目录（有项目路径时）"""
    from pathlib import Path
    with tempfile.TemporaryDirectory() as tmpdir:
        utils.set_project_path(tmpdir)
        base_dir = utils._get_code_deploy_base_dir()
        # 解决 /var -> /private/var 符号链接问题
        expected = Path(tmpdir).resolve() / '.code_deploy'
        assert base_dir.resolve() == expected
        utils.set_project_path(None)


def test_get_code_deploy_base_dir_without_project_path():
    """测试获取 code_deploy 目录（无项目路径时）"""
    utils.set_project_path(None)
    base_dir = utils._get_code_deploy_base_dir()
    assert '.code_deploy' in str(base_dir)


def test_ensure_code_deploy_dirs():
    """测试确保 code_deploy 目录存在"""
    with tempfile.TemporaryDirectory() as tmpdir:
        utils.set_project_path(tmpdir)
        code_deploy_dir, _, release_dir = utils.ensure_code_deploy_dirs()
        assert code_deploy_dir.exists()
        assert release_dir.exists()
        utils.set_project_path(None)


def test_load_application_info_not_exists():
    """测试加载不存在的 application info"""
    with tempfile.TemporaryDirectory() as tmpdir:
        utils.set_project_path(tmpdir)
        result = utils.load_application_info()
        assert result == {}
        utils.set_project_path(None)


def test_load_application_info_exists():
    """测试加载存在的 application info"""
    with tempfile.TemporaryDirectory() as tmpdir:
        utils.set_project_path(tmpdir)
        
        # 创建 .code_deploy 目录和 application.json
        code_deploy_dir = os.path.join(tmpdir, '.code_deploy')
        os.makedirs(code_deploy_dir, exist_ok=True)
        app_json_path = os.path.join(code_deploy_dir, 'application.json')
        
        test_data = {'app_name': 'test', 'version': '1.0'}
        with open(app_json_path, 'w') as f:
            json.dump(test_data, f)
        
        result = utils.load_application_info()
        assert result == test_data
        utils.set_project_path(None)


def test_save_application_info():
    """测试保存 application info"""
    with tempfile.TemporaryDirectory() as tmpdir:
        utils.set_project_path(tmpdir)
        
        test_data = {'app_name': 'test', 'version': '2.0'}
        utils.save_application_info(test_data)
        
        # 验证保存的内容
        result = utils.load_application_info()
        assert result['app_name'] == 'test'
        assert result['version'] == '2.0'
        utils.set_project_path(None)


def test_get_release_path():
    """测试获取 release 路径"""
    with tempfile.TemporaryDirectory() as tmpdir:
        utils.set_project_path(tmpdir)
        
        release_path = utils.get_release_path('test_file.tar.gz')
        assert 'release' in str(release_path)
        assert 'test_file.tar.gz' in str(release_path)
        utils.set_project_path(None)


def test_create_client():
    """测试创建 OOS 客户端"""
    with patch('alibaba_cloud_ops_mcp_server.alibabacloud.utils.create_config') as mock_create_config, \
         patch('alibaba_cloud_ops_mcp_server.alibabacloud.utils.oos20190601Client') as mock_client:
        mock_config = MagicMock()
        mock_create_config.return_value = mock_config
        mock_client_instance = MagicMock()
        mock_client.return_value = mock_client_instance
        
        result = utils.create_client('cn-hangzhou')
        assert result is mock_client_instance
        assert mock_config.endpoint == 'oos.cn-hangzhou.aliyuncs.com'


def test_create_ecs_client():
    """测试创建 ECS 客户端"""
    with patch('alibaba_cloud_ops_mcp_server.alibabacloud.utils.create_config') as mock_create_config, \
         patch('alibaba_cloud_ops_mcp_server.alibabacloud.utils.ecs20140526Client') as mock_client:
        mock_config = MagicMock()
        mock_create_config.return_value = mock_config
        mock_client_instance = MagicMock()
        mock_client.return_value = mock_client_instance
        
        result = utils.create_ecs_client('cn-beijing')
        assert result is mock_client_instance
        assert mock_config.endpoint == 'ecs.cn-beijing.aliyuncs.com'


def test_put_bucket_tagging():
    """测试给 bucket 打标签"""
    mock_client = MagicMock()
    
    utils.put_bucket_tagging(mock_client, 'test-bucket', {'key1': 'value1', 'key2': 'value2'})
    
    mock_client.put_bucket_tags.assert_called_once()


def test_find_bucket_by_tag_found():
    """测试通过标签找到 bucket"""
    mock_client = MagicMock()
    mock_paginator = MagicMock()
    mock_page = MagicMock()
    mock_bucket = MagicMock()
    mock_bucket.name = 'found-bucket'
    mock_page.buckets = [mock_bucket]
    mock_paginator.iter_page.return_value = [mock_page]
    mock_client.list_buckets_paginator.return_value = mock_paginator
    
    result = utils.find_bucket_by_tag(mock_client, 'tag_key', 'tag_value')
    assert result == 'found-bucket'


def test_find_bucket_by_tag_not_found():
    """测试通过标签未找到 bucket"""
    mock_client = MagicMock()
    mock_paginator = MagicMock()
    mock_page = MagicMock()
    mock_page.buckets = None
    mock_paginator.iter_page.return_value = [mock_page]
    mock_client.list_buckets_paginator.return_value = mock_paginator
    
    result = utils.find_bucket_by_tag(mock_client, 'tag_key', 'tag_value')
    assert result is None


def test_find_bucket_by_tag_exception():
    """测试查找 bucket 时发生异常"""
    mock_client = MagicMock()
    mock_paginator = MagicMock()
    mock_paginator.iter_page.side_effect = Exception('test error')
    mock_client.list_buckets_paginator.return_value = mock_paginator
    
    result = utils.find_bucket_by_tag(mock_client, 'tag_key', 'tag_value')
    assert result is None


def test_get_or_create_bucket_for_code_deploy_existing():
    """测试获取已存在的 bucket"""
    with patch('alibaba_cloud_ops_mcp_server.alibabacloud.utils.create_oss_client') as mock_create_client, \
         patch('alibaba_cloud_ops_mcp_server.alibabacloud.utils.find_bucket_by_tag') as mock_find:
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client
        mock_find.return_value = 'existing-bucket'
        
        result = utils.get_or_create_bucket_for_code_deploy('test-app')
        assert result == 'existing-bucket'


def test_get_or_create_bucket_for_code_deploy_create_new():
    """测试创建新 bucket"""
    with patch('alibaba_cloud_ops_mcp_server.alibabacloud.utils.create_oss_client') as mock_create_client, \
         patch('alibaba_cloud_ops_mcp_server.alibabacloud.utils.find_bucket_by_tag') as mock_find, \
         patch('alibaba_cloud_ops_mcp_server.alibabacloud.utils.put_bucket_tagging') as mock_tag:
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client
        mock_find.return_value = None
        
        result = utils.get_or_create_bucket_for_code_deploy('test-app')
        assert result.startswith('code-deploy-')
        mock_client.put_bucket.assert_called_once()
        mock_tag.assert_called_once() 