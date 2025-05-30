import os
from pydantic import Field
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_tea_util import models as util_models
from alibabacloud_tea_openapi.client import Client as OpenApiClient
from alibabacloud_openapi_util.client import Client as OpenApiUtilClient
from alibaba_cloud_ops_mcp_server.alibabacloud.api_meta_client import ApiMetaClient
from alibaba_cloud_ops_mcp_server.alibabacloud.static import PROMPT_UNDERSTANDING
from alibaba_cloud_ops_mcp_server.tools.api_tools import create_client, _tools_api_call

END_STATUSES = ['Success', 'Failed', 'Cancelled']

tools = []


@tools.append
def PromptUnderstanding() -> str:
    """
    Always use this tool first to understand the user's query and convert it into suggestions from Alibaba Cloud experts.
    """
    return PROMPT_UNDERSTANDING


@tools.append
def ListAPIs(
        service: str = Field(description='AlibabaCloud service code')
):
    """
    Get the corresponding API list information through the service name to prepare for the subsequent selection of the appropriate API to call
    """
    return ApiMetaClient.get_apis_in_service(service)


@tools.append
def GetAPIInfo(
        service: str = Field(description='AlibabaCloud service code'),
        api: str = Field(description='AlibabaCloud api name'),
):
    """
    After specifying the service name and API name, get the detailed API META of the corresponding API
    """
    data, version = ApiMetaClient.get_api_meta(service, api)
    return data.get('parameters')


@tools.append
def CommonAPICaller(
        service: str = Field(description='AlibabaCloud service code'),
        api: str = Field(description='AlibabaCloud api name'),
        parameters: dict = Field(description='AlibabaCloud ECS instance ID List', default={}),
):
    """
    Perform the actual call by specifying the Service, API, and Parameters
    """
    return _tools_api_call(service, api, parameters, None)
