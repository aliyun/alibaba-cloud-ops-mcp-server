import logging
from typing import Any
from pydantic import Field

from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_tea_util import models as util_models
from alibabacloud_tea_openapi.client import Client as OpenApiClient
from alibabacloud_openapi_util.client import Client as OpenApiUtilClient
from alibaba_cloud_ops_mcp_server.alibabacloud.utils import create_config
from alibaba_cloud_ops_mcp_server.tools.api_tools import _get_service_endpoint, _tools_api_call


logger = logging.getLogger(__name__)


tools = []


@tools.append
def QueryAccountResources(
        query_input: str = Field(
            description='自然语言查询描述，可以查询资源属性或者数量等信息，例如：查询上海有哪些资源、所有地域的ECS实例数量')
):
    """查询账号下的资源信息。
    Args:
        query_input (str):
            自然语言查询描述，可以查询资源属性或者数量等信息，例如："查询上海有哪些资源"、"查询东南亚地区的 ECS 实例"、"所有地域的ECS实例数量"等。

    Returns:
        ToolResponse:
            返回资源查询结果（JSON 文本）。
    """
    try:
        # 第一步：调用 GenerateSQLQueryByAI 生成 SQL
        service = 'resourcecenter'

        # 创建客户端和参数
        config = create_config()
        config.endpoint = _get_service_endpoint(service, 'cn-hangzhou')
        client = OpenApiClient(config)

        # 调用 GenerateSQLQueryByAI
        queries_generate = {'Input': query_input}
        params_generate = open_api_models.Params(
            action='GenerateSQLQueryByAI',
            version='2022-12-01',
            protocol='HTTPS',
            method='POST',
            auth_type='AK',
            style='RPC',
            pathname='/',
            req_body_type='json',
            body_type='json'
        )
        request_generate = open_api_models.OpenApiRequest(
            query=OpenApiUtilClient.query(queries_generate)
        )
        runtime = util_models.RuntimeOptions()

        logger.info(f'Call GenerateSQLQueryByAI: Input={query_input}')
        resp_generate = client.call_api(params_generate, request_generate, runtime)
        logger.info(f'GenerateSQLQueryByAI Response: {resp_generate}')

        # 从响应中提取 SQL
        body = resp_generate.get('body', {})
        sql = body.get('Sql', '')

        if not sql:
            error_msg = f"生成 SQL 失败，响应: {resp_generate}"
            logger.error(error_msg)
            return error_msg

        logger.info(f'Generated SQL: {sql}')

        # 第二步：调用 ExecuteSQLQuery 执行 SQL 查询
        queries_execute = {'Expression': sql}
        params_execute = open_api_models.Params(
            action='ExecuteSQLQuery',
            version='2022-12-01',
            protocol='HTTPS',
            method='POST',
            auth_type='AK',
            style='RPC',
            pathname='/',
            req_body_type='json',
            body_type='json'
        )
        request_execute = open_api_models.OpenApiRequest(
            query=OpenApiUtilClient.query(queries_execute)
        )

        logger.info(f'Call ExecuteSQLQuery: Expression={sql}')
        resp_execute = client.call_api(params_execute, request_execute, runtime)
        logger.info(f'ExecuteSQLQuery Response: {resp_execute}')

        # 返回查询结果
        return resp_execute

    except Exception as e:
        error_msg = f"查询资源失败: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return error_msg


@tools.append
def DescribeZones(
        region_id: str = Field(description='地域ID,例如:cn-hangzhou、cn-beijing、cn-shanghai等')
):
    """查询指定地域下的可用区列表

    Args:
        region_id (`str`):
            地域ID,例如:cn-hangzhou(杭州)、cn-beijing(北京)、cn-shanghai(上海)等

    Returns:
        `ToolResponse`:
            返回指定地域下的可用区列表,包括可用区ID
    """
    try:
        # 调用 ECS DescribeZones API 查询可用区信息
        parameters = {
            'RegionId': region_id
        }
        resp = _tools_api_call('ecs', 'DescribeZones', parameters, ctx=None)

        # 解析返回结果,提取可用区ID列表
        zones = resp.get('body', {}).get('Zones', {}).get('Zone', [])

        if not zones:
            text = f"地域 {region_id} 下未查询到可用区信息,可能是不支持的地域ID或API调用失败"
        else:
            # 提取可用区ID列表
            zone_ids = [zone.get('ZoneId') for zone in zones if zone.get('ZoneId')]

            # 格式化输出为纯文本列表
            text = f"地域 {region_id} 的可用区列表:\n"
            for idx, zone_id in enumerate(zone_ids, 1):
                text += f"{idx}. {zone_id}\n"
            text += f"共 {len(zone_ids)} 个可用区"

        return text
    except Exception as e:
        error_text = f"查询地域 {region_id} 的可用区时发生错误: {str(e)}"
        logger.error(error_text, exc_info=True)
        return error_text
