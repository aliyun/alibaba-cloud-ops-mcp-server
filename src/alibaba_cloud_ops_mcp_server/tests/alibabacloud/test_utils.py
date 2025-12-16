from unittest.mock import patch, MagicMock
from alibaba_cloud_ops_mcp_server.alibabacloud import utils

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