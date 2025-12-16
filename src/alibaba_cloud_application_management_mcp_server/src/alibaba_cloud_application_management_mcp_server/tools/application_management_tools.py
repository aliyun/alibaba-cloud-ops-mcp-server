import re
import logging

from alibaba_cloud_application_management_mcp_server.tools.api_tools import _tools_api_call
from pathlib import Path

from pydantic import Field
from typing import Optional
import json
import time
from alibabacloud_oos20190601.client import Client as oos20190601Client
from alibabacloud_oos20190601 import models as oos_20190601_models
from alibabacloud_ecs20140526 import models as ecs_20140526_models
from alibaba_cloud_application_management_mcp_server.tools import oss_tools
from alibaba_cloud_application_management_mcp_server.alibabacloud.utils import (
    ensure_code_deploy_dirs,
    load_application_info,
    save_application_info,
    get_release_path,
    create_client,
    create_ecs_client,
    put_bucket_tagging,
    find_bucket_by_tag,
    get_or_create_bucket_for_code_deploy,
)

logger = logging.getLogger(__name__)

APPLICATION_MANAGEMENT_REGION_ID = 'cn-hangzhou'
DEPLOYING_STATUSES = ['Deploying', 'Releasing']
SUCCESS_STATUSES = ['Deployed', 'Released']
FAILED_STATUSES = ['DeployFailed', 'ReleaseFailed']
END_STATUSES = SUCCESS_STATUSES + FAILED_STATUSES

tools = []


def _append_tool(func):
    tools.append(func)
    return func


@_append_tool
def CodeDeploy(
        name: str = Field(description='name of the application'),
        deploy_region_id: str = Field(description='Region ID for deployment'),
        application_group_name: str = Field(description='name of the application group'),
        region_id_oss: str = Field(description='OSS region ID'),
        object_name: str = Field(description='OSS object name'),
        file_path: str = Field(description='Local file path to upload. If the file is not in '
                                           '.code_deploy/release directory, it will be copied there.'),
        is_internal_oss: bool = Field(description='Whether to download OSS files through internal network. Note: '
                                                  'If you choose internal network download, you must ensure that '
                                                  'the ECS to be deployed and OSS are in the same region.'),
        application_start: str = Field(
            description='Application start command script. IMPORTANT: If the uploaded artifact '
                        'is a tar archive or compressed package (e.g., .tar, .tar.gz, .zip), '
                        'you MUST first extract it and navigate into the corresponding directory'
                        ' before executing the start command. The start command must correspond '
                        'to the actual structure of the extracted artifact. For example, if you '
                        'upload a tar.gz file containing a Java application, first extract it '
                        'with "tar -xzf <filename>.tar.gz", then cd into the extracted '
                        'directory, and then run the start command (e.g., "java -jar app.jar" '
                        'or "./start.sh"). Ensure the start command matches the actual '
                        'executable or script in the extracted artifact to avoid deployment '
                        'failures.'),
        application_stop: str = Field(description='Application stop command script'),
        port: int = Field(description='Application listening port'),
        instance_ids: list = Field(description='AlibabaCloud ECS instance ID List. If empty or not provided, user '
                                               'will be prompted to create ECS instances.', default=None)
):
    """
    通过应用管理 API 部署应用到 ECS 实例。

    完整部署流程（在调用此工具之前）：

    步骤 1：识别部署方式
    - 通过本地文件操作工具读取项目文件（package.json、requirements.txt、pom.xml 等）
    - 识别项目的部署方式和技术栈（npm、python、java、go 等）
    - 生成构建命令，注意，该构建命令不需要生成构建脚本，不要因此新增sh文件，任何情况下都不要，因为构建命令是CodeDeploy的参数，不需要生成文件

    步骤 2：构建或压缩文件，并记录文件路径
    - 在本地执行构建命令，生成部署产物（tar.gz、zip 等压缩包）
    - 将构建产物保存到 .code_deploy/release 目录下
    - 记录文件路径，留待后续CodeDeploy使用

    步骤 3：调用此工具进行部署
    - 此工具会依次调用：CreateApplication（如果不存在）、CreateApplicationGroup（如果不存在）、
      TagResources（可选，如果是已有资源需要打 tag 导入应用分组）、DeployApplicationGroup

    重要提示：
    1. 启动脚本（application_start）必须与上传的产物对应。如果产物是压缩包（tar、tar.gz、zip等），
       需要先解压并进入对应目录后再执行启动命令。
    2. 示例：如果上传的是 app.tar.gz，启动脚本应该类似，一般压缩包就在当前目录下，直接解压即可：
       "tar -xzf app.tar.gz && ./start.sh"
       或者如果解压后是Java应用：
       "tar -xzf app.tar.gz && java -jar app.jar"
    3. 确保启动命令能够正确找到并执行解压后的可执行文件或脚本，避免部署失败。启动命令应该将程序运行在后台并打印日志到指定文件，
        注意使用非交互式命令，比如unzip -o等自动覆盖的命令，无需交互
    例如：
       - npm 程序示例：
         "tar -xzf app.tar.gz  && nohup npm start > /root/app.log 2>&1 &"
         或者分别输出标准输出和错误日志：
         "tar -xzf app.tar.gz && nohup npm start > /root/app.log 2> /root/app.error.log &"
       - Java 程序示例：
         "tar -xzf app.tar.gz && nohup java -jar app.jar > /root/app.log 2>&1 &"
       - Python 程序示例：
         "tar -xzf app.tar.gz && nohup python app.py > /root/app.log 2>&1 &"
       说明：使用 nohup 命令可以让程序在后台运行，即使终端关闭也不会终止；> 重定向标准输出到日志文件；2>&1 将标准错误也重定向到同一文件；& 符号让命令在后台执行。
    4. 应用和应用分组会自动检查是否存在，如果存在则跳过创建，避免重复创建错误。
    5. 如果未提供 ECS 实例 ID，工具会返回提示信息，引导用户到 ECS 控制台创建实例。
    6. 部署完成后，部署信息会保存到 .code_deploy/.application.json 文件中。

    创建完成后，你应该以markdown的形式向用户展示你获取的service link，方便用户跳转
    """
    # Check ECS instance ID
    if not instance_ids or len(instance_ids) == 0:
        ecs_purchase_link = f'https://ecs-buy.aliyun.com/ecs#/custom/prepay/{deploy_region_id}?orderSource=buyWizard-console-list'
        security_group_link = f'https://ecs.console.aliyun.com/securityGroup?regionId={deploy_region_id}'
        port_info = f'port {port}' if port else 'application port'
        return {
            'error': 'ECS_INSTANCE_REQUIRED',
            'message': f'ECS instance ID not provided. Please create ECS instances first before deployment.',
            'region_id': deploy_region_id,
            'ecs_purchase_link': ecs_purchase_link,
            'security_group_link': security_group_link,
            'instructions': f'''
                ## ECS Instance Creation Required
                
                **Deployment Region**: {deploy_region_id}
                
                ### Step 1: Create ECS Instances
                Please visit the following link to create ECS instances:
                [{ecs_purchase_link}]({ecs_purchase_link})
                
                After creation, please provide the ECS instance ID list.
                
                ### Step 2: Configure Security Group (Post-deployment Operation)
                After deployment, you need to open {port_info} for the ECS instance's security group. Please visit:
                [{security_group_link}]({security_group_link})
                
                Add inbound rules in the security group rules:
                - Port range: {port}/{port} (if port is specified)
                - Protocol type: TCP
                - Authorized object: 0.0.0.0/0 (or restrict access source as needed)
            '''
        }

    ensure_code_deploy_dirs()

    # Process file path: if file is not in release directory, copy it to release directory
    file_path_obj = Path(file_path)
    if not file_path_obj.is_absolute():
        file_path_obj = Path.cwd() / file_path_obj

    # Check if file exists
    if not file_path_obj.exists():
        raise FileNotFoundError(f"File does not exist: {file_path_obj}")

    # Normalize path (resolve Windows path case and separator issues)
    file_path_resolved = file_path_obj.resolve()
    release_path = get_release_path(file_path_obj.name)
    release_path_resolved = release_path.resolve()

    # If file is not in release directory, copy it there (using Path object comparison, cross-platform compatible)
    if file_path_resolved != release_path_resolved:
        import shutil
        shutil.copy2(file_path_resolved, release_path_resolved)
        logger.info(f"[code_deploy] Copied file from {file_path_resolved} to {release_path_resolved}")
        file_path = str(release_path_resolved)
    else:
        logger.info(f"[code_deploy] File already in release directory: {file_path}")

    # Log input parameters
    logger.info(f"[code_deploy] Input parameters: name={name}, deploy_region_id={deploy_region_id}, "
                f"application_group_name={application_group_name}, instance_ids={instance_ids}, "
                f"region_id_oss={region_id_oss}, object_name={object_name}, "
                f"is_internal_oss={is_internal_oss}, port={port}")

    # Upload file to OSS
    bucket_name = get_or_create_bucket_for_code_deploy(name, region_id_oss)
    logger.info(f"[code_deploy] Auto selected/created bucket: {bucket_name}")

    put_object_resp = oss_tools.OSS_PutObject(
        BucketName=bucket_name,
        ObjectKey=object_name,
        FilePath=file_path,
        RegionId=region_id_oss,
        ContentType="application/octet-stream",
    )
    version_id = put_object_resp.get('version_id')
    logger.info(f"[code_deploy] Put Object Response: {put_object_resp}")

    client = create_client(region_id=APPLICATION_MANAGEMENT_REGION_ID)

    if not _check_application_exists(client, name):
        logger.info(f"[code_deploy] Application '{name}' does not exist, creating it...")
        alarm_config = oos_20190601_models.CreateApplicationRequestAlarmConfig()
        create_application_request = oos_20190601_models.CreateApplicationRequest(
            region_id=APPLICATION_MANAGEMENT_REGION_ID,
            name=name,
            alarm_config=alarm_config
        )
        client.create_application(create_application_request)
        logger.info(f"[code_deploy] Application '{name}' created successfully")
    else:
        logger.info(f"[code_deploy] Application '{name}' already exists, skipping creation")

    if not _check_application_group_exists(client, name, application_group_name):
        deploy_request = _handle_new_application_group(client, name, application_group_name,
                                                       deploy_region_id, region_id_oss, bucket_name,
                                                       object_name, version_id, is_internal_oss,
                                                       port, instance_ids, application_start,
                                                       application_stop)
    else:
        deploy_request = _handle_existing_application_group(client, name, application_group_name,
                                                            deploy_region_id, region_id_oss, bucket_name,
                                                            object_name, version_id, application_start,
                                                            application_stop)

    response = client.deploy_application_group(deploy_request)
    logger.info(f"[code_deploy] Response: {json.dumps(str(response), ensure_ascii=False)}")

    # Save deployment info to .application.json
    deploy_info = {
        'last_deployment': {
            'application_name': name,
            'application_group_name': application_group_name,
            'deploy_region_id': deploy_region_id,
            'port': port,
            'instance_ids': instance_ids,
            'deploy_time': time.strftime('%Y-%m-%d %H:%M:%S')
        }
    }
    save_application_info(deploy_info)
    service_link = f'https://ecs.console.aliyun.com/app/detail?tabKey=overview&appName={name}&groupName={application_group_name}'
    security_group_link = f'https://ecs.console.aliyun.com/securityGroup?regionId={deploy_region_id}'

    return {
        'response': response,
        'service_link': service_link,
        'security_group_link': security_group_link,
        'port': port,
        'deploy_region_id': deploy_region_id,
        'security_group_instructions': f'''
            ## Deployment Successful!
            
            **Service Link**: [View Deployment Details]({service_link})
            
            ### Important: Configure Security Group Rules
            
            After the application is deployed, you need to open port **{port}** for the ECS instance's security group, otherwise the application will not be accessible from outside.
            
            **Security Group Management Link**: [{security_group_link}]({security_group_link})
            
            **Configuration Steps**:
            1. Visit the security group management link above
            2. Find the security group to which your ECS instance belongs
            3. Click "Configure Rules" → "Add Security Group Rule"
            4. Configure inbound rule:
               - **Port range**: {port}/{port}
               - **Protocol type**: TCP
               - **Authorized object**: 0.0.0.0/0 (allow all sources, or restrict access source as needed)
               - **Description**: Application port {port}
            
            After configuration, the application can be accessed via the ECS instance's public IP and port {port}.
        '''
    }


@_append_tool
def GetLastDeploymentInfo(
        random_string: Optional[str] = Field(default=None, description='')
):
    """
    获取上次部署的应用信息
    """
    logger.info("[GetLastDeploymentInfo] Reading last deployment info")
    info = load_application_info()
    last_deployment = info.get('last_deployment', {})

    if not last_deployment:
        return {
            'message': 'No information found about the last deployment',
            'info': {}
        }

    logger.info(f"[GetLastDeploymentInfo] Found last deployment: {last_deployment}")
    return {
        'message': 'Successfully retrieved last deployment information',
        'info': last_deployment
    }


@_append_tool
def GetDeployStatus(
        name: str = Field(description='name of the application'),
        application_group_name: str = Field(description='name of the application group'),
):
    """
    查询应用分组的部署状态
    """
    logger.info(f"[GetDeployStatus] Input parameters: name={name}, application_group_name={application_group_name}")
    client = create_client(region_id=APPLICATION_MANAGEMENT_REGION_ID)
    response = _list_application_group_deployment(client, name, application_group_name, END_STATUSES)
    logger.info(f"[GetDeployStatus] Response: {json.dumps(str(response), ensure_ascii=False)}")
    return response


def _handle_new_application_group(client, name, application_group_name, deploy_region_id,
                                  region_id_oss, bucket_name, object_name, version_id,
                                  is_internal_oss, port, instance_ids, application_start,
                                  application_stop):
    logger.info(f"[code_deploy] Application group '{application_group_name}' does not exist, creating it...")
    create_application_group_request = oos_20190601_models.CreateApplicationGroupRequest(
        region_id=APPLICATION_MANAGEMENT_REGION_ID,
        application_name=name,
        deploy_region_id=deploy_region_id,
        name=application_group_name
    )
    client.create_application_group(create_application_group_request)
    logger.info(f"[code_deploy] Application group '{application_group_name}' created successfully")

    if len(instance_ids) > 1:
        _tag_multiple_instances(deploy_region_id, name, application_group_name, instance_ids)

    deploy_parameters = _create_deploy_parameters(
        name, application_group_name, region_id_oss, bucket_name,
        object_name, version_id, is_internal_oss, port, instance_ids,
        application_start, application_stop
    )

    return oos_20190601_models.DeployApplicationGroupRequest(
        region_id=APPLICATION_MANAGEMENT_REGION_ID,
        application_name=name,
        name=application_group_name,
        deploy_parameters=json.dumps(deploy_parameters)
    )


def _handle_existing_application_group(client, name, application_group_name, deploy_region_id,
                                       region_id_oss, bucket_name, object_name, version_id,
                                       application_start, application_stop):
    logger.info(f"[code_deploy] Application group '{application_group_name}' already exists, skipping creation")

    location_hooks = _create_location_and_hooks(
        region_id_oss, bucket_name, object_name, version_id,
        deploy_region_id, application_start, application_stop
    )

    create_deploy_parameters = {
        'ApplicationName': name,
        'Description': '',
        'RevisionType': 'Oss',
        'Location': json.dumps(location_hooks["location"]),
        'Hooks': json.dumps(location_hooks["hooks"])
    }

    create_deploy_revision_response = _tools_api_call(
        'oos',
        'CreateDeployRevision',
        create_deploy_parameters,
        ctx=None
    )
    logger.info(f"[code_deploy] create_deploy_revision_response {create_deploy_revision_response}")
    revision_id = str(create_deploy_revision_response.get('body', {}).get('Revision', {}).get('RevisionId'))

    start_execution_parameters = json.dumps({
        "Parameters": json.dumps({
            "applicationName": name,
            "applicationGroupName": application_group_name,
            "deployRevisionId": revision_id,
            "deployMethod": "all",
            "batchNumber": 2,
            "batchPauseOption": "Automatic"
        }),
        "Mode": "FailurePause"
    })
    deploy_parameters = json.dumps({
        "StartExecutionParameters": start_execution_parameters
    })
    logger.info(f"[code_deploy] deploy_parameters {deploy_parameters}")
    return oos_20190601_models.DeployApplicationGroupRequest(
        region_id=APPLICATION_MANAGEMENT_REGION_ID,
        application_name=name,
        name=application_group_name,
        deploy_parameters=deploy_parameters,
        revision_id=revision_id
    )


def _tag_multiple_instances(deploy_region_id, name, application_group_name, instance_ids):
    remaining_instance_ids = instance_ids[1:]
    ecs_client = create_ecs_client(region_id=deploy_region_id)
    tag_resources_request = ecs_20140526_models.TagResourcesRequest(
        region_id=deploy_region_id,
        resource_type='Instance',
        resource_id=remaining_instance_ids,
        tag=[ecs_20140526_models.TagResourcesRequestTag(
            key=f'app-{name}',
            value=application_group_name
        )]
    )
    ecs_client.tag_resources(tag_resources_request)


def _list_application_group_deployment(client, name, application_group_name, status_list):
    """
    View application group deployment status
    """

    get_application_group_request = oos_20190601_models.GetApplicationGroupRequest(
        region_id=APPLICATION_MANAGEMENT_REGION_ID,
        application_name=name,
        name=application_group_name
    )
    response = client.get_application_group(get_application_group_request)
    status = response.body.application_group.status
    if status in status_list:
        return response.body


def _check_application_exists(client: oos20190601Client, name: str) -> bool:
    try:
        get_application_request = oos_20190601_models.GetApplicationRequest(
            region_id=APPLICATION_MANAGEMENT_REGION_ID,
            name=name
        )
        client.get_application(get_application_request)
        return True
    except Exception as e:
        error_code = getattr(e, 'code', None)
        if error_code == 'EntityNotExists.Application':
            return False
        logger.warning(f"[_check_application_exists] Error checking application {name}: {e}")
        raise


def _check_application_group_exists(client: oos20190601Client, application_name: str, group_name: str) -> bool:
    try:
        get_application_group_request = oos_20190601_models.GetApplicationGroupRequest(
            region_id=APPLICATION_MANAGEMENT_REGION_ID,
            application_name=application_name,
            name=group_name
        )
        client.get_application_group(get_application_group_request)
        return True
    except Exception as e:
        error_code = getattr(e, 'code', None)
        if error_code == 'EntityNotExists.ApplicationGroup':
            return False
        logger.warning(
            f"[_check_application_group_exists] Error checking application group {application_name}/{group_name}: {e}")
        raise


def _create_deploy_parameters(name, application_group_name, region_id_oss, bucket_name, object_name, version_id,
                              is_internal_oss, port, instance_ids, application_start, application_stop):
    """
    Create deployment parameters
    """
    repo_name = re.sub(r'[^a-z0-9-]', '-', name.lower())

    return {
        "Parameters": {
            "CreateEcsOption": "ExistECS" if instance_ids else "NewECS",
            "InstanceId": instance_ids[0] if instance_ids else None,
            "ApplicationName": name,
            "Description": "",
            "ZoneId": "cn-hangzhou-b",
            "Port": port,
            "RepoName": repo_name,
            "RevisionType": "Oss",
            "RegionIdOSS": region_id_oss,
            "BucketName": bucket_name,
            "ObjectName": object_name,
            "VersionId": version_id,
            "IsInternalOSS": is_internal_oss,
            "ApplicationGroupName": application_group_name,
            "WorkingDir": "/root",
            "ApplicationStart": application_start,
            "ApplicationStop": application_stop,
            "ArtifactSourceType": "others",
            "PackageName": "ACS-Extension-DockerCE-1853370294850618"
        },
        "TemplateName": "Sample",
        "ServiceVersion": "beta",
        "ServiceId": "service-561c4b4e45c74dcaa741"
    }


def _create_location_and_hooks(region_id_oss, bucket_name, object_name, version_id, deploy_region_id,
                               application_start, application_stop):
    """
    Create location and hook configuration
    """
    return {
        "location": {
            "regionId": region_id_oss,
            "bucketName": bucket_name,
            "objectName": object_name,
            "versionId": version_id,
            "isInternal": "true" if region_id_oss == deploy_region_id else "false"
        },
        "hooks": {
            "workingDir": "/root",
            "applicationStart": application_start,
            "applicationStop": application_stop
        }
    }


def _create_revision_deploy_parameters():
    """
    Create revised deployment parameters
    """
    return {
        "StartExecutionParameters": {
            "Parameters": {
                "applicationName": "",
                "applicationGroupName": "",
                "deployRevisionId": "",
                "deployMethod": "all",
                "batchNumber": 2,
                "batchPauseOption": "Automatic"
            },
            "Mode": "FailurePause"
        }
    }
