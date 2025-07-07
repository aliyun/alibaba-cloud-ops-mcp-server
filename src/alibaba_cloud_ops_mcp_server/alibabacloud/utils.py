import logging

from alibabacloud_credentials.client import Client as CredClient
from alibabacloud_tea_openapi.models import Config
from fastmcp.server.dependencies import get_http_request

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


def log_args_and_return(func):
    def wrapper(*args, **kwargs):
        logger.info(f"Calling {func.__name__} with args: {args}, kwargs: {kwargs}")
        result = func(*args, **kwargs)
        logger.info(f"{func.__name__} returned: {result}")
        return result
    return wrapper
