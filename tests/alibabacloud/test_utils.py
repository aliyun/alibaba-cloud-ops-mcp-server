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

def test_create_config_with_credentials_from_header():
    with patch('alibaba_cloud_ops_mcp_server.alibabacloud.utils.get_http_request') as mock_request, \
         patch('alibaba_cloud_ops_mcp_server.alibabacloud.utils.Config') as mock_cfg:
        mock_request.return_value.headers = {
            'x-ak-proven-access-key-id': 'test_id',
            'x-ak-proven-access-key-secret': 'test_secret',
            'x-acs-ak-proven': 'test_token'
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


def test_get_credentials_from_header_with_all_headers():
    with patch('alibaba_cloud_ops_mcp_server.alibabacloud.utils.get_http_request') as mock_request:
        mock_request.return_value.headers = {
            'x-ak-proven-access-key-id': 'test_id',
            'x-ak-proven-access-key-secret': 'test_secret',
            'x-acs-ak-proven': 'test_token'
        }
        credentials = utils.get_credentials_from_header()
        assert credentials == {
            'AccessKeyId': 'test_id',
            'AccessKeySecret': 'test_secret',
            'SecurityToken': 'test_token'
        }
