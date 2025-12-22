import os
import time

from Tea.exceptions import UnretryableException
from mcp.server.fastmcp import FastMCP, Context
from pydantic import Field
import logging
import json

import inspect
import types
from dataclasses import make_dataclass, field
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_tea_util import models as util_models
from alibabacloud_tea_openapi.client import Client as OpenApiClient
from alibabacloud_openapi_util.client import Client as OpenApiUtilClient
from alibaba_cloud_ops_mcp_server.alibabacloud.api_meta_client import ApiMetaClient
from alibaba_cloud_ops_mcp_server.alibabacloud.utils import create_config
from alibaba_cloud_ops_mcp_server.settings import settings

logger = logging.getLogger(__name__)

type_map = {
    'string': str,
    'integer': int,
    'boolean': bool,
    'array': list,
    'object': dict,
    'number': float
}

REGION_ENDPOINT_SERVICE = ['ecs', 'oos', 'vpc', 'slb']

DOUBLE_ENDPOINT_SERVICE = {
    'rds': ['cn-qingdao', 'cn-beijing', 'cn-hangzhou', 'cn-shanghai', 'cn-shenzhen', 'cn-heyuan', 'cn-guangzhou', 'cn-hongkong'],
    'ess': ['cn-qingdao', 'cn-beijing', 'cn-hangzhou', 'cn-shanghai', 'cn-nanjing', 'cn-shenzhen'],
    'dds': ['cn-qingdao', 'cn-beijing', 'cn-wulanchabu', 'cn-hangzhou', 'cn-shanghai', 'cn-shenzhen', 'cn-heyuan', 'cn-guangzhou'],
    'r-kvstore': ['cn-qingdao', 'cn-beijing', 'cn-wulanchabu', 'cn-hangzhou', 'cn-shanghai', 'cn-shenzhen', 'cn-heyuan']
}

CENTRAL_SERVICE = ['cbn', 'ros', 'ram']

CENTRAL_SERVICE_ENDPOINTS = {
    'bssopenapi': {
        'DomesticEndpoint': 'business.aliyuncs.com',
        'InternationalEndpoint': 'business.ap-southeast-1.aliyuncs.com',
        'DomesticRegion': ['cn-qingdao', 'cn-beijing', 'cn-zhangjiakou', 'cn-huhehaote', 'cn-wulanchabu',
                           'cn-hangzhou', 'cn-shanghai', 'cn-shenzhen', 'cn-chengdu', 'cn-hongkong']
    }
}


def _get_service_endpoint(service: str, region_id: str):
    region_id = region_id.lower()

    # Prioritizing central service endpoints
    central = CENTRAL_SERVICE_ENDPOINTS.get(service)
    if central:
        if settings.env == 'international':
            return central['InternationalEndpoint']
        elif region_id in central.get('DomesticRegion', []) or settings.env == 'domestic':
            return central['DomesticEndpoint']
        else:
            return central['InternationalEndpoint']

    # Determine whether to use regional endpoints
    if service in REGION_ENDPOINT_SERVICE:
        return f'{service}.{region_id}.aliyuncs.com'

    if service in DOUBLE_ENDPOINT_SERVICE:
        not_in_central = region_id not in DOUBLE_ENDPOINT_SERVICE[service]
        if not_in_central:
            return f'{service}.{region_id}.aliyuncs.com'
        else:
            return f'{service}.aliyuncs.com'

    if service in CENTRAL_SERVICE:
        return f'{service}.aliyuncs.com'

    # Default
    return f'{service}.{region_id}.aliyuncs.com'


def create_client(service: str, region_id: str) -> OpenApiClient:
    config = create_config()
    if isinstance(service, str):
        service = service.lower()
    endpoint = _get_service_endpoint(service, region_id.lower())
    config.endpoint = endpoint
    logger.info(f'Service Endpoint: {endpoint}')
    return OpenApiClient(config)


# JSON array parameter of type String
ECS_LIST_PARAMETERS = {
    'HpcClusterIds', 'DedicatedHostClusterIds', 'DedicatedHostIds',
    'InstanceIds', 'DeploymentSetIds', 'KeyPairNames', 'SecurityGroupIds',
    'diskIds', 'repeatWeekdays', 'timePoints', 'DiskIds', 'SnapshotLinkIds',
    'EipAddresses', 'PublicIpAddresses', 'PrivateIpAddresses'
}


def _tools_api_call(service: str, api: str, parameters: dict, ctx: Context):
    service = service.lower()
    try:
        api_meta, _ = ApiMetaClient.get_api_meta(service, api)
    except Exception as e:
        logger.error(f'Get API Meta Error: {e}')
        api_meta = {}

    version = ApiMetaClient.get_service_version(service)
    method = 'POST' if api_meta.get('methods', ['post'])[0] == 'post' else 'GET'
    path = api_meta.get('path', '/')
    style = ApiMetaClient.get_service_style(service)

    # Handling special parameter formats
    processed_parameters = parameters.copy()
    processed_parameters = {k: v for k, v in processed_parameters.items() if v is not None}
    if service == 'ecs':
        for param_name, param_value in parameters.items():
            if param_name in ECS_LIST_PARAMETERS and isinstance(param_value, list):
                processed_parameters[param_name] = json.dumps(param_value)

    req = open_api_models.OpenApiRequest(
        query=OpenApiUtilClient.query(processed_parameters)
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
    logger.info(f'Call API Request: Service: {service} API: {api} Method: {method} Parameters: {processed_parameters}')
    client = create_client(service, processed_parameters.get('RegionId', 'cn-hangzhou'))
    runtime = util_models.RuntimeOptions()
    
    max_retries = 3
    last_exception = None
    
    for attempt in range(max_retries):
        try:
            resp = client.call_api(params, req, runtime)
            logger.info(f'Call API Response: {resp}')
            return resp
        except UnretryableException as e:
            last_exception = e
            error_msg = str(e)
            has_bad_fd = '[Errno 9] Bad file descriptor' in error_msg
            
            if has_bad_fd and attempt < max_retries - 1:
                wait_time = (attempt + 1) * 0.5
                logger.warning(f'[_tools_api_call] UnretryableException with [Errno 9] Bad file descriptor (attempt {attempt + 1}/{max_retries}), retrying after {wait_time}s: {e}')
                time.sleep(wait_time)
            else:
                logger.error(f'Call API Error: {e}')
                raise e

    if last_exception:
        logger.error(f'[_tools_api_call] All retries failed, raising last exception: {last_exception}')
        raise last_exception


def _create_parameter_schema(fields: dict):
    return make_dataclass("ParameterSchema", [(name, type_, value) for name, (type_, value) in fields.items()])


def _create_function_schemas(service, api, api_meta):
    schemas = {}
    schemas[api] = {}
    parameters = api_meta.get('parameters', [])

    required_params = []
    optional_params = []

    for parameter in parameters:
        name = parameter.get('name')
        # TODO 目前忽略了带'.'的参数
        if '.' in name:
            continue
        schema = parameter.get('schema', '')
        required = schema.get('required', False)

        if required:
            required_params.append(parameter)
        else:
            optional_params.append(parameter)

    def process_parameter(parameter):
        name = parameter.get('name')
        schema = parameter.get('schema', '')
        description = schema.get('description', '')
        example = schema.get('example', '')
        type_ = schema.get('type', '')
        description = f'{description} 参数类型: {type_},参数示例：{example}'
        required = schema.get('required', False)

        if service.lower() == 'ecs' and name in ECS_LIST_PARAMETERS and type_ == 'string':
            python_type = list
        else:
            python_type = type_map.get(type_, str)

        field_info = (
            python_type,
            field(
                default=None,
                metadata={'description': description, 'required': required}
            )
        )
        return name, field_info

    for parameter in required_params:
        name, field_info = process_parameter(parameter)
        schemas[api][name] = field_info

    for parameter in optional_params:
        name, field_info = process_parameter(parameter)
        schemas[api][name] = field_info

    if 'RegionId' not in schemas[api]:
        schemas[api]['RegionId'] = (
            str,
            field(
                default='cn-hangzhou',
                metadata={'description': '地域ID', 'required': False}
            )
        )
    return schemas


def _create_tool_function_with_signature(service: str, api: str, fields: dict, description: str):
    """
    Dynamically creates a lambda function with a custom signature based on the provided fields.
    """
    parameters = []
    annotations = {}
    defaults = {}

    for name, (type_, field_info) in fields.items():
        field_description = field_info.metadata.get('description', '')
        is_required = field_info.metadata.get('required', False)
        default_value = field_info.default if not is_required else ...

        field_default = Field(default=default_value, description=field_description)
        parameters.append(inspect.Parameter(
            name=name,
            kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
            default=field_default,
            annotation=type_
        ))
        annotations[name] = type_
        defaults[name] = field_default

    signature = inspect.Signature(parameters)
    function_name = f'{service.upper()}_{api}'
    def func_code(*args, **kwargs):
        bound_args = signature.bind(*args, **kwargs)
        bound_args.apply_defaults()

        return _tools_api_call(
            service=service,
            api=api,
            parameters=bound_args.arguments,
            ctx=None
        )

    func = types.FunctionType(
        func_code.__code__,
        globals(),
        function_name,
        None,
        func_code.__closure__
    )
    func.__signature__ = signature
    func.__annotations__ = annotations
    func.__defaults__ = tuple(defaults.values())
    func.__doc__ = description

    return func


def _create_and_decorate_tool(mcp: FastMCP, service: str, api: str):
    """Create a tool function for an AlibabaCloud openapi."""
    api_meta, _ = ApiMetaClient.get_api_meta(service, api)
    fields = _create_function_schemas(service, api, api_meta).get(api, {})
    description = api_meta.get('summary', '')
    dynamic_lambda = _create_tool_function_with_signature(service, api, fields, description)
    function_name = f'{service.upper()}_{api}'
    decorated_function = mcp.tool(name=function_name)(dynamic_lambda)

    return decorated_function


def create_api_tools(mcp: FastMCP, config:dict):
    for service_code, apis in config.items():
        for api_name in apis:
            _create_and_decorate_tool(mcp, service_code, api_name)
