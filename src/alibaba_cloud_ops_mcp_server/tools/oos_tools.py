from pydantic import Field
from typing import List
import os
import json
import time

from alibabacloud_oos20190601.client import Client as oos20190601Client
from alibabacloud_oos20190601 import models as oos_20190601_models
from alibaba_cloud_ops_mcp_server.alibabacloud.utils import create_config
from alibaba_cloud_ops_mcp_server.alibabacloud import exception


END_STATUSES = [SUCCESS, FAILED, CANCELLED] = ['Success', 'Failed', 'Cancelled']


tools = []


def create_client(region_id: str) -> oos20190601Client:
    config = create_config()
    config.endpoint = f'oos.{region_id}.aliyuncs.com'
    return oos20190601Client(config)


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
@tools.append
def OOS_RunCommand(
    Command: str = Field(description='Content of the command executed on the ECS instance'),
    InstanceIds: List[str] = Field(description='AlibabaCloud ECS instance ID List'),
    RegionId: str = Field(description='AlibabaCloud region ID', default='cn-hangzhou'),
    CommandType: str = Field(description='The type of command executed on the ECS instance, optional value：RunShellScript，RunPythonScript，RunPerlScript，RunBatScript，RunPowerShellScript', default='RunShellScript')
):
    """批量在多台ECS实例上运行云助手命令，适用于需要同时管理多台ECS实例的场景，如应用程序管理和资源标记操作等。"""
    
    parameters = {
        'regionId': RegionId,
        'resourceType': 'ALIYUN::ECS::Instance',
        'targets': {
            'ResourceIds': InstanceIds,
            'RegionId': RegionId,
            'Type': 'ResourceIds',
            'Parameters': {
                'RegionId': RegionId,
                'Status': 'Running'
            }
        },
        "commandType": CommandType,
        "commandContent": Command
    }
    return _start_execution_sync(region_id=RegionId, template_name='ACS-ECS-BulkyRunCommand', parameters=parameters)
    

@tools.append
def OOS_StartInstances(
    InstanceIds: List[str] = Field(description='AlibabaCloud ECS instance ID List'),
    RegionId: str = Field(description='AlibabaCloud region ID', default='cn-hangzhou'),
):
    """批量启动ECS实例，适用于需要同时管理和启动多台ECS实例的场景，例如应用部署和高可用性场景。"""
    
    parameters = {
        'regionId': RegionId,
        'resourceType': 'ALIYUN::ECS::Instance',
        'targets': {
            'ResourceIds': InstanceIds,
            'RegionId': RegionId,
            'Type': 'ResourceIds'
        }
    }
    return _start_execution_sync(region_id=RegionId, template_name='ACS-ECS-BulkyStartInstances', parameters=parameters)


@tools.append
def OOS_StopInstances(
    InstanceIds: List[str] = Field(description='AlibabaCloud ECS instance ID List'),
    RegionId: str = Field(description='AlibabaCloud region ID', default='cn-hangzhou'),
    ForeceStop: bool = Field(description='Is forced shutdown required', default=False)
):
    """批量停止ECS实例，适用于需要同时管理和停止多台ECS实例的场景。"""
    
    parameters = {
        'regionId': RegionId,
        'resourceType': 'ALIYUN::ECS::Instance',
        'targets': {
            'ResourceIds': InstanceIds,
            'RegionId': RegionId,
            'Type': 'ResourceIds'
        },
        'forceStop': ForeceStop
    }
    return _start_execution_sync(region_id=RegionId, template_name='ACS-ECS-BulkyStopInstances', parameters=parameters)


@tools.append
def OOS_RebootInstances(
    InstanceIds: List[str] = Field(description='AlibabaCloud ECS instance ID List'),
    RegionId: str = Field(description='AlibabaCloud region ID', default='cn-hangzhou'),
    ForeceStop: bool = Field(description='Is forced shutdown required', default=False)
):
    """批量重启ECS实例，适用于需要同时管理和重启多台ECS实例的场景。"""
    
    parameters = {
        'regionId': RegionId,
        'resourceType': 'ALIYUN::ECS::Instance',
        'targets': {
            'ResourceIds': InstanceIds,
            'RegionId': RegionId,
            'Type': 'ResourceIds'
        },
        'forceStop': ForeceStop
    }
    return _start_execution_sync(region_id=RegionId, template_name='ACS-ECS-BulkyRebootInstances', parameters=parameters)


@tools.append
def OOS_RunInstances(
    ImageId: str = Field(description='Image ID'),
    InstanceType: str = Field(description='Instance Type'),
    SecurityGroupId: str = Field(description='SecurityGroup ID'),
    VSwitchId: str = Field(description='VSwitch ID'),
    RegionId: str = Field(description='AlibabaCloud region ID', default='cn-hangzhou'),
    InternetMaxBandwidthOut: int = Field(description='The maximum outbound bandwidth of the instance. Unit: Mbit/s. Valid values: 0 to 100. If you want to open the public network for the ECS instance, you need to set a value > 0', default=0),
    Amount: int = Field(description='Number of ECS instances', default=1),
    InstanceName: str = Field(description='Instance Name', default=''),
    SystemDiskCategory: str = Field(description='The category of the system disk. Valid values: cloud_efficiency, cloud_ssd, cloud_essd, cloud_auto, cloud, cloud_essd_entry', default='cloud_essd'),
    SystemDiskSize: str = Field(description='The size of the system disk. Unit: GiB. Valid values: 20 to 500. Default value: 40 or the image size, whichever is greater', default=''),
    SystemDiskName: str = Field(description='The name of the system disk', default=''),
    SystemDiskDescription: str = Field(description='The description of the system disk', default=''),
    SystemDiskPerformanceLevel: str = Field(description='The performance level of the ESSD used as the system disk. Valid values: PL0, PL1, PL2, PL3', default='PL1'),
    PrivateIpAddress: str = Field(description='The private IP address of the instance. For VPC type ECS instances, the private IP address must be selected from the available IP range of the VSwitch', default=''),
    SystemDiskAutoSnapshotPolicyId: str = Field(description='The ID of the automatic snapshot policy to apply to the system disk', default=''),
    DataDiskParameters: str = Field(description='Data disk configuration in JSON format. Example: [{"Size":"100","DiskName":"data-disk-1","Description":"","Category":"cloud_essd","PerformanceLevel":"PL1","AutoSnapshotPolicyId":""}]', default=''),
    Tags: list = Field(description='The tag of an ECS instance, for example: [{"Key":"oos","Value":"test"}]', default=[]),
    ResourceGroupId: str = Field(description='Resource group ID', default=''),
    Description: str = Field(description='The description of the ECS instances', default=''),
    HostName: str = Field(description='The host name of the ECS instance', default=''),
    ZoneId: str = Field(description='The ID of the zone where the ECS instances are deployed', default=''),
):
    """批量创建ECS实例，适用于需要同时创建多台ECS实例的场景，例如应用部署和高可用性场景。"""

    parameters = {
        'regionId': RegionId,
        'imageId': ImageId,
        'instanceType': InstanceType,
        'securityGroupId': SecurityGroupId,
        'vSwitchId': VSwitchId,
        'internetMaxBandwidthOut': InternetMaxBandwidthOut,
        'amount': Amount,
        'instanceName': InstanceName
    }

    if SystemDiskCategory:
        parameters['systemDiskCategory'] = SystemDiskCategory
    if SystemDiskSize:
        parameters['systemDiskSize'] = SystemDiskSize
    if SystemDiskName:
        parameters['systemDiskName'] = SystemDiskName
    if SystemDiskDescription:
        parameters['systemDiskDescription'] = SystemDiskDescription
    if SystemDiskPerformanceLevel:
        parameters['systemDiskPerformanceLevel'] = SystemDiskPerformanceLevel
    if PrivateIpAddress:
        parameters['privateIpAddress'] = PrivateIpAddress
    if SystemDiskAutoSnapshotPolicyId:
        parameters['systemDiskAutoSnapshotPolicyId'] = SystemDiskAutoSnapshotPolicyId
    if Tags:
        parameters['tags'] = Tags
    if ResourceGroupId:
        parameters['resourceGroupId'] = ResourceGroupId
    if Description:
        parameters['description'] = Description
    if HostName:
        parameters['hostName'] = HostName
    if ZoneId:
        parameters['zoneId'] = ZoneId

    if DataDiskParameters:
        try:
            data_disks = json.loads(DataDiskParameters) if isinstance(DataDiskParameters, str) else DataDiskParameters
            if isinstance(data_disks, list) and len(data_disks) > 0:
                parameters['dataDiskParameters'] = data_disks
        except (json.JSONDecodeError, TypeError) as e:
            pass
    
    return _start_execution_sync(region_id=RegionId, template_name='ACS-ECS-RunInstances', parameters=parameters)


@tools.append
def OOS_ResetPassword(
    InstanceIds: List[str] = Field(description='AlibabaCloud ECS instance ID List'),
    Password: str = Field(description='The password of the ECS instance must be 8-30 characters and must contain only the following characters: lowercase letters, uppercase letters, numbers, and special characters only.（）~！@#$%^&*-_+=（40：<>，？/'),
    RegionId: str = Field(description='AlibabaCloud region ID', default='cn-hangzhou'),
):
    """批量修改ECS实例的密码，请注意，本操作将会重启ECS实例"""
    parameters = {
        'regionId': RegionId,
        'resourceType': 'ALIYUN::ECS::Instance',
        'targets': {
            'ResourceIds': InstanceIds,
            'RegionId': RegionId,
            'Type': 'ResourceIds'
        },
        'password': Password
    }
    return _start_execution_sync(region_id=RegionId, template_name='ACS-ECS-BulkyResetPassword', parameters=parameters)

@tools.append
def OOS_ReplaceSystemDisk(
    InstanceIds: List[str] = Field(description='AlibabaCloud ECS instance ID List'),
    ImageId: str = Field(description='Image ID'),
    RegionId: str = Field(description='AlibabaCloud region ID', default='cn-hangzhou')
):
    """批量替换ECS实例的系统盘，更换操作系统"""
    parameters = {
        'regionId': RegionId,
        'resourceType': 'ALIYUN::ECS::Instance',
        'targets': {
            'ResourceIds': InstanceIds,
            'RegionId': RegionId,
            'Type': 'ResourceIds'
        },
        'imageId': ImageId
    }
    return _start_execution_sync(region_id=RegionId, template_name='ACS-ECS-BulkyReplaceSystemDisk', parameters=parameters)


@tools.append
def OOS_StartRDSInstances(
    InstanceIds: List[str] = Field(description='AlibabaCloud ECS instance ID List'),
    RegionId: str = Field(description='AlibabaCloud region ID', default='cn-hangzhou')
):
    """批量启动RDS实例，适用于需要同时管理和启动多台RDS实例的场景，例如应用部署和高可用性场景。"""

    parameters = {
        'regionId': RegionId,
        'resourceType': 'ALIYUN::RDS::Instance',
        'targets': {
            'ResourceIds': InstanceIds,
            'RegionId': RegionId,
            'Type': 'ResourceIds'
        }
    }
    return _start_execution_sync(region_id=RegionId, template_name='ACS-RDS-BulkyStartInstances', parameters=parameters)


@tools.append
def OOS_StopRDSInstances(
    InstanceIds: List[str] = Field(description='AlibabaCloud RDS instance ID List'),
    RegionId: str = Field(description='AlibabaCloud region ID', default='cn-hangzhou')
):
    """批量停止RDS实例，适用于需要同时管理和停止多台RDS实例的场景。"""

    parameters = {
        'regionId': RegionId,
        'resourceType': 'ALIYUN::RDS::Instance',
        'targets': {
            'ResourceIds': InstanceIds,
            'RegionId': RegionId,
            'Type': 'ResourceIds'
        }
    }
    return _start_execution_sync(region_id=RegionId, template_name='ACS-RDS-BulkyStopInstances', parameters=parameters)


@tools.append
def OOS_RebootRDSInstances(
    InstanceIds: List[str] = Field(description='AlibabaCloud RDS instance ID List'),
    RegionId: str = Field(description='AlibabaCloud region ID', default='cn-hangzhou')
):
    """批量重启RDS实例，适用于需要同时管理和重启多台RDS实例的场景。"""

    parameters = {
        'regionId': RegionId,
        'resourceType': 'ALIYUN::RDS::Instance',
        'targets': {
            'ResourceIds': InstanceIds,
            'RegionId': RegionId,
            'Type': 'ResourceIds'
        }
    }
    return _start_execution_sync(region_id=RegionId, template_name='ACS-RDS-BulkyRestartInstances',
                                 parameters=parameters)
