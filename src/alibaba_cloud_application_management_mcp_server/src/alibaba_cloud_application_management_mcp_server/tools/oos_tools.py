from pydantic import Field
from typing import List
import json
import time
import logging

from alibabacloud_oos20190601.client import Client as oos20190601Client
from alibabacloud_oos20190601 import models as oos_20190601_models
from alibaba_cloud_ops_mcp_server.alibabacloud.utils import create_config
from alibaba_cloud_ops_mcp_server.alibabacloud import exception
from alibaba_cloud_application_management_mcp_server.alibabacloud.utils import create_client


END_STATUSES = [SUCCESS, FAILED, CANCELLED] = ['Success', 'Failed', 'Cancelled']


tools = []

PACKAGE_MAP = {
    'docker': 'ACS-Extension-DockerCE-1853370294850618',
    'java': 'ACS-Extension-java-1853370294850618',
    'python': 'ACS-Extension-python-1853370294850618',
    'nodejs': 'ACS-Extension-node-1853370294850618',
    'golang': 'ACS-Extension-golang-1853370294850618',
    'nginx': 'ACS-Extension-nginx-1853370294850618',
    'git': 'ACS-Extension-Git-1853370294850618',
}


def _start_execution_sync(region_id: str, template_name: str, parameters: dict):
    client = create_client(region_id=region_id)
    start_execution_request = oos_20190601_models.StartExecutionRequest(
        region_id=region_id,
        template_name=template_name,
        parameters=json.dumps(parameters)
    )
    start_execution_resp = client.start_execution(start_execution_request)
    execution_id = start_execution_resp.body.execution.execution_id

    while True:
        list_executions_request = oos_20190601_models.ListExecutionsRequest(
            region_id=region_id,
            execution_id=execution_id
        )
        list_executions_resp = client.list_executions(list_executions_request)
        status = list_executions_resp.body.executions[0].status
        if status == FAILED:
            status_message = list_executions_resp.body.executions[0].status_message
            raise exception.OOSExecutionFailed(reason=status_message)
        elif status in END_STATUSES:
            return list_executions_resp.body
        time.sleep(1)


def _start_execution_async(region_id: str, template_name: str, parameters: dict):
    client = create_client(region_id=region_id)
    start_execution_request = oos_20190601_models.StartExecutionRequest(
        region_id=region_id,
        template_name=template_name,
        parameters=json.dumps(parameters)
    )
    start_execution_resp = client.start_execution(start_execution_request)
    execution_id = start_execution_resp.body.execution.execution_id
    return execution_id


@tools.append
def InstallDeployEnvironment(
        PackageName: str = Field(description='OOS Package Name, like: Java, Python, ...'),
        InstanceIds: List[str] = Field(description='AlibabaCloud ECS instance ID List', default=None),
        RegionId: str = Field(description='AlibabaCloud region ID', default='cn-hangzhou'),
        Action: str = Field(description='Action to be performed, optional value：install uninstall', default='install'),
        ApplicationName: str = Field(description='Application name', default=None),
        ApplicationGroupName: str = Field(description='Application group name', default=None)
):
    """
    功能说明
        安装 OOS 公共扩展（即：将指定软件安装到 ECS 实例）。

    参数说明
        a. ApplicationName 与 ApplicationGroupName 需成对提供，作为一组筛选条件。
        b. InstanceIds 需成组提供，作为另一组筛选条件。
        以上两组条件，至少需提供一组，否则无法确定目标 ECS 实例，安装将无法进行。允许同时提交

    支持的扩展列表
        Docker：Docker 社区版
        Java：Java 编程语言环境
        Python：Python 编程语言环境
        Nodejs：Node.js 运行环境
        Golang：Go 编程语言环境
        Nginx：高性能 HTTP 及反向代理服务器
        Git：分布式版本控制系统

    注意：
    1、请确保已正确指定筛选条件，否则扩展安装无法执行。
    2、只允许安装列表内的软件。

    """
    logging.info(f"OOS_ConfigureOOSPackages Input: PackageName={PackageName}, InstanceIds={InstanceIds}, RegionId={RegionId}, Action={Action}, ApplicationName={ApplicationName}, ApplicationGroupName={ApplicationGroupName}")
    
    package_name = PACKAGE_MAP.get(PackageName.lower())
    if not package_name:
        raise PackageNotSupported(package=PackageName, list=list(PACKAGE_MAP.keys()))

    if ApplicationName and ApplicationGroupName:
        targets = {
            'RegionId': RegionId,
            'Type': 'ApplicationGroup',
            'ApplicationName': ApplicationName,
            'ApplicationGroupName': ApplicationGroupName
        }
        if InstanceIds:
            targets['ResourceIds'] = InstanceIds
    else:
        targets = {
            'ResourceIds': InstanceIds,
            'RegionId': RegionId,
            'Type': 'ResourceIds'
        }
    parameters = {
        "regionId": RegionId,
        "targets": targets,
        "action": Action,
        "packageName": package_name,
    }
    execution_id = _start_execution_async(region_id=RegionId, template_name='ACS-ECS-BulkyConfigureOOSPackageWithTemporaryURL',
                                         parameters=parameters)

    url = f"https://oos.console.aliyun.com/{RegionId}/execution/detail/{execution_id}"

    logging.info(f"OOS_ConfigureOOSPackages Output: execution_id={execution_id}, url={url}")

    return {
        'region_id': RegionId,
        'execution_id': execution_id,
        'url': url
    }


@tools.append
def ListExecutions(
        ExecutionId: str = Field(description='The ID of the OOS Execution'),
        RegionId: str = Field(description='AlibabaCloud region ID', default='cn-hangzhou')
):
    """
    根据执行ID查询执行状态
    """
    client = create_client(region_id=RegionId)
    list_executions_request = oos_20190601_models.ListExecutionsRequest(
        region_id=RegionId,
        execution_id=ExecutionId
    )
    list_executions_resp = client.list_executions(list_executions_request)
    status = list_executions_resp.body.executions[0].status
    template_name = list_executions_resp.body.executions[0].template_name
    resp = {
        'TemplateName': template_name,
        'Status': status,
        'ExecutionId': ExecutionId,
        'url': f"https://oos.console.aliyun.com/{RegionId}/execution/detail/{ExecutionId}"
    }
    if status == 'Success':
        output = list_executions_resp.body.executions[0].outputs
        if output:
            resp['Output'] = output
    if status == 'Failed':
        status_message = list_executions_resp.body.executions[0].status_message
        if status:
            resp['StatusMessage'] = status_message
    return resp


class PackageNotSupported(exception.AcsException):
    msg_fmt = 'The requested package: ({package}) is not supported. Supported packages: {list}.'
    status = 400
    code = 'Package.NotSupported'
