from alibabacloud_credentials.client import Client as CredClient
from alibabacloud_tea_openapi.models import Config
from fastmcp.server.dependencies import get_http_request


def get_credentials_from_header():
    request = get_http_request()
    headers = request.headers
    access_key_id = headers.get('x-ak-proven-access-key-id', None)
    access_key_secret = headers.get('x-ak-proven-access-key-secret', None)
    token = headers.get('x-acs-ak-proven', None)
    credentials = None
    if access_key_id:
        credentials = {
            'AccessKeyId': access_key_id,
            'AccessKeySecret': access_key_secret,
            'SecurityToken': token
        }
    return credentials


def create_config():
    credentials = get_credentials_from_header()
    if credentials:
        access_key_id = credentials.get('AccessKeyId', None)
        access_key_secret = credentials.get('AccessKeySecret', None)
        token = credentials.get('SecurityToken', None)
        config = Config(
            access_key_id=access_key_id,
            access_key_secret=access_key_secret,
            security_token=token
        )
    else:
        credentialsClient = CredClient()
        config = Config(credential=credentialsClient)
    config.user_agent = 'alibaba-cloud-ops-mcp-server'
    return config
