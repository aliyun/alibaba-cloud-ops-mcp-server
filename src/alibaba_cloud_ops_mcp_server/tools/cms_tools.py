from pydantic import Field
from typing import List
import os
import json

from alibabacloud_cms20190101.client import Client as cms20190101Client
from alibabacloud_cms20190101 import models as cms_20190101_models
from alibaba_cloud_ops_mcp_server.alibabacloud.utils import create_config


END_STATUSES = ['Success', 'Failed', 'Cancelled']


tools = []


def create_client(region_id: str) -> cms20190101Client:
    config = create_config()
    config.endpoint = f'metrics.{region_id}.aliyuncs.com'
    return cms20190101Client(config)


def _get_cms_metric_data(region_id: str, instance_ids: List[str], metric_name: str):
    client = create_client(region_id)
    dimesion = []
    for instance_id in instance_ids:
        dimesion.append({
            'instanceId': instance_id
        })
    describe_metric_last_request = cms_20190101_models.DescribeMetricLastRequest(
        namespace='acs_ecs_dashboard',
        metric_name=metric_name,
        dimensions=json.dumps(dimesion),
    )
    describe_metric_last_resp = client.describe_metric_last(describe_metric_last_request)
    return describe_metric_last_resp.body.datapoints

@tools.append
def CMS_GetCpuUsageData(
    RegionId: str = Field(description='AlibabaCloud region ID', default='cn-hangzhou'),
    InstanceIds: List[str] = Field(description='AlibabaCloud ECS instance ID List'),
):
    """获取ECS实例的CPU使用率数据"""
    return _get_cms_metric_data(RegionId, InstanceIds, 'cpu_total')


@tools.append
def CMS_GetCpuLoadavgData(
    RegionId: str = Field(description='AlibabaCloud region ID', default='cn-hangzhou'),
    InstanceIds: List[str] = Field(description='AlibabaCloud ECS instance ID List'),
):
    """获取CPU一分钟平均负载指标数据"""
    return _get_cms_metric_data(RegionId, InstanceIds, 'load_1m')


@tools.append
def CMS_GetCpuloadavg5mData(
    RegionId: str = Field(description='AlibabaCloud region ID', default='cn-hangzhou'),
    InstanceIds: List[str] = Field(description='AlibabaCloud ECS instance ID List'),
):
    """获取CPU五分钟平均负载指标数据"""
    return _get_cms_metric_data(RegionId, InstanceIds, 'load_5m')
    

@tools.append
def CMS_GetCpuloadavg15mData(
    RegionId: str = Field(description='AlibabaCloud region ID', default='cn-hangzhou'),
    InstanceIds: List[str] = Field(description='AlibabaCloud ECS instance ID List'),
):
    """获取CPU十五分钟平均负载指标数据"""
    return _get_cms_metric_data(RegionId, InstanceIds, 'load_15m')

@tools.append
def CMS_GetMemUsedData(
    RegionId: str = Field(description='AlibabaCloud region ID', default='cn-hangzhou'),
    InstanceIds: List[str] = Field(description='AlibabaCloud ECS instance ID List'),
):
    """获取内存使用量指标数据"""
    return _get_cms_metric_data(RegionId, InstanceIds, 'memory_usedspace')


@tools.append
def CMS_GetMemUsageData(
    RegionId: str = Field(description='AlibabaCloud region ID', default='cn-hangzhou'),
    InstanceIds: List[str] = Field(description='AlibabaCloud ECS instance ID List'),
):
    """获取内存利用率指标数据"""
    return _get_cms_metric_data(RegionId, InstanceIds, 'memory_usedutilization')


@tools.append
def CMS_GetDiskUsageData(
    RegionId: str = Field(description='AlibabaCloud region ID', default='cn-hangzhou'),
    InstanceIds: List[str] = Field(description='AlibabaCloud ECS instance ID List'),
):
    """获取磁盘利用率指标数据"""
    return _get_cms_metric_data(RegionId, InstanceIds, 'diskusage_utilization')


@tools.append
def CMS_GetDiskTotalData(
    RegionId: str = Field(description='AlibabaCloud region ID', default='cn-hangzhou'),
    InstanceIds: List[str] = Field(description='AlibabaCloud ECS instance ID List'),
):
    """获取磁盘分区总容量指标数据"""
    return _get_cms_metric_data(RegionId, InstanceIds, 'diskusage_total')


@tools.append
def CMS_GetDiskUsedData(
    RegionId: str = Field(description='AlibabaCloud region ID', default='cn-hangzhou'),
    InstanceIds: List[str] = Field(description='AlibabaCloud ECS instance ID List'),
):
    """获取磁盘分区使用量指标数据"""
    return _get_cms_metric_data(RegionId, InstanceIds, 'diskusage_used')
