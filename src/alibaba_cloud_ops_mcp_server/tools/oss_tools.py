import os
import mimetypes
import logging
import json
import alibabacloud_oss_v2 as oss

from pydantic import Field
from alibabacloud_oss_v2 import Credentials
from alibabacloud_oss_v2.credentials import EnvironmentVariableCredentialsProvider
from alibabacloud_credentials.client import Client as CredClient

tools = []


logger = logging.getLogger(__name__)


class CredentialsProvider(EnvironmentVariableCredentialsProvider):
    def __init__(self) -> None:
        from alibaba_cloud_ops_mcp_server.alibabacloud.utils import get_credentials_from_header
        credentials = get_credentials_from_header()
        if credentials:
            access_key_id = credentials.get('AccessKeyId', None)
            access_key_secret = credentials.get('AccessKeySecret', None)
            session_token = credentials.get('SecurityToken', None)
        else:
            credentialsClient = CredClient()
            access_key_id = credentialsClient.get_credential().access_key_id
            access_key_secret = credentialsClient.get_credential().access_key_secret
            session_token = credentialsClient.get_credential().security_token

        self._credentials = Credentials(
            access_key_id, access_key_secret, session_token)

    def get_credentials(self) -> Credentials:
        return self._credentials


def create_client(region_id: str) -> oss.Client:
    credentials_provider = CredentialsProvider()
    cfg = oss.config.load_default()
    cfg.user_agent = 'alibaba-cloud-ops-mcp-server'
    cfg.credentials_provider = credentials_provider
    cfg.region = region_id
    return oss.Client(cfg)


@tools.append
def OSS_ListBuckets(
    RegionId: str = Field(description='AlibabaCloud region ID', default='cn-hangzhou'),
    Prefix: str = Field(description='AlibabaCloud OSS Bucket Name prefix', default=None)
):
    """列出指定区域的所有OSS存储空间。"""
    client = create_client(region_id=RegionId)
    paginator = client.list_buckets_paginator()
    results = []
    for page in paginator.iter_page(oss.ListBucketsRequest(prefix=Prefix)):
        for bucket in page.buckets:
            results.append(bucket.__str__())
    return results


@tools.append
def OSS_ListObjects(
    BucketName: str = Field(description='AlibabaCloud OSS Bucket Name'),
    RegionId: str = Field(description='AlibabaCloud region ID', default='cn-hangzhou'),
    Prefix: str = Field(description='AlibabaCloud OSS Bucket Name prefix', default=None)
):
    """获取指定OSS存储空间中的所有文件信息。"""
    if not BucketName:
        raise ValueError("Bucket name is required")
    client = create_client(region_id=RegionId)
    paginator = client.list_objects_v2_paginator()
    results = []
    for page in paginator.iter_page(oss.ListObjectsV2Request(
            bucket=BucketName,
            prefix=Prefix
        )):
        for object in page.contents:
            results.append(object.__str__())
    return results


@tools.append
def OSS_PutBucket(
    BucketName: str = Field(description='AlibabaCloud OSS Bucket Name'),
    RegionId: str = Field(description='AlibabaCloud region ID', default='cn-hangzhou'),
    StorageClass: str = Field(description='The Storage Type of AlibabaCloud OSS Bucket, The value range is as follows: '
                                          'Standard (default): standard storage, '
                                          'IA: infrequent access, Archive: archive storage, '
                                          'ColdArchive: cold archive storage, '
                                          'DeepColdArchive: deep cold archive storage', default='Standard'),
    DataRedundancyType: str = Field(description='The data disaster recovery type of AlibabaCloud OSS Bucket, '
                                                'LRS (default): Locally redundant LRS, which stores your data '
                                                'redundantly on different storage devices in the same availability zone. '
                                                'ZRS: Intra-city redundant ZRS, which uses a multi-availability zone '
                                                '(AZ) mechanism to store your data redundantly in three availability '
                                                'zones in the same region.', default='LRS')
):
    """创建一个新的OSS存储空间。"""
    client = create_client(region_id=RegionId)
    result = client.put_bucket(oss.PutBucketRequest(
        bucket=BucketName,
        create_bucket_configuration=oss.CreateBucketConfiguration(
            storage_class=StorageClass,
            data_redundancy_type=DataRedundancyType
        )
    ))
    return result.__str__()


@tools.append
def OSS_DeleteBucket(
    BucketName: str = Field(description='AlibabaCloud OSS Bucket Name'),
    RegionId: str = Field(description='AlibabaCloud region ID', default='cn-hangzhou')
):
    """删除指定的OSS存储空间。"""
    client = create_client(region_id=RegionId)
    result = client.delete_bucket(oss.DeleteBucketRequest(bucket=BucketName))
    return result.__str__()



def OSS_PutObject(
    BucketName: str = Field(description='AlibabaCloud OSS Bucket Name'),
    ObjectKey: str = Field(description='AlibabaCloud OSS Object Key (file path/name in OSS)'),
    FilePath: str = Field(description='Local file path to upload'),
    RegionId: str = Field(description='AlibabaCloud region ID', default='cn-hangzhou'),
    ContentType: str = Field(description='Content type of the object (e.g., text/plain, application/json). If not provided, will be inferred from file extension.', default=None)
):
    """上传本地文件到指定的OSS存储空间。"""
    logger.info(f"[OSS_PutObject] Input parameters: BucketName={BucketName}, ObjectKey={ObjectKey}, "
                f"FilePath={FilePath}, RegionId={RegionId}, ContentType={ContentType}")
    if not BucketName:
        raise ValueError("Bucket name is required")
    if not ObjectKey:
        raise ValueError("Object key is required")
    if not FilePath:
        raise ValueError("File path is required")

    # Check if file exists
    if not os.path.exists(FilePath):
        raise FileNotFoundError(f"File not found: {FilePath}")

    if not os.path.isfile(FilePath):
        raise ValueError(f"Path is not a file: {FilePath}")

    client = create_client(region_id=RegionId)

    # Read file content in binary mode
    with open(FilePath, 'rb') as f:
        body = f.read()

    # Infer content type from file extension if not provided
    if not ContentType:
        ContentType, _ = mimetypes.guess_type(FilePath)
        if not ContentType:
            ContentType = 'application/octet-stream'  # Default to binary

    # Prepare put object request
    request = oss.PutObjectRequest(
        bucket=BucketName,
        key=ObjectKey,
        body=body
    )

    # Set content type
    request.content_type = ContentType

    result = client.put_object(request)
    version_id = result.version_id
    response = {
        'status_code': result.status_code,
        'etag': result.etag if hasattr(result, 'etag') else None,
        'file_size': len(body),
        'content_type': ContentType,
        'version_id': version_id,
        'message': f'Successfully uploaded file {FilePath} as {ObjectKey} to bucket {BucketName}'
    }
    logger.info(f"[OSS_PutObject] Response: {json.dumps(response, ensure_ascii=False)}")
    return response
