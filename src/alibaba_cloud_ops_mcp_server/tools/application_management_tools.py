import re
import logging
import tarfile
import zipfile
import tempfile
import shutil

from alibaba_cloud_ops_mcp_server.tools.api_tools import _tools_api_call
from pathlib import Path
import alibabacloud_oss_v2 as oss
from pydantic import Field
from typing import Optional, Tuple, List, Dict, Set
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
        file_path: str = Field(description='Local file path to upload. If the file is not in .code_deploy/release directory, it will be copied there.'),
        deploy_language: str = Field(description='Deploy language, like:docker, java, python, nodejs, golang'),
        port: int = Field(description='Application listening port'),
        project_path: Optional[str] = Field(description='Root path of the project. The .code_deploy directory will be created in this path. If not provided, will try to infer from file_path or use current working directory.'),
        application_start: Optional[str] = Field(default=None, description='**OPTIONAL - DO NOT PROVIDE UNLESS USER EXPLICITLY REQUIRES IT** Application start command script. In normal cases, you should NOT provide this parameter. The system will automatically generate the start command using rule engine based on deployment file analysis and deploy_language. Only provide this parameter when: (1) User explicitly specifies a custom start command, or (2) User provides specific instructions about the start command. The auto-generated command includes defensive checks for file/path existence and proper archive extraction. If you must provide a custom command, ensure it includes defensive checks like "[ -f file ] && command" and handles archive extraction properly.'),
        application_stop: Optional[str] = Field( default=None, description='**OPTIONAL - DO NOT PROVIDE UNLESS USER EXPLICITLY REQUIRES IT** Application stop command script. In normal cases, you should NOT provide this parameter. The system will automatically generate the stop command using rule engine based on deploy_language. Only provide this parameter when: (1) User explicitly specifies a custom stop command, or (2) User provides specific instructions about the stop command. The auto-generated command includes defensive checks and proper process termination.'),
        instance_ids: list = Field(description='AlibabaCloud ECS instance ID List. If empty or not provided, user will be prompted to create ECS instances.', default=None)
):
    """
    将应用部署到阿里云ECS实例。使用阿里云OOS（运维编排服务）的CodeDeploy功能实现自动化部署。

    ## 前置条件（调用此工具前需完成）

    1. **识别项目类型**：读取项目配置文件（package.json、pom.xml、requirements.txt等），确定技术栈和部署语言（通过deploy_language参数传入）
    2. **构建部署产物**：执行构建命令生成压缩包（tar.gz、zip等），保存到 `.code_deploy/release` 目录
    3. **准备ECS实例**：确保目标ECS实例已创建，获取实例ID列表

    ## ⚠️ 重要提示：启动和停止命令参数

    **正常情况下，不需要提供 application_start 和 application_stop 参数！**
    
    - 系统会自动通过规则引擎分析部署文件和 deploy_language，自动生成启动和停止命令
    - 自动生成的命令包含所有必要的防御性检查（文件存在性、路径存在性等）
    - 自动生成的命令正确处理压缩包解压、目录切换、后台运行、日志重定向等
    - 对于 Node.js 应用，自动生成的命令会先执行 `npm install` 安装依赖
    
    **只有在以下情况下才需要手动提供这两个参数：**
    1. 用户明确指定了自定义的启动/停止命令
    2. 用户提供了关于启动/停止命令的特殊要求或说明
    
    **调用建议：直接调用工具，不传 application_start 和 application_stop 参数即可。**

    ## 自动生成的命令规范（供参考，了解即可）

    ### 1. 防御性命令设计
    自动生成的命令包含存在性检查，避免因路径/文件/命令不存在导致失败：
    - 压缩包：先检查文件存在再解压 `[ -f app.tar.gz ] && tar -xzf app.tar.gz || exit 1`
    - 可执行文件：检查文件存在再执行 `[ -f start.sh ] && chmod +x start.sh && ./start.sh || exit 1`
    - 命令可用性：检查命令是否存在 `command -v npm >/dev/null 2>&1 || exit 1`
    - 目录切换：先验证路径存在再切换 `[ -d dir ] && cd dir || exit 1`

    ### 2. 压缩包处理规范
    如果产物是压缩包，自动生成的命令会先解压：
    - 使用非交互式命令：`tar -xzf`、`unzip -o`（自动覆盖，无需确认）
    - 解压后执行启动命令，确保路径对应
    - 示例：`tar -xzf app.tar.gz && [ -d app ] && cd app && nohup java -jar app.jar > /root/app.log 2>&1 &`

    ### 3. 后台运行与日志
    自动生成的启动命令使用后台运行并重定向日志：
    - 格式：`nohup <command> > /root/app.log 2>&1 &`
    - 说明：nohup保持后台运行，`>` 重定向标准输出，`2>&1` 合并错误输出，`&` 后台执行

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
    
    # 如果未提供启动/停止命令，尝试通过规则引擎生成
    logger.info(f"[DEBUG code_deploy] ===== Checking if commands need to be generated ======")
    logger.info(f"[DEBUG code_deploy] application_start provided: {application_start is not None}, value: {application_start}")
    logger.info(f"[DEBUG code_deploy] application_stop provided: {application_stop is not None}, value: {application_stop}")
    
    if not application_start or not application_stop:
        logger.info(f"[code_deploy] Attempting to generate commands by rules. "
                   f"application_start provided: {application_start is not None}, "
                   f"application_stop provided: {application_stop is not None}")
        logger.info(f"[DEBUG code_deploy] Calling rule engine with: file_path={file_path}, deploy_language={deploy_language}")
        
        generated_start, generated_stop = _generate_start_stop_commands_by_rules(
            file_path, deploy_language, name, port
        )
        
        logger.info(f"[DEBUG code_deploy] Rule engine returned: generated_start={generated_start is not None}, generated_stop={generated_stop is not None}")
        if generated_start:
            logger.info(f"[DEBUG code_deploy] Generated start command content: {generated_start}")
        if generated_stop:
            logger.info(f"[DEBUG code_deploy] Generated stop command content: {generated_stop}")
        
        if not application_start and generated_start:
            application_start = generated_start
            logger.info(f"[code_deploy] Auto-generated start command: {application_start}")
            logger.info(f"[DEBUG code_deploy] Successfully assigned generated start command")
        elif not application_start:
            logger.warning(f"[code_deploy] Failed to generate start command by rules, "
                          f"will require manual input or LLM generation")
            logger.info(f"[DEBUG code_deploy] ===== START COMMAND GENERATION FAILED ======")
            logger.info(f"[DEBUG code_deploy] file_path: {file_path}")
            logger.info(f"[DEBUG code_deploy] deploy_language: {deploy_language}")
            logger.info(f"[DEBUG code_deploy] generated_start: {generated_start}")
            return {
                'error': 'START_COMMAND_REQUIRED',
                'message': '无法通过规则引擎自动生成启动命令，请手动提供 application_start 参数并再次调用OOS_CodeDeploy',
                'file_path': file_path,
                'deploy_language': deploy_language,
                'instructions': f'''
                    ## 启动命令生成失败
                    
                    系统尝试通过规则引擎自动生成启动命令，但未能成功识别。
                    
                    **文件路径**: {file_path}
                    **部署语言**: {deploy_language}
                    
                    请根据以下信息手动提供启动命令：
                    1. 如果文件是压缩包（tar.gz、zip等），需要先解压
                    2. 启动命令必须包含防御性检查（检查文件/路径是否存在）
                    3. 启动命令必须使用后台运行并重定向日志：`nohup <command> > /root/app.log 2>&1 &`
                    
                    示例：
                    - Java: `[ -f app.tar.gz ] && tar -xzf app.tar.gz && [ -f app/app.jar ] && nohup java -jar app/app.jar > /root/app.log 2>&1 &`
                    - Python: `[ -f app.tar.gz ] && tar -xzf app.tar.gz && [ -f app/app.py ] && nohup python app/app.py > /root/app.log 2>&1 &`
                    - Node.js: `[ -f app.tar.gz ] && tar -xzf app.tar.gz && [ -f app/package.json ] && nohup npm start > /root/app.log 2>&1 &`
                '''
            }
        
        if not application_stop and generated_stop:
            application_stop = generated_stop
            logger.info(f"[code_deploy] Auto-generated stop command: {application_stop}")
    else:
        logger.info(f"[DEBUG code_deploy] Both commands provided, skipping rule engine")
    
    logger.info(f"[DEBUG code_deploy] ===== Final command assignment ======")
    logger.info(f"[DEBUG code_deploy] Final application_start: {application_start}")
    logger.info(f"[DEBUG code_deploy] Final application_stop: {application_stop}")
    
    region_id_oss = 'cn-hangzhou'
    is_internal_oss = True if deploy_region_id.lower() == 'cn-hangzhou' else False
    # Log input parameters
    logger.info(f"[code_deploy] Input parameters: name={name}, deploy_region_id={deploy_region_id}, "
                f"application_group_name={application_group_name}, instance_ids={instance_ids}, "
                f"region_id_oss={region_id_oss}, object_name={object_name}, "
                f"is_internal_oss={is_internal_oss}, port={port}, "
                f"application_start={application_start}, application_stop={application_stop}")

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


def _extract_top_level_dir(members: List[str]) -> Optional[str]:
    """
    从压缩包成员列表中提取顶级目录名
    
    如果所有文件都在同一个顶级目录下，返回该目录名；否则返回 None
    """
    if not members:
        return None
    
    top_level = set()
    for member in members:
        parts = member.split('/')
        if parts[0]:
            top_level.add(parts[0])
    
    logger.info(f"[DEBUG _extract_top_level_dir] Top-level items: {list(top_level)}")
    
    if len(top_level) == 1:
        return list(top_level)[0]
    return None


def _analyze_deployment_file(file_path: str) -> Dict:
    """
    分析部署文件，返回文件类型和内容列表
    
    Returns:
        {
            'file_type': 'archive' | 'directory' | 'file',
            'archive_type': 'tar.gz' | 'tar' | 'zip' | None,
            'file_name': str,
            'files_in_archive': List[str],  # 压缩包内的文件列表
            'extracted_dir_name': Optional[str],  # 解压后的目录名（如果有）
        }
    """
    logger.info(f"[DEBUG _analyze_deployment_file] Starting analysis for: {file_path}")
    file_path_obj = Path(file_path)
    
    if not file_path_obj.exists():
        logger.warning(f"[_analyze_deployment_file] File does not exist: {file_path}")
        return {'file_type': 'unknown', 'file_name': file_path_obj.name}
    
    result = {
        'file_type': 'file',
        'archive_type': None,
        'file_name': file_path_obj.name,
        'files_in_archive': [],
        'extracted_dir_name': None,
    }
    
    file_name_lower = file_path_obj.name.lower()
    
    # 处理 tar.gz 和 tar 文件
    if file_name_lower.endswith('.tar.gz') or file_name_lower.endswith('.tgz'):
        result['file_type'] = 'archive'
        result['archive_type'] = 'tar.gz'
        try:
            with tarfile.open(file_path, 'r:gz') as tar:
                members = tar.getnames()
                result['files_in_archive'] = members
                result['extracted_dir_name'] = _extract_top_level_dir(members)
                logger.info(f"[DEBUG _analyze_deployment_file] tar.gz: {len(members)} files, extracted_dir: {result['extracted_dir_name']}")
        except Exception as e:
            logger.warning(f"[_analyze_deployment_file] Failed to read tar.gz: {e}")
    
    elif file_name_lower.endswith('.tar'):
        result['file_type'] = 'archive'
        result['archive_type'] = 'tar'
        try:
            with tarfile.open(file_path, 'r') as tar:
                members = tar.getnames()
                result['files_in_archive'] = members
                result['extracted_dir_name'] = _extract_top_level_dir(members)
                logger.info(f"[DEBUG _analyze_deployment_file] tar: {len(members)} files, extracted_dir: {result['extracted_dir_name']}")
        except Exception as e:
            logger.warning(f"[_analyze_deployment_file] Failed to read tar: {e}")
    
    elif file_name_lower.endswith('.zip'):
        result['file_type'] = 'archive'
        result['archive_type'] = 'zip'
        try:
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                members = zip_ref.namelist()
                result['files_in_archive'] = members
                result['extracted_dir_name'] = _extract_top_level_dir(members)
                logger.info(f"[DEBUG _analyze_deployment_file] zip: {len(members)} files, extracted_dir: {result['extracted_dir_name']}")
        except Exception as e:
            logger.warning(f"[_analyze_deployment_file] Failed to read zip: {e}")
    else:
        logger.info(f"[DEBUG _analyze_deployment_file] Not a recognized archive type")
    
    logger.info(f"[DEBUG _analyze_deployment_file] Result: {json.dumps(result, ensure_ascii=False, default=str)}")
    return result


def _find_executable_files(files_list: List[str], deploy_language: str) -> Dict[str, List[str]]:
    """
    在文件列表中查找可执行文件
    
    Returns:
        {
            'jar_files': List[str],
            'py_files': List[str],
            'js_files': List[str],
            'go_binaries': List[str],
            'shell_scripts': List[str],
            'package_json': Optional[str],
            'requirements_txt': Optional[str],
            'dockerfile': Optional[str],
        }
    """
    logger.info(f"[DEBUG _find_executable_files] Starting search in {len(files_list)} files for language: {deploy_language}")
    
    result = {
        'jar_files': [],
        'py_files': [],
        'js_files': [],
        'go_binaries': [],
        'shell_scripts': [],
        'package_json': None,
        'requirements_txt': None,
        'dockerfile': None,
    }
    
    for file_path in files_list:
        file_name = file_path.split('/')[-1].lower()
        
        # Java
        if file_name.endswith('.jar'):
            result['jar_files'].append(file_path)
            logger.info(f"[DEBUG _find_executable_files] Found JAR file: {file_path}")
        # Python
        elif file_name.endswith('.py'):
            result['py_files'].append(file_path)
            logger.info(f"[DEBUG _find_executable_files] Found Python file: {file_path}")
        # Node.js
        elif file_name == 'package.json':
            result['package_json'] = file_path
            logger.info(f"[DEBUG _find_executable_files] Found package.json: {file_path}")
        elif file_name.endswith('.js'):
            result['js_files'].append(file_path)
            logger.info(f"[DEBUG _find_executable_files] Found JS file: {file_path}")
        # Go - 只在 golang 语言时查找潜在的二进制文件
        # 排除常见的非二进制文件（文档、配置等）
        elif deploy_language == 'golang':
            # 排除列表：常见的非二进制文件名
            non_binary_names = {
                'readme', 'license', 'makefile', 'dockerfile', 'changelog',
                'contributing', 'authors', 'version', 'manifest', 'config',
                'gitignore', 'dockerignore', 'editorconfig', 'env'
            }
            file_name_no_ext = file_name.split('.')[0] if '.' in file_name else file_name
            # 检查是否是潜在的 Go 二进制：没有扩展名（或只有一个点），且不在排除列表中
            has_extension = '.' in file_name and not file_name.startswith('.')
            if not has_extension and file_name_no_ext.lower() not in non_binary_names:
                result['go_binaries'].append(file_path)
                logger.info(f"[DEBUG _find_executable_files] Found potential Go binary: {file_path}")
        # Shell scripts
        elif file_name.endswith('.sh'):
            result['shell_scripts'].append(file_path)
            logger.info(f"[DEBUG _find_executable_files] Found shell script: {file_path}")
        # Python requirements
        elif file_name == 'requirements.txt':
            result['requirements_txt'] = file_path
            logger.info(f"[DEBUG _find_executable_files] Found requirements.txt: {file_path}")
        # Dockerfile
        elif file_name == 'dockerfile' and not file_path.lower().endswith('.dockerignore'):
            result['dockerfile'] = file_path
            logger.info(f"[DEBUG _find_executable_files] Found Dockerfile: {file_path}")
    
    logger.info(f"[DEBUG _find_executable_files] Search results: jar_files={len(result['jar_files'])}, "
                f"py_files={len(result['py_files'])}, js_files={len(result['js_files'])}, "
                f"go_binaries={len(result['go_binaries'])}, shell_scripts={len(result['shell_scripts'])}, "
                f"package_json={result['package_json']}, requirements_txt={result['requirements_txt']}, "
                f"dockerfile={result['dockerfile']}")
    
    return result


def _generate_start_command_by_rules(
    file_path: str,
    deploy_language: str,
    file_analysis: Dict,
    extracted_dir_name: Optional[str] = None,
    application_name: Optional[str] = None,
    port: Optional[int] = None
) -> Optional[str]:
    """
    根据规则生成启动命令
    
    Returns:
        生成的启动命令，如果无法通过规则生成则返回 None
    """
    logger.info(f"[DEBUG _generate_start_command_by_rules] Starting command generation")
    logger.info(f"[DEBUG _generate_start_command_by_rules] Input: file_path={file_path}, "
               f"deploy_language={deploy_language}, extracted_dir_name={extracted_dir_name}")
    logger.info(f"[DEBUG _generate_start_command_by_rules] File analysis: {json.dumps(file_analysis, ensure_ascii=False, default=str)}")
    
    file_name = Path(file_path).name
    file_name_lower = file_name.lower()
    logger.info(f"[DEBUG _generate_start_command_by_rules] File name: {file_name}")
    
    # 判断是否需要解压
    is_archive = file_analysis['file_type'] == 'archive'
    logger.info(f"[DEBUG _generate_start_command_by_rules] Is archive: {is_archive}")
    extract_cmd = ""
    work_dir = ""
    
    if is_archive:
        archive_type = file_analysis['archive_type']
        logger.info(f"[DEBUG _generate_start_command_by_rules] Archive type: {archive_type}")
        if archive_type == 'tar.gz':
            extract_cmd = f"[ -f {file_name} ] && tar -xzf {file_name} || exit 1"
            logger.info(f"[DEBUG _generate_start_command_by_rules] Generated tar.gz extract command: {extract_cmd}")
        elif archive_type == 'tar':
            extract_cmd = f"[ -f {file_name} ] && tar -xf {file_name} || exit 1"
            logger.info(f"[DEBUG _generate_start_command_by_rules] Generated tar extract command: {extract_cmd}")
        elif archive_type == 'zip':
            extract_cmd = f"[ -f {file_name} ] && unzip -o {file_name} || exit 1"
            logger.info(f"[DEBUG _generate_start_command_by_rules] Generated zip extract command: {extract_cmd}")
        
        # 如果有明确的解压目录，使用它
        if extracted_dir_name:
            work_dir = f" && [ -d {extracted_dir_name} ] && cd {extracted_dir_name} || exit 1"
            logger.info(f"[DEBUG _generate_start_command_by_rules] Using extracted directory: {extracted_dir_name}, work_dir: {work_dir}")
        else:
            # 如果没有明确目录，假设解压到当前目录
            work_dir = ""
            logger.info(f"[DEBUG _generate_start_command_by_rules] No extracted directory, assuming current directory")
    
    # 根据语言类型生成命令
    files_in_archive = file_analysis.get('files_in_archive', [])
    logger.info(f"[DEBUG _generate_start_command_by_rules] Files in archive: {len(files_in_archive)} files")
    executable_files = _find_executable_files(files_in_archive, deploy_language)
    
    start_cmd = ""
    logger.info(f"[DEBUG _generate_start_command_by_rules] Processing deploy_language: {deploy_language}")
    
    if deploy_language == 'java':
        logger.info(f"[DEBUG _generate_start_command_by_rules] Processing Java application")
        # Java 应用：查找 jar 文件
        jar_files = executable_files['jar_files']
        logger.info(f"[DEBUG _generate_start_command_by_rules] Found {len(jar_files)} JAR files: {jar_files}")
        if jar_files:
            # 使用第一个找到的 jar 文件
            jar_file = jar_files[0].split('/')[-1]  # 只取文件名
            logger.info(f"[DEBUG _generate_start_command_by_rules] Selected JAR file (filename only): {jar_file}")
            if is_archive and extracted_dir_name:
                jar_file = f"{extracted_dir_name}/{jar_file}"
                logger.info(f"[DEBUG _generate_start_command_by_rules] JAR file with extracted dir: {jar_file}")
            elif is_archive:
                jar_file = jar_file  # 假设解压到当前目录
                logger.info(f"[DEBUG _generate_start_command_by_rules] JAR file in current dir: {jar_file}")
            start_cmd = f"[ -f {jar_file} ] && nohup java -jar {jar_file} > /root/app.log 2>&1 &"
            logger.info(f"[DEBUG _generate_start_command_by_rules] Generated Java start command: {start_cmd}")
        else:
            logger.info(f"[DEBUG _generate_start_command_by_rules] No JAR files found, using first common name with defensive check")
            # 尝试第一个常见的 jar 文件名（带防御性检查，如果不存在会跳过）
            common_jar_names = ['app.jar', 'application.jar', 'main.jar', 'server.jar']
            jar_name = common_jar_names[0]  # 使用第一个作为默认
            if is_archive and extracted_dir_name:
                test_path = f"{extracted_dir_name}/{jar_name}"
            else:
                test_path = jar_name
            logger.info(f"[DEBUG _generate_start_command_by_rules] Using common JAR name: {test_path}")
            # 命令已包含防御性检查，如果文件不存在会失败
            start_cmd = f"[ -f {test_path} ] && nohup java -jar {test_path} > /root/app.log 2>&1 &"
    
    elif deploy_language == 'python':
        logger.info(f"[DEBUG _generate_start_command_by_rules] Processing Python application")
        # Python 应用：查找 py 文件或 requirements.txt
        py_files = executable_files['py_files']
        logger.info(f"[DEBUG _generate_start_command_by_rules] Found {len(py_files)} Python files: {py_files}")
        if py_files:
            # 优先查找 main.py, app.py, run.py, server.py
            preferred_names = ['main.py', 'app.py', 'run.py', 'server.py', 'application.py']
            logger.info(f"[DEBUG _generate_start_command_by_rules] Looking for preferred Python files: {preferred_names}")
            py_file = None
            for preferred in preferred_names:
                for py_path in py_files:
                    if py_path.endswith(preferred):
                        py_file = py_path.split('/')[-1]
                        logger.info(f"[DEBUG _generate_start_command_by_rules] Found preferred Python file: {py_file} (from {py_path})")
                        break
                if py_file:
                    break
            
            if not py_file and py_files:
                py_file = py_files[0].split('/')[-1]
                logger.info(f"[DEBUG _generate_start_command_by_rules] Using first Python file: {py_file}")
            
            if py_file:
                if is_archive and extracted_dir_name:
                    py_file = f"{extracted_dir_name}/{py_file}"
                    logger.info(f"[DEBUG _generate_start_command_by_rules] Python file with extracted dir: {py_file}")
                else:
                    logger.info(f"[DEBUG _generate_start_command_by_rules] Python file in current dir: {py_file}")
                start_cmd = f"[ -f {py_file} ] && nohup python {py_file} > /root/app.log 2>&1 &"
                logger.info(f"[DEBUG _generate_start_command_by_rules] Generated Python start command: {start_cmd}")
        else:
            logger.info(f"[DEBUG _generate_start_command_by_rules] No Python files found, using first common name with defensive check")
            # 尝试第一个常见的 Python 文件名（带防御性检查，如果不存在会跳过）
            common_py_names = ['app.py', 'main.py', 'run.py', 'server.py']
            py_name = common_py_names[0]  # 使用第一个作为默认
            if is_archive and extracted_dir_name:
                test_path = f"{extracted_dir_name}/{py_name}"
            else:
                test_path = py_name
            logger.info(f"[DEBUG _generate_start_command_by_rules] Using common Python name: {test_path}")
            # 命令已包含防御性检查，如果文件不存在会失败
            start_cmd = f"[ -f {test_path} ] && nohup python {test_path} > /root/app.log 2>&1 &"
    
    elif deploy_language == 'nodejs':
        logger.info(f"[DEBUG _generate_start_command_by_rules] Processing Node.js application")
        # Node.js 应用：查找 package.json
        if executable_files['package_json']:
            package_json_path = executable_files['package_json']
            logger.info(f"[DEBUG _generate_start_command_by_rules] Found package.json: {package_json_path}")
            if is_archive and extracted_dir_name:
                package_json_dir = extracted_dir_name
            else:
                package_json_dir = "."
            logger.info(f"[DEBUG _generate_start_command_by_rules] Package.json directory: {package_json_dir}")
            
            # 检查是否有 start.sh
            shell_scripts = executable_files['shell_scripts']
            logger.info(f"[DEBUG _generate_start_command_by_rules] Found {len(shell_scripts)} shell scripts: {shell_scripts}")
            start_script = None
            for script in shell_scripts:
                if 'start' in script.lower():
                    start_script = script.split('/')[-1]
                    logger.info(f"[DEBUG _generate_start_command_by_rules] Found start script: {start_script}")
                    break
            
            if start_script:
                logger.info(f"[DEBUG _generate_start_command_by_rules] Found start script: {start_script}")
                # 即使有 start.sh，也先执行 npm install 确保依赖已安装
                # 如果 start.sh 内部已经包含 npm install，这里执行也不会出错（npm install 是幂等的）
                # 注意：如果 extracted_dir_name 存在，work_dir 会在命令组合阶段处理 cd，所以这里使用相对路径
                # 如果 extracted_dir_name 不存在，文件解压到当前目录，也使用相对路径
                script_path_for_cmd = start_script  # 使用相对路径（文件名），因为 work_dir 会处理 cd 或已在当前目录
                start_cmd = f"command -v npm >/dev/null 2>&1 && [ -f package.json ] && npm install && [ -f {script_path_for_cmd} ] && chmod +x {script_path_for_cmd} && nohup ./{script_path_for_cmd} > /root/app.log 2>&1 &"
                logger.info(f"[DEBUG _generate_start_command_by_rules] Generated Node.js start command with script (with npm install): {start_cmd}")
            else:
                # 使用 npm start，必须先执行 npm install
                logger.info(f"[DEBUG _generate_start_command_by_rules] No start script found, using npm start with npm install")
                # 注意：如果 extracted_dir_name 存在，work_dir 会在命令组合阶段处理 cd
                # 如果 extracted_dir_name 不存在，文件解压到当前目录
                # 两种情况都使用相对路径 package.json
                start_cmd = f"command -v npm >/dev/null 2>&1 && [ -f package.json ] && npm install && nohup npm start > /root/app.log 2>&1 &"
                logger.info(f"[DEBUG _generate_start_command_by_rules] Generated Node.js start command with npm (with npm install): {start_cmd}")
        else:
            logger.info(f"[DEBUG _generate_start_command_by_rules] No package.json found, trying to find JS files")
            # 尝试查找 js 文件
            js_files = executable_files['js_files']
            logger.info(f"[DEBUG _generate_start_command_by_rules] Found {len(js_files)} JS files: {js_files}")
            if js_files:
                # 优先查找 index.js, app.js, server.js
                preferred_names = ['index.js', 'app.js', 'server.js', 'main.js']
                logger.info(f"[DEBUG _generate_start_command_by_rules] Looking for preferred JS files: {preferred_names}")
                js_file = None
                for preferred in preferred_names:
                    for js_path in js_files:
                        if js_path.endswith(preferred):
                            js_file = js_path.split('/')[-1]
                            logger.info(f"[DEBUG _generate_start_command_by_rules] Found preferred JS file: {js_file} (from {js_path})")
                            break
                    if js_file:
                        break
                
                if not js_file and js_files:
                    js_file = js_files[0].split('/')[-1]
                    logger.info(f"[DEBUG _generate_start_command_by_rules] Using first JS file: {js_file}")
                
                if js_file:
                    if is_archive and extracted_dir_name:
                        js_file = f"{extracted_dir_name}/{js_file}"
                        logger.info(f"[DEBUG _generate_start_command_by_rules] JS file with extracted dir: {js_file}")
                    else:
                        logger.info(f"[DEBUG _generate_start_command_by_rules] JS file in current dir: {js_file}")
                    start_cmd = f"[ -f {js_file} ] && nohup node {js_file} > /root/app.log 2>&1 &"
                    logger.info(f"[DEBUG _generate_start_command_by_rules] Generated Node.js start command: {start_cmd}")
                else:
                    logger.info(f"[DEBUG _generate_start_command_by_rules] Failed to determine JS file")
                    return None
            else:
                logger.info(f"[DEBUG _generate_start_command_by_rules] No JS files found, cannot generate command")
                return None
    
    elif deploy_language == 'golang':
        logger.info(f"[DEBUG _generate_start_command_by_rules] Processing Golang application")
        # Go 应用：查找二进制文件
        go_binaries = executable_files['go_binaries']
        logger.info(f"[DEBUG _generate_start_command_by_rules] Found {len(go_binaries)} potential Go binaries: {go_binaries}")
        # Go 二进制文件通常没有扩展名，且名称可能包含路径
        # 尝试查找常见的二进制文件名
        common_bin_names = ['app', 'main', 'server', 'application']
        logger.info(f"[DEBUG _generate_start_command_by_rules] Looking for common binary names: {common_bin_names}")
        binary_file = None
        
        for bin_name in common_bin_names:
            for file_path in files_in_archive:
                file_name_only = file_path.split('/')[-1]
                if file_name_only == bin_name or file_name_only.startswith(bin_name):
                    binary_file = file_path.split('/')[-1]
                    logger.info(f"[DEBUG _generate_start_command_by_rules] Found binary file: {binary_file} (from {file_path})")
                    break
            if binary_file:
                break
        
        if binary_file:
            if is_archive and extracted_dir_name:
                binary_file = f"{extracted_dir_name}/{binary_file}"
                logger.info(f"[DEBUG _generate_start_command_by_rules] Binary file with extracted dir: {binary_file}")
            else:
                logger.info(f"[DEBUG _generate_start_command_by_rules] Binary file in current dir: {binary_file}")
            start_cmd = f"[ -f {binary_file} ] && chmod +x {binary_file} && nohup ./{binary_file} > /root/app.log 2>&1 &"
            logger.info(f"[DEBUG _generate_start_command_by_rules] Generated Golang start command: {start_cmd}")
        else:
            logger.info(f"[DEBUG _generate_start_command_by_rules] No binary found, trying base filename")
            # 尝试直接使用文件名（去掉扩展名）
            base_name = file_name.rsplit('.', 1)[0] if '.' in file_name else file_name
            logger.info(f"[DEBUG _generate_start_command_by_rules] Base filename: {base_name}")
            if is_archive and extracted_dir_name:
                test_path = f"{extracted_dir_name}/{base_name}"
            else:
                test_path = base_name
            logger.info(f"[DEBUG _generate_start_command_by_rules] Testing path: {test_path}")
            start_cmd = f"[ -f {test_path} ] && chmod +x {test_path} && nohup ./{test_path} > /root/app.log 2>&1 & || true"
            logger.info(f"[DEBUG _generate_start_command_by_rules] Generated Golang start command with fallback: {start_cmd}")
            if not start_cmd:
                logger.info(f"[DEBUG _generate_start_command_by_rules] Failed to generate Golang start command")
                return None
    
    elif deploy_language == 'docker':
        logger.info(f"[DEBUG _generate_start_command_by_rules] Processing Docker application")
        # Docker 应用：检查是否有 Dockerfile，然后生成 docker build 和 docker run 命令
        dockerfile_path = executable_files.get('dockerfile')
        
        if not dockerfile_path:
            logger.info(f"[DEBUG _generate_start_command_by_rules] No Dockerfile found, returning None")
            return None
        
        logger.info(f"[DEBUG _generate_start_command_by_rules] Found Dockerfile: {dockerfile_path}")
        
        # 生成 Docker 命令
        # 使用应用名称作为镜像和容器名称的基础（如果没有，使用默认值）
        image_name = (application_name or 'app').lower().replace(' ', '-').replace('_', '-')
        container_name = image_name
        logger.info(f"[DEBUG _generate_start_command_by_rules] Using image name: {image_name}, container name: {container_name}")
        
        # 确定 Dockerfile 的路径
        if is_archive and extracted_dir_name:
            # 如果 Dockerfile 在解压目录中
            dockerfile_dir = extracted_dir_name
            dockerfile_for_build = "Dockerfile"  # 在解压目录中，使用相对路径
        elif is_archive:
            # 解压到当前目录
            dockerfile_dir = "."
            dockerfile_for_build = "Dockerfile"
        else:
            # 不是压缩包，使用文件所在目录
            dockerfile_dir = "."
            dockerfile_for_build = "Dockerfile"
        
        logger.info(f"[DEBUG _generate_start_command_by_rules] Dockerfile directory: {dockerfile_dir}, Dockerfile path for build: {dockerfile_for_build}")
        
        # 构建 Docker 命令
        # 1. 先停止并删除可能存在的旧容器
        # 2. 构建镜像
        # 3. 运行容器
        port_mapping = f"-p {port}:{port} " if port else ""
        logger.info(f"[DEBUG _generate_start_command_by_rules] Port mapping: {port_mapping if port_mapping else 'None'}")
        
        # 检查 Docker 是否安装
        docker_check = "command -v docker >/dev/null 2>&1 && "
        
        # 停止并删除旧容器（如果存在）
        stop_old_container = f"docker stop {container_name} 2>/dev/null || true && docker rm {container_name} 2>/dev/null || true && "
        
        # 构建镜像（检查 Dockerfile 是否存在）
        build_cmd = f"[ -f {dockerfile_for_build} ] && docker build -t {image_name}:latest . && "
        
        # 运行容器
        run_cmd = f"docker run -d --name {container_name} {port_mapping}{image_name}:latest"
        
        # 组合命令
        # 注意：对于 Docker，如果 is_archive 为 true，work_dir 会在命令组合阶段处理 cd
        # 所以这里只需要生成 Docker 相关的命令，不需要额外的 cd_cmd
        start_cmd = f"{docker_check}{stop_old_container}{build_cmd}{run_cmd}"
        logger.info(f"[DEBUG _generate_start_command_by_rules] Generated Docker start command (before work_dir): {start_cmd}")
    
    else:
        # 未知语言类型，返回 None
        logger.info(f"[DEBUG _generate_start_command_by_rules] Unknown deploy_language: {deploy_language}, returning None")
        return None
    
    # 组合命令
    logger.info(f"[DEBUG _generate_start_command_by_rules] Combining commands: is_archive={is_archive}, work_dir={work_dir}, start_cmd={start_cmd}")
    if is_archive:
        if work_dir:
            final_cmd = f"{extract_cmd}{work_dir} && {start_cmd}"
            logger.info(f"[DEBUG _generate_start_command_by_rules] Final command with extract and work_dir: {final_cmd}")
        else:
            final_cmd = f"{extract_cmd} && {start_cmd}"
            logger.info(f"[DEBUG _generate_start_command_by_rules] Final command with extract (no work_dir): {final_cmd}")
    else:
        final_cmd = start_cmd
        logger.info(f"[DEBUG _generate_start_command_by_rules] Final command (no archive): {final_cmd}")
    
    logger.info(f"[DEBUG _generate_start_command_by_rules] Returning final command: {final_cmd}")
    return final_cmd


def _generate_stop_command_by_rules(
    deploy_language: str,
    file_analysis: Dict,
    extracted_dir_name: Optional[str] = None,
    application_name: Optional[str] = None
) -> str:
    """
    根据规则生成停止命令
    
    Returns:
        生成的停止命令（总是返回有效命令，未知语言使用通用命令）
    """
    logger.info(f"[DEBUG _generate_stop_command_by_rules] Generating stop command for language: {deploy_language}")
    
    # 语言到停止命令的映射
    stop_commands = {
        'java': "pkill -f 'java -jar' || true",
        'python': "pkill -f 'python.*\\.py' || true",
        'nodejs': "pkill -f 'node.*\\.js' || pkill -f 'npm start' || true",
        'golang': "pkill -f './app' || pkill -f './main' || pkill -f './server' || true",
    }
    
    # Docker 需要特殊处理（使用容器名）
    if deploy_language == 'docker':
        container_name = (application_name or 'app').lower().replace(' ', '-').replace('_', '-')
        stop_cmd = f"docker stop {container_name} 2>/dev/null || true && docker rm {container_name} 2>/dev/null || true"
    else:
        # 使用映射表，未知语言使用通用命令
        stop_cmd = stop_commands.get(deploy_language, "pkill -f 'app' || true")
    
    logger.info(f"[DEBUG _generate_stop_command_by_rules] Generated stop command: {stop_cmd}")
    return stop_cmd


def _generate_start_stop_commands_by_rules(
    file_path: str,
    deploy_language: str,
    application_name: Optional[str] = None,
    port: Optional[int] = None
) -> Tuple[Optional[str], Optional[str]]:
    """
    根据工程规则生成启动和停止命令
    
    Args:
        file_path: 部署文件路径
        deploy_language: 部署语言类型
        application_name: 应用名称（用于 Docker 容器命名等）
        port: 应用端口（用于 Docker 端口映射等）
    
    Returns:
        (start_command, stop_command): 如果无法通过规则生成则返回 (None, None)
    """
    logger.info(f"[DEBUG _generate_start_stop_commands_by_rules] Starting: file_path={file_path}, "
                f"deploy_language={deploy_language}, application_name={application_name}, port={port}")
    
    try:
        # 分析部署文件
        file_analysis = _analyze_deployment_file(file_path)
        extracted_dir_name = file_analysis.get('extracted_dir_name')
        
        # 生成启动命令
        start_cmd = _generate_start_command_by_rules(
            file_path, deploy_language, file_analysis, extracted_dir_name, application_name, port
        )
        
        # 生成停止命令
        stop_cmd = _generate_stop_command_by_rules(
            deploy_language, file_analysis, extracted_dir_name, application_name
        )
        
        # 记录结果
        if start_cmd:
            logger.info(f"[_generate_start_stop_commands_by_rules] Generated start command: {start_cmd}")
        else:
            logger.warning(f"[_generate_start_stop_commands_by_rules] Failed to generate start command")
        
        logger.info(f"[_generate_start_stop_commands_by_rules] Generated stop command: {stop_cmd}")
        
        return (start_cmd, stop_cmd)
    
    except Exception as e:
        logger.warning(f"[_generate_start_stop_commands_by_rules] Failed to generate commands: {e}")
        return (None, None)
