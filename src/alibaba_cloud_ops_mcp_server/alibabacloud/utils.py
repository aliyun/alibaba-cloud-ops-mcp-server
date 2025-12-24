import logging
import logging
import json
import uuid
from pathlib import Path
from typing import Dict, Any, Optional

from alibabacloud_oos20190601.client import Client as oos20190601Client
from alibabacloud_ecs20140526.client import Client as ecs20140526Client
from alibaba_cloud_ops_mcp_server.tools.oss_tools import create_client as create_oss_client
import alibabacloud_oss_v2 as oss

logger = logging.getLogger(__name__)

# Global variable to store the project path
_project_path: Optional[Path] = None
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


def set_project_path(project_path: Optional[str] = None):
    """
    Set the project root path for code deployment.
    This determines where the .code_deploy directory will be created.

    Args:
        project_path: The root path of the project. If None, will use current working directory.
    """
    global _project_path
    if project_path:
        _project_path = Path(project_path).resolve()
        logger.info(f"[set_project_path] Project path set to: {_project_path}")
    else:
        _project_path = None
        logger.info(f"[set_project_path] Project path reset to None, will use current working directory")


def _get_code_deploy_base_dir() -> Path:
    """
    Get the .code_deploy base directory in the project root directory.
    This ensures each project has its own isolated deployment configuration.

    If project_path is set, use it. Otherwise, use current working directory.
    """
    if _project_path is not None:
        return _project_path / '.code_deploy'
    return Path.cwd() / '.code_deploy'


CODE_DEPLOY_BASE_DIR = _get_code_deploy_base_dir()
CODE_DEPLOY_DIR = CODE_DEPLOY_BASE_DIR
RELEASE_DIR = CODE_DEPLOY_DIR / 'release'
APPLICATION_JSON_FILE = CODE_DEPLOY_DIR / 'application.json'


def ensure_code_deploy_dirs():
    """
    Ensure that the .code_deploy and release directories exist (in the project root directory)
    """
    # Recalculate paths to ensure we use the current working directory
    code_deploy_dir = _get_code_deploy_base_dir()
    release_dir = code_deploy_dir / 'release'

    code_deploy_dir.mkdir(parents=True, exist_ok=True)
    release_dir.mkdir(parents=True, exist_ok=True)

    return code_deploy_dir, code_deploy_dir, release_dir


def load_application_info() -> Dict[str, Any]:
    """
    Load deployment information from the .application.json file
    (from the .code_deploy directory under the project root directory)
    """
    json_file = _get_code_deploy_base_dir() / 'application.json'

    if json_file.exists():
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"[_load_application_info] Failed to load application info: {e}")
            return {}
    return {}


def save_application_info(info: Dict[str, Any]):
    """
    Save deployment information to the .application.json file
    (save it to the .code_deploy directory under the project root directory)
    """
    json_file = _get_code_deploy_base_dir() / 'application.json'

    try:
        json_file.parent.mkdir(parents=True, exist_ok=True)

        existing_info = load_application_info()
        existing_info.update(info)

        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(existing_info, f, ensure_ascii=False, indent=2)
        logger.info(f"[_save_application_info] Saved application info to {json_file}")
    except Exception as e:
        logger.error(f"[_save_application_info] Failed to save application info: {e}")


def get_release_path(filename: str) -> Path:
    """
    Get the file path in the release directory
    (the .code_deploy/release directory under the project root directory)
    """
    release_dir = _get_code_deploy_base_dir() / 'release'
    release_dir.mkdir(parents=True, exist_ok=True)
    return release_dir / filename


def create_client(region_id: str) -> oos20190601Client:
    config = create_config()
    config.endpoint = f'oos.{region_id}.aliyuncs.com'
    return oos20190601Client(config)


def create_ecs_client(region_id: str) -> ecs20140526Client:
    config = create_config()
    config.endpoint = f'ecs.{region_id}.aliyuncs.com'
    return ecs20140526Client(config)


def put_bucket_tagging(client: oss.Client, bucket_name: str, tags: dict):
    tag_list = [oss.Tag(key=k, value=v) for k, v in tags.items()]
    tag_set = oss.TagSet(tags=tag_list)
    client.put_bucket_tags(oss.PutBucketTagsRequest(
        bucket=bucket_name,
        tagging=oss.Tagging(tag_set=tag_set)
    ))


def find_bucket_by_tag(client: oss.Client, tag_key: str, tag_value: str) -> Optional[str]:
    paginator = client.list_buckets_paginator(tag_key=tag_key, tag_value=tag_value)
    buckets = []
    try:
        for page in paginator.iter_page(oss.ListBucketsRequest(tag_key=tag_key, tag_value=tag_value)):
            if not page.buckets:
                continue
            for bucket in page.buckets:
                buckets.append(bucket.name)
        logger.info(f'[code_deploy] Trying to find bucket with tag {tag_key}:{tag_value}, buckets: {buckets}')
    except Exception as e:
        logger.error(f'[code_deploy] Failed to list buckets: {e}')
    return buckets[0] if buckets else None


def get_or_create_bucket_for_code_deploy(application_name: str) -> str:
    """
    Obtain or create an OSS bucket for code deployment

    1. If a bucket_name is provided, check if it exists. If not, create it and tag it.

    2. If not provided, search for an existing bucket using the tag (key: app_management, value: code_deploy).

    3. If found, use it. If not found, create a new bucket and tag it.

    4. New bucket naming convention: app-{application_name}-code-deploy-{uuid}
    """
    tag_key = 'app_management'
    tag_value = 'code_deploy'
    client = create_oss_client(region_id='cn-hangzhou')

    found_bucket = find_bucket_by_tag(client, tag_key, tag_value)
    if found_bucket:
        logger.info(f"[code_deploy] Found existing bucket by tag: {found_bucket}")
        return found_bucket

    bucket_name = f'code-deploy-{str(uuid.uuid4())[:8]}'

    try:
        client.put_bucket(oss.PutBucketRequest(
            bucket=bucket_name,
            create_bucket_configuration=oss.CreateBucketConfiguration(
                storage_class='Standard',
                data_redundancy_type='LRS'
            )
        ))
        put_bucket_tagging(client, bucket_name, {tag_key: tag_value})
        logger.info(f"[code_deploy] Created new bucket: {bucket_name}")
        return bucket_name
    except oss.exceptions.OperationError as e:
        logger.info(f"[code_deploy] OperationError Failed to create bucket: {e}")
        raise e
    except Exception as e:
        logger.info(f"[code_deploy] Failed to create bucket: {e}")
        raise e
