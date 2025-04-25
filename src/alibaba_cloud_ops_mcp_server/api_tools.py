from pydantic import Field
from typing import List
from api_meta_client import ApiMetaClient

import os
from mcp.server.fastmcp import FastMCP, Context
from pydantic import Field
import click
import logging

import inspect
import types
from dataclasses import make_dataclass, field
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_tea_util import models as util_models
from alibabacloud_tea_openapi.client import Client as OpenApiClient
from alibabacloud_openapi_util.client import Client as OpenApiUtilClient
from alibaba_cloud_ops_mcp_server.api_meta_client import ApiMetaClient
from alibaba_cloud_ops_mcp_server.config import config

END_STATUSES = ['Success', 'Failed', 'Cancelled']

tools = []


@tools.append
def ListServices():
    """获取阿里云所有公开的服务信息，数据量较大，谨慎调用"""
    return ApiMetaClient.get_all_service_info()


@tools.append
def ListAPIs(
        service: str = Field(description='AlibabaCloud service code')
):
    """通过服务名称，获取其对应的api列表信息，为后续选择合适的API进行调用作准备"""
    return ApiMetaClient.get_apis_in_service(service)


@tools.append
def GetAPIInfo(
        service: str = Field(description='AlibabaCloud service code'),
        api: str = Field(description='AlibabaCloud api name'),
):
    """指定服务名称和API名称后，获取对应api的详细API META"""
    data, version = ApiMetaClient.get_api_meta(service, api)
    return data.get('parameters')


@tools.append
def CommonAPICaller(
        service: str = Field(description='AlibabaCloud service code'),
        api: str = Field(description='AlibabaCloud api name'),
        parameters: dict = Field(description='AlibabaCloud ECS instance ID List', default={}),
):
    """通过指定Service，API，以及Parameters，来进行实际的调用"""
    service = service.lower()
    api_meta, _ = ApiMetaClient.get_api_meta(service, api)
    version = ApiMetaClient.get_service_version(service)
    method = 'POST' if api_meta.get('methods', [])[0] == 'post' else 'GET'
    path = api_meta.get('path', '/')
    style = ApiMetaClient.get_service_style(service)
    req = open_api_models.OpenApiRequest(
        query=OpenApiUtilClient.query(parameters)
    )
    params = open_api_models.Params(
        action=api,
        version=version,
        protocol='HTTPS',
        pathname=path,
        method=method,
        auth_type='AK',
        style=style,
        req_body_type='formData',
        body_type='json'
    )
    client = create_client(service, parameters.get('RegionId', 'cn-hangzhou'))
    runtime = util_models.RuntimeOptions()
    return client.call_api(params, req, runtime)


def create_client(service: str, region_id: str) -> OpenApiClient:
    config = open_api_models.Config(
        access_key_id=os.environ['ALIBABA_CLOUD_ACCESS_KEY_ID'],
        access_key_secret=os.environ['ALIBABA_CLOUD_ACCESS_KEY_SECRET'],
        user_agent='alibaba-cloud-ops-mcp-server',
    )
    if isinstance(service, str):
        service = service.lower()
    config.endpoint = f'{service}.{region_id}.aliyuncs.com'
    return OpenApiClient(config)
