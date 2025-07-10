import logging

from alibabacloud_credentials.client import Client as CredClient
from alibabacloud_tea_openapi.models import Config
from fastmcp.server.dependencies import get_http_request
from alibaba_cloud_ops_mcp_server.settings import settings

logger = logging.getLogger(__name__)


def get_credentials_from_header():
    credentials = None
    try:
        request = get_http_request()
        headers = request.headers
        access_key_id = headers.get('x-acs-accesskey-id', None)
        access_key_secret = headers.get('x-acs-accesskey-secret', None)
        token = headers.get('x-acs-security-token', None)

        if access_key_id:
            credentials = {
                'AccessKeyId': access_key_id,
                'AccessKeySecret': access_key_secret,
                'SecurityToken': token
            }

    except Exception as e:
        logger.info(f'get_credentials_from_header error: {e}')
    return credentials


def create_config():
    credentials = get_credentials_from_header()

    if credentials:
        access_key_id = credentials.get('AccessKeyId')
        access_key_secret = credentials.get('AccessKeySecret')
        token = credentials.get('SecurityToken')
        config = Config(
            access_key_id=access_key_id,
            access_key_secret=access_key_secret,
            security_token=token
        )
    elif settings.headers_credential_only:
        config = Config()
    else:
        credentials_client = CredClient()
        config = Config(credential=credentials_client)

    config.user_agent = 'alibaba-cloud-ops-mcp-server'
    return config
