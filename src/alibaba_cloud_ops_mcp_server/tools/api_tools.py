import os
from mcp.server.fastmcp import FastMCP, Context
from pydantic import Field
import logging
import json
import re
from urllib.parse import quote

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

SERVICE_ENDPOINT_MAPPING = {
    'fc': 'fcv3'
}

REGION_ENDPOINT_SERVICE = ['ecs', 'oos', 'vpc', 'slb']

DOUBLE_ENDPOINT_SERVICE = {
    'rds': ['cn-qingdao', 'cn-beijing', 'cn-hangzhou', 'cn-shanghai', 'cn-shenzhen', 'cn-heyuan', 'cn-guangzhou', 'cn-hongkong'],
    'ess': ['cn-qingdao', 'cn-beijing', 'cn-hangzhou', 'cn-shanghai', 'cn-nanjing', 'cn-shenzhen'],
    'dds': ['cn-qingdao', 'cn-beijing', 'cn-wulanchabu', 'cn-hangzhou', 'cn-shanghai', 'cn-shenzhen', 'cn-heyuan', 'cn-guangzhou'],
    'r-kvstore': ['cn-qingdao', 'cn-beijing', 'cn-wulanchabu', 'cn-hangzhou', 'cn-shanghai', 'cn-shenzhen', 'cn-heyuan']
}

CENTRAL_SERVICE = ['cbn', 'ros', 'ram', 'resourcecenter']


DOMESTIC_ENDPOINT = 'DomesticEndpoint'
DOMESTIC_REGION = 'DomesticRegion'
INTERNATIONAL_ENDPOINT = 'InternationalEndpoint'

CENTRAL_SERVICE_ENDPOINTS = {
    'bssopenapi': {
        DOMESTIC_ENDPOINT: 'business.aliyuncs.com',
        INTERNATIONAL_ENDPOINT: 'business.ap-southeast-1.aliyuncs.com',
        DOMESTIC_REGION: ['cn-qingdao', 'cn-beijing', 'cn-zhangjiakou', 'cn-huhehaote', 'cn-wulanchabu',
                           'cn-hangzhou', 'cn-shanghai', 'cn-shenzhen', 'cn-chengdu', 'cn-hongkong']
    },
    'computenest': {
        DOMESTIC_ENDPOINT: 'computenest.cn-hangzhou.aliyuncs.com',
        INTERNATIONAL_ENDPOINT: 'computenest.ap-southeast-1.aliyuncs.com',
        DOMESTIC_REGION: ['cn-qingdao', 'cn-beijing', 'cn-zhangjiakou', 'cn-huhehaote', 'cn-wulanchabu',
                           'cn-hangzhou', 'cn-shanghai', 'cn-shenzhen', 'cn-chengdu', 'cn-hongkong']
    },
    'computenestsupplier': {
        DOMESTIC_ENDPOINT: 'computenestsupplier.cn-hangzhou.aliyuncs.com',
        INTERNATIONAL_ENDPOINT: 'computenestsupplier.ap-southeast-1.aliyuncs.com',
        DOMESTIC_REGION: ['cn-qingdao', 'cn-beijing', 'cn-zhangjiakou', 'cn-huhehaote', 'cn-wulanchabu',
                           'cn-hangzhou', 'cn-shanghai', 'cn-shenzhen', 'cn-chengdu', 'cn-hongkong']
    },
    'resourcecenter': {
        DOMESTIC_ENDPOINT: 'resourcecenter.aliyuncs.com',
        INTERNATIONAL_ENDPOINT: 'resourcecenter-intl.aliyuncs.com',
        DOMESTIC_REGION: ['cn-qingdao', 'cn-beijing', 'cn-zhangjiakou', 'cn-huhehaote', 'cn-wulanchabu',
                           'cn-hangzhou', 'cn-shanghai', 'cn-shenzhen', 'cn-chengdu', 'cn-hongkong']
    },
    'resourcemanager': {
        DOMESTIC_ENDPOINT: 'resourcemanager.aliyuncs.com',
        INTERNATIONAL_ENDPOINT: 'resourcemanager-intl.aliyuncs.com',
        DOMESTIC_REGION: ['cn-qingdao', 'cn-beijing', 'cn-zhangjiakou', 'cn-huhehaote', 'cn-wulanchabu',
                           'cn-hangzhou', 'cn-shanghai', 'cn-shenzhen', 'cn-chengdu', 'cn-hongkong']
    },
    'eds-user': {
        DOMESTIC_ENDPOINT: 'eds-user.cn-shanghai.aliyuncs.com',
        INTERNATIONAL_ENDPOINT: 'eds-user.ap-southeast-1.aliyuncs.com',
        DOMESTIC_REGION: ['cn-qingdao', 'cn-beijing', 'cn-zhangjiakou', 'cn-huhehaote', 'cn-wulanchabu',
                           'cn-hangzhou', 'cn-shanghai', 'cn-shenzhen', 'cn-chengdu', 'cn-hongkong']
    },
    'cloudfw': {
        DOMESTIC_ENDPOINT: 'cloudfw.aliyuncs.com',
        INTERNATIONAL_ENDPOINT: 'cloudfw.ap-southeast-1.aliyuncs.com',
        DOMESTIC_REGION: ['cn-qingdao', 'cn-beijing', 'cn-zhangjiakou', 'cn-huhehaote', 'cn-wulanchabu',
                           'cn-hangzhou', 'cn-shanghai', 'cn-shenzhen', 'cn-chengdu', 'cn-hongkong']
    }
}


def _get_service_endpoint(service: str, region_id: str):
    region_id = region_id.lower()
    service = service.lower()

    endpoint_service = SERVICE_ENDPOINT_MAPPING.get(service, service)

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
        return f'{endpoint_service}.{region_id}.aliyuncs.com'

    if service in DOUBLE_ENDPOINT_SERVICE:
        not_in_central = region_id not in DOUBLE_ENDPOINT_SERVICE[service]
        if not_in_central:
            return f'{endpoint_service}.{region_id}.aliyuncs.com'
        else:
            return f'{endpoint_service}.aliyuncs.com'

    if service in CENTRAL_SERVICE:
        return f'{endpoint_service}.aliyuncs.com'

    # Default
    return f'{endpoint_service}.{region_id}.aliyuncs.com'


def create_client(service: str, region_id: str) -> OpenApiClient:
    config = create_config()
    if isinstance(service, str):
        service = service.lower()
        # 通过代理访问的云产品
        if service in ['rdc-inner', 'ecs', 'devops-inner', 'ess', 'webhosting', 'slb', 'ecd', 'tag']:
            config.protocol = 'http'
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
    api_meta, _ = ApiMetaClient.get_api_meta(service, api)
    print(f'api_meta: {api_meta}')
    version = ApiMetaClient.get_service_version(service)
    method = 'POST' if api_meta.get('methods', [])[0] == 'post' else api_meta.get('methods', [])[0].upper()
    path = api_meta.get('path', '/')
    style = ApiMetaClient.get_service_style(service)
    
    # Handling special parameter formats
    processed_parameters = parameters.copy()
    processed_parameters = {k: v for k, v in processed_parameters.items() if v is not None}
    if service == 'ecs':
        for param_name, param_value in parameters.items():
            if param_name in ECS_LIST_PARAMETERS and isinstance(param_value, list):
                processed_parameters[param_name] = json.dumps(param_value)
    
    # 判断是否为 RESTful API
    is_restful = (style and style.upper() in ['RESTFUL', 'ROA'] ) or service in ['fc']
    
    if is_restful:
        # RESTful API 处理：区分路径参数、查询参数和请求体参数
        parameters_meta = api_meta.get('parameters', [])
        path_params = {}
        query_params = {}
        body_params = {}
        body_param_names = set()
        
        # 先找出所有 body 参数的名称
        for param_meta in parameters_meta:
            param_in = param_meta.get('in', '').lower()
            if param_in == 'body':
                param_name = param_meta.get('name')
                if param_name:
                    body_param_names.add(param_name)
                # 检查 body 参数的 schema，可能包含嵌套的属性
                schema = param_meta.get('schema', {})
                if isinstance(schema, dict):
                    properties = schema.get('properties', {})
                    if properties:
                        body_param_names.update(properties.keys())
        
        # 根据参数位置分类
        for param_meta in parameters_meta:
            param_name = param_meta.get('name')
            param_in = param_meta.get('in', '').lower()
            
            if param_name in processed_parameters:
                param_value = processed_parameters[param_name]
                if param_in == 'path':
                    path_params[param_name] = param_value
                elif param_in == 'query':
                    query_params[param_name] = param_value
                elif param_in == 'body' or param_name in body_param_names:
                    # body 参数或 body 中的嵌套属性
                    body_params[param_name] = param_value
        
        # 替换路径中的参数占位符，支持 {paramName} 格式
        pathname = path
        for param_name, param_value in path_params.items():
            # 支持多种占位符格式：{paramName}, {param_name}
            # 使用正则表达式替换，不区分大小写
            escaped_name = re.escape(param_name)
            # 对路径参数值进行 URL 编码，保留路径分隔符 / 不被编码
            # 这样可以正确处理路径参数，同时避免特殊字符导致 "Illegal Path Character" 错误
            param_str = str(param_value)
            # 对于路径参数，只编码特殊字符，保留 / 字符（如果参数值本身是路径的一部分）
            encoded_value = quote(param_str, safe='/')
            # 替换 {paramName} 格式（单花括号）
            pathname = re.sub(rf'\{{{escaped_name}\}}', encoded_value, pathname, flags=re.IGNORECASE)
            # 替换 {{paramName}} 格式（双重花括号，用于转义）
            pathname = re.sub(rf'\{{{{2}}{escaped_name}\}}{2}', encoded_value, pathname, flags=re.IGNORECASE)
        
        # 确保路径以 / 开头
        if not pathname.startswith('/'):
            pathname = '/' + pathname
        
        # 获取请求体样式
        body_style = ApiMetaClient.get_api_body_style(service, api)
        req_body_type = body_style if body_style else 'json'
        
        # 构建请求体
        body = None
        if body_params:
            if req_body_type == 'json':
                # 对于 JSON 格式，直接序列化 body_params
                body = json.dumps(body_params, ensure_ascii=False) if isinstance(body_params, dict) else body_params
            elif req_body_type in ['formData', 'form']:
                # 对于 formData 格式，使用 OpenApiUtilClient.query 处理
                body = OpenApiUtilClient.query(body_params)
            else:
                body = body_params
        
        # 构建 OpenApiRequest
        req = open_api_models.OpenApiRequest(
            query=OpenApiUtilClient.query(query_params) if query_params else None,
            body=body
        )
        
        # ROA/RESTful API 配置
        # 注意：根据阿里云 SDK 文档，ROA 风格的 API 可能需要 action 参数
        # 但某些情况下 action 可以为 None，优先使用 pathname
        params = open_api_models.Params(
            action=api,  # ROA 风格 API 通常也需要 action
            version=version,
            protocol='HTTPS',
            pathname=pathname,
            method=method,
            auth_type='AK',
            style='ROA',
            req_body_type=req_body_type,
            body_type='string'
        )
        
        logger.info(f'Call RESTful API Request: Service: {service} API: {api} Method: {method} Path: {pathname} Query: {query_params} Body: {body_params}')
    else:
        # RPC API 处理（原有逻辑）
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
        logger.info(f'Call RPC API Request: Service: {service} API: {api} Method: {method} Parameters: {processed_parameters}')
    
    client = create_client(service, processed_parameters.get('RegionId', 'cn-hangzhou'))
    runtime = util_models.RuntimeOptions()
    try:
        resp = client.call_api(params, req, runtime)
        logger.info(f'Call API Response: {resp}')
    except Exception as e:
        resp = f'Call API Error: {e}'
        logger.error(resp)
    return resp


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
