import re
import logging

from alibaba_cloud_ops_mcp_server.tools.api_tools import _tools_api_call
from pathlib import Path
import alibabacloud_oss_v2 as oss
from pydantic import Field
from typing import Optional, Tuple, List
import json
import time
from alibabacloud_oos20190601.client import Client as oos20190601Client
from alibabacloud_oos20190601 import models as oos_20190601_models
from alibabacloud_ecs20140526 import models as ecs_20140526_models
from alibabacloud_ecs20140526.client import Client as ecs20140526Client
from alibaba_cloud_ops_mcp_server.tools import oss_tools
from alibaba_cloud_ops_mcp_server.alibabacloud.utils import (
    ensure_code_deploy_dirs,
    load_application_info,
    save_application_info,
    get_release_path,
    create_client,
    create_ecs_client,
    put_bucket_tagging,
    find_bucket_by_tag,
    get_or_create_bucket_for_code_deploy,
    set_project_path,
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
def OOS_CodeDeploy(
        name: str = Field(description='name of the application'),
        deploy_region_id: str = Field(description='Region ID for deployment'),
        application_group_name: str = Field(description='name of the application group'),
        object_name: str = Field(description='OSS object name'),
        file_path: str = Field(description='Local file path to upload. If the file is not in '
                                           '.code_deploy/release directory, it will be copied there.'),
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
                        'failures. Do not blindly use the `cd` command; always verify that the corresponding file '
                        'and path exist before using it.'),
        application_stop: str = Field(description='Application stop command script, Defensive stop command - checks if '
                                                  'the service exists and if the CD path exists, preventing errors '
                                                  'caused by blindly using `cd` or due to non-existent commands.'),
        deploy_language: str = Field(description='Deploy language, like:docker, java, python, nodejs, golang'),
        port: int = Field(description='Application listening port'),
        project_path: Optional[str] = Field(description='Root path of the project. The .code_deploy '
                                                                       'directory will be created in this path. '
                                                                       'If not provided, will try to infer from file_path '
                                                                       'or use current working directory.'),
        instance_ids: list = Field(description='AlibabaCloud ECS instance ID List. If empty or not provided, user '
                                               'will be prompted to create ECS instances.', default=None)

):
    """
    将应用部署到阿里云ECS实例。使用阿里云OOS（运维编排服务）的CodeDeploy功能实现自动化部署。

    ## 前置条件（调用此工具前需完成）

    1. **识别项目类型**：读取项目配置文件（package.json、pom.xml、requirements.txt等），确定技术栈和部署语言（通过deploy_language参数传入）
    2. **构建部署产物**：执行构建命令生成压缩包（tar.gz、zip等），保存到 `.code_deploy/release` 目录
    3. **准备ECS实例**：确保目标ECS实例已创建，获取实例ID列表

    ## 核心要求

    ### 1. 防御性命令设计（必须）
    启动和停止命令必须包含存在性检查，避免因路径/文件/命令不存在导致失败：
    - 压缩包：先检查文件存在再解压 `[ -f app.tar.gz ] && tar -xzf app.tar.gz || exit 1`
    - 可执行文件：检查文件存在再执行 `[ -f start.sh ] && chmod +x start.sh && ./start.sh || exit 1`
    - 命令可用性：检查命令是否存在 `command -v npm >/dev/null 2>&1 || exit 1`
    - 禁止直接使用 `cd`，必须先验证路径存在

    ### 2. 压缩包处理规范（必须）
    如果产物是压缩包，启动命令必须先解压：
    - 使用非交互式命令：`tar -xzf`、`unzip -o`（自动覆盖，无需确认）
    - 解压后执行启动命令，确保路径对应
    - 示例：`tar -xzf app.tar.gz && nohup java -jar app.jar > /root/app.log 2>&1 &`

    ### 3. 后台运行与日志（必须）
    启动命令必须使用后台运行并重定向日志：
    - 格式：`nohup <command> > /root/app.log 2>&1 &`
    - 说明：nohup保持后台运行，`>` 重定向标准输出，`2>&1` 合并错误输出，`&` 后台执行

    ### 4. 停止命令规范
    停止命令需检查服务/进程是否存在：
    - systemctl服务：`systemctl list-units | grep -q "service" && systemctl stop service`
    - 进程名：`pkill -f "process_pattern" || true`

    ## 注意事项

    - 应用和应用分组会自动检查，已存在则跳过创建
    - 未提供ECS实例ID时，工具会返回创建引导链接
    - 部署信息自动保存到 `.code_deploy/.application.json`
    - project_path未提供时，会从file_path推断或使用当前目录
    - 部署完成后，以markdown格式展示service_link供用户跳转
    """
    # Set project path if provided
    if project_path:
        set_project_path(project_path)
        logger.info(f"[code_deploy] Project path set to: {project_path}")
    else:
        # Try to infer project path from file_path
        file_path_obj = Path(file_path)
        if not file_path_obj.is_absolute():
            file_path_obj = Path.cwd() / file_path_obj
        file_path_resolved = file_path_obj.resolve()
        
        # Try to find project root by looking for common project files
        current_dir = file_path_resolved.parent
        project_root = None
        project_indicators = ['package.json', 'pom.xml', 'requirements.txt', 'go.mod', 'Cargo.toml', '.git']
        
        # Search up to 5 levels for project root
        for _ in range(5):
            if any((current_dir / indicator).exists() for indicator in project_indicators):
                project_root = current_dir
                break
            parent = current_dir.parent
            if parent == current_dir:  # Reached filesystem root
                break
            current_dir = parent
        
        if project_root:
            set_project_path(str(project_root))
            logger.info(f"[code_deploy] Inferred project path from file_path: {project_root}")
        else:
            # Use the directory containing the file as project root
            set_project_path(str(file_path_resolved.parent))
            logger.info(f"[code_deploy] Using file directory as project path: {file_path_resolved.parent}")
    
    # Check ECS instance ID
    if not instance_ids:
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
    
    # 校验 ECS 实例是否存在
    logger.info(f"[code_deploy] Validating ECS instances: {instance_ids}")
    all_exist, missing_instance_ids = _check_ecs_instances_exist(deploy_region_id, instance_ids)
    if not all_exist:
        return {
            'error': 'ECS_INSTANCE_NOT_FOUND',
            'message': f'Some ECS instances do not exist in region {deploy_region_id}.',
            'region_id': deploy_region_id,
            'missing_instance_ids': missing_instance_ids,
            'provided_instance_ids': instance_ids,
            'instructions': f'''
                ## ECS Instance Validation Failed
                
                **Deployment Region**: {deploy_region_id}
                
                **Missing Instance IDs**: {', '.join(missing_instance_ids)}
                
                **All Provided Instance IDs**: {', '.join(instance_ids)}
                
                Please verify that:
                1. The instance IDs are correct
                2. The instances exist in region {deploy_region_id}
                3. You have permission to access these instances
                
                You can check your instances at:
                https://ecs.console.aliyun.com/?regionId={deploy_region_id}#/server/instance
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
    region_id_oss = 'cn-hangzhou'
    is_internal_oss = True if deploy_region_id.lower() == 'cn-hangzhou' else False
    # Log input parameters
    logger.info(f"[code_deploy] Input parameters: name={name}, deploy_region_id={deploy_region_id}, "
                f"application_group_name={application_group_name}, instance_ids={instance_ids}, "
                f"region_id_oss={region_id_oss}, object_name={object_name}, "
                f"is_internal_oss={is_internal_oss}, port={port}")

    # Upload file to OSS
    try:
        bucket_name = get_or_create_bucket_for_code_deploy(name)
        logger.info(f"[code_deploy] Auto selected/created bucket: {bucket_name}")
    except oss.exceptions.OperationError as e:
        oss_console_link = 'https://oss.console.aliyun.com/'
        return {
            'error': 'OSS_SERVICE_NOT_ACTIVATED',
            'message': '用户的阿里云OSS服务未开通，需要点击链接进行开通',
            'oss_console_link': oss_console_link,
            'instructions': f'''
                ## OSS服务未开通
                
                您的阿里云OSS服务尚未开通，请点击以下链接进行开通：
                [{oss_console_link}]({oss_console_link})
                
                开通后，请重新尝试部署操作。
            '''
        }

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
                                                       application_stop, deploy_language)
    else:
        deploy_request = _handle_existing_application_group(name, application_group_name,
                                                            deploy_region_id, region_id_oss, bucket_name,
                                                            object_name, version_id, application_start,
                                                            application_stop, instance_ids)

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
    instance_id = instance_ids[0] if instance_ids else None
    if instance_id:
        security_group_link = f'https://ecs.console.aliyun.com/server/{instance_id}/group?regionId={deploy_region_id}#/'
    else:
        security_group_link = f'https://ecs.console.aliyun.com/securityGroup/region/{deploy_region_id}'

    return {
        'response': response,
        'service_link': service_link,
        'security_group_link': security_group_link,
        'port': port,
        'deploy_region_id': deploy_region_id,
        'bucket_name': bucket_name,
        'oss_bucket_link': f'https://oss.console.aliyun.com/bucket/oss-cn-hangzhou/{bucket_name}/object',
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
def OOS_GetLastDeploymentInfo(
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
def OOS_GetDeployStatus(
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


@_append_tool
def ECS_DescribeInstances(
        instance_ids: List[str] = Field(description='AlibabaCloud ECS instance ID List (required)'),
        region_id: str = Field(description='AlibabaCloud region ID', default='cn-hangzhou'),
):
    """
    查询指定ECS实例的详细信息。此工具要求必须提供实例ID列表，避免随意查询所有实例。
    注意：此工具仅用于查询用户明确指定的实例信息，不允许用于扫描或枚举所有实例。
    """
    logger.info(f"[ECS_DescribeInstances] Input parameters: region_id={region_id}, instance_ids={instance_ids}")
    
    if not instance_ids:
        raise ValueError("instance_ids is required and cannot be empty")
    
    describe_instances_request = ecs_20140526_models.DescribeInstancesRequest(
        region_id=region_id,
        instance_ids=json.dumps(instance_ids)
    )
    
    response = _describe_instances_with_retry(region_id, describe_instances_request)
    logger.info(f"[ECS_DescribeInstances] Response: {json.dumps(str(response), ensure_ascii=False)}")
    return response


def _handle_new_application_group(client, name, application_group_name, deploy_region_id,
                                  region_id_oss, bucket_name, object_name, version_id,
                                  is_internal_oss, port, instance_ids, application_start,
                                  application_stop, deploy_language):
    logger.info(f"[code_deploy] Application group '{application_group_name}' does not exist, creating it...")
    create_application_group_request = oos_20190601_models.CreateApplicationGroupRequest(
        region_id=APPLICATION_MANAGEMENT_REGION_ID,
        application_name=name,
        deploy_region_id=deploy_region_id,
        name=application_group_name
    )
    client.create_application_group(create_application_group_request)
    logger.info(f"[code_deploy] Application group '{application_group_name}' created successfully")

    # 确保所有实例都打上 tag（包括第一个实例）
    _ensure_instances_tagged(deploy_region_id, name, application_group_name, instance_ids)

    deploy_parameters = _create_deploy_parameters(
        name, application_group_name, region_id_oss, bucket_name,
        object_name, version_id, is_internal_oss, port, instance_ids,
        application_start, application_stop, deploy_language
    )

    return oos_20190601_models.DeployApplicationGroupRequest(
        region_id=APPLICATION_MANAGEMENT_REGION_ID,
        application_name=name,
        name=application_group_name,
        deploy_parameters=json.dumps(deploy_parameters)
    )


def _handle_existing_application_group(name, application_group_name, deploy_region_id, region_id_oss, bucket_name,
                                       object_name, version_id, application_start, application_stop, instance_ids):
    logger.info(f"[code_deploy] Application group '{application_group_name}' already exists, skipping creation")
    
    # 确保所有实例都打上 tag（应用分组已存在的情况）
    _ensure_instances_tagged(deploy_region_id, name, application_group_name, instance_ids)

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


def _describe_instances_with_retry(deploy_region_id: str, describe_instances_request):
    """
    带重试逻辑的 describe_instances 调用
    处理 UnretryableException 和 "Bad file descriptor" 错误，最多重试3次
    
    Args:
        deploy_region_id: 部署区域ID
        describe_instances_request: DescribeInstancesRequest 对象
    
    Returns:
        describe_instances 的响应对象
    
    Raises:
        如果所有重试都失败，抛出最后一次的异常
    """
    max_retries = 3
    last_exception = None
    
    for attempt in range(max_retries):
        try:
            ecs_client = create_ecs_client(region_id=deploy_region_id)
            response = ecs_client.describe_instances(describe_instances_request)
            return response
        except Exception as e:
            last_exception = e
            error_msg = str(e)
            error_type = type(e).__name__
            # 检查是否是 UnretryableException 且包含 "Bad file descriptor"
            is_unretryable = 'UnretryableException' in error_type or 'UnretryableException' in error_msg
            has_bad_fd = 'Bad file descriptor' in error_msg or 'bad file descriptor' in error_msg.lower()
            
            if is_unretryable and has_bad_fd and attempt < max_retries - 1:
                wait_time = (attempt + 1) * 1  # 递增等待时间：1秒、2秒、3秒
                logger.warning(f"[_describe_instances_with_retry] UnretryableException with Bad file descriptor (attempt {attempt + 1}/{max_retries}), retrying after {wait_time}s: {e}")
                time.sleep(wait_time)
            else:
                # 如果不是可重试的错误，或者已经重试了3次，直接抛出异常
                logger.error(f"[_describe_instances_with_retry] Error calling describe_instances: {e}")
                raise
    
    # 如果所有重试都失败了，抛出最后一次的异常
    if last_exception:
        logger.error(f"[_describe_instances_with_retry] All retries failed, raising last exception: {last_exception}")
        raise last_exception


def _check_ecs_instances_exist(deploy_region_id: str, instance_ids: list) -> Tuple[bool, list]:
    """
    检查 ECS 实例是否存在
    
    Returns:
        (all_exist, missing_instance_ids): 如果所有实例都存在返回 (True, [])，否则返回 (False, [缺失的实例ID列表])
    """
    if not instance_ids:
        return True, []
    
    describe_instances_request = ecs_20140526_models.DescribeInstancesRequest(
        region_id=deploy_region_id,
        instance_ids=json.dumps(instance_ids)
    )
    
    response = _describe_instances_with_retry(deploy_region_id, describe_instances_request)
    
    existing_instance_ids = set()
    if response.body and response.body.instances and response.body.instances.instance:
        for instance in response.body.instances.instance:
            if instance.instance_id:
                existing_instance_ids.add(instance.instance_id)
    
    missing_instance_ids = [inst_id for inst_id in instance_ids if inst_id not in existing_instance_ids]
    
    if missing_instance_ids:
        logger.warning(f"[_check_ecs_instances_exist] Missing instances: {missing_instance_ids}")
        return False, missing_instance_ids
    else:
        logger.info(f"[_check_ecs_instances_exist] All instances exist: {instance_ids}")
        return True, []


def _check_instance_has_tag(deploy_region_id: str, instance_id: str, tag_key: str, tag_value: str) -> bool:
    """
    检查 ECS 实例是否已经有指定的 tag
    
    Returns:
        bool: 如果实例已经有指定的 tag 返回 True，否则返回 False
    """
    describe_instances_request = ecs_20140526_models.DescribeInstancesRequest(
        region_id=deploy_region_id,
        instance_ids=json.dumps([instance_id])
    )
    
    try:
        response = _describe_instances_with_retry(deploy_region_id, describe_instances_request)
        if response.body and response.body.instances and response.body.instances.instance:
            instance = response.body.instances.instance[0]
            if instance.tags and instance.tags.tag is not None:
                for tag in instance.tags.tag:
                    if tag.tag_key == tag_key and tag.tag_value == tag_value:
                        logger.info(f"[_check_instance_has_tag] Instance {instance_id} already has tag {tag_key}={tag_value}")
                        return True
        logger.info(f"[_check_instance_has_tag] Instance {instance_id} does not have tag {tag_key}={tag_value}")
        return False
    except Exception as e:
        # 如果查询失败，假设没有 tag，继续打 tag
        logger.warning(f"[_check_instance_has_tag] Error checking tag for instance {instance_id}: {e}")
        return False


def _ensure_instances_tagged(deploy_region_id: str, name: str, application_group_name: str, instance_ids: list):
    """
    确保所有 ECS 实例都打上了指定的 tag
    如果实例没有 tag，则为其打上 tag
    """
    if not instance_ids:
        return
    
    tag_key = f'app-{name}'
    tag_value = application_group_name
    
    # 找出需要打 tag 的实例
    instances_to_tag = []
    for instance_id in instance_ids:
        if not _check_instance_has_tag(deploy_region_id, instance_id, tag_key, tag_value):
            instances_to_tag.append(instance_id)
    
    if not instances_to_tag:
        logger.info(f"[_ensure_instances_tagged] All instances already have tag {tag_key}={tag_value}")
        return
    
    # 为需要打 tag 的实例打 tag
    logger.info(f"[_ensure_instances_tagged] Tagging instances: {instances_to_tag}")
    ecs_client = create_ecs_client(region_id=deploy_region_id)
    tag_resources_request = ecs_20140526_models.TagResourcesRequest(
        region_id=deploy_region_id,
        resource_type='Instance',
        resource_id=instances_to_tag,
        tag=[ecs_20140526_models.TagResourcesRequestTag(
            key=tag_key,
            value=tag_value
        )]
    )
    ecs_client.tag_resources(tag_resources_request)
    logger.info(f"[_ensure_instances_tagged] Successfully tagged instances: {instances_to_tag}")


def _tag_multiple_instances(deploy_region_id, name, application_group_name, instance_ids):
    """
    为多个实例打 tag
    """
    remaining_instance_ids = instance_ids[1:]
    if remaining_instance_ids:
        _ensure_instances_tagged(deploy_region_id, name, application_group_name, remaining_instance_ids)


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
    execution_id = response.body.application_group.execution_id
    list_executions_response = None

    if execution_id:
        try:
            list_executions_request = oos_20190601_models.ListExecutionsRequest(
                execution_id=execution_id
            )
            list_executions_response = client.list_executions(list_executions_request)
        except Exception as e:
            logger.info(f"[_list_application_group_deployment] Error listing executions for application group {application_group_name}: {e}")
            pass

    resp = {
        'info': response.body,
        'status': status,
        'execution_id': execution_id,
        'deploy_execution_info': list_executions_response.body if list_executions_response else None
    }

    return resp


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
                              is_internal_oss, port, instance_ids, application_start, application_stop, deploy_language):
    """
    Create deployment parameters
    """
    PACKAGE_MAP = {
        'docker': 'ACS-Extension-DockerCE-1853370294850618',
        'java': 'ACS-Extension-java-1853370294850618',
        'python': 'ACS-Extension-python-1853370294850618',
        'nodejs': 'ACS-Extension-node-1853370294850618',
        'golang': 'ACS-Extension-golang-1853370294850618',
        'nginx': 'ACS-Extension-nginx-1853370294850618',
        'git': 'ACS-Extension-Git-1853370294850618',
    }
    package_name = PACKAGE_MAP.get(deploy_language, PACKAGE_MAP['docker'])

    return {
        "Parameters": {
            "CreateEcsOption": "ExistECS" if instance_ids else "NewECS",
            "InstanceId": instance_ids[0] if instance_ids else None,
            "ApplicationName": name,
            "Description": "",
            "ZoneId": "cn-hangzhou-b",
            "Port": port,
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
            "PackageName": package_name
        },
        "TemplateName": "oss-revision",
        "ServiceId": "service-af8acc2d6f4044f4b5ea"
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
