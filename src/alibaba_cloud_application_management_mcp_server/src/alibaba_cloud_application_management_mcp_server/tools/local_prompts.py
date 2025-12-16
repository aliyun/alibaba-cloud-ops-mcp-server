"""
本地文件操作和项目部署识别的 MCP Prompts

根据 MCP 协议，prompt 函数应该直接返回 messages 列表。
每个 message 包含 role 和 content。
"""

from typing import List, Dict, Any, Optional
from pydantic import Field

class PromptsList:
    """一个可以同时作为列表和装饰器使用的提示列表"""
    def __init__(self):
        self._list = []
    
    def append(self, func):
        """装饰器：将函数添加到列表中并返回函数本身"""
        self._list.append(func)
        return func
    
    def __iter__(self):
        return iter(self._list)
    
    def __len__(self):
        return len(self._list)


prompts = PromptsList()


@prompts.append
def SetupAndIdentifyProject(
    source_path: str = Field(description="对于 'git' 类型，这是 Git 仓库 URL；对于 'local' 类型，这是本地目录路径", default=""),
    source_type: str = Field(description="代码来源类型，'git' 表示从 Git 仓库克隆，'local' 表示使用本地目录", default="git"),
    destination: str = Field(description="克隆的目标目录（仅当 source_type='git' 时需要）", default=""),
    branch: Optional[str] = Field(description="要克隆的分支名称（可选，仅当 source_type='git' 时需要）", default=None)
):
    """
    从 Git 仓库克隆项目或使用本地目录，并识别项目的部署方式和技术栈。
    
    这个 prompt 会指导 agent 执行以下步骤：
    1. 如果 source_type 是 'git'，使用 CloneGitRepository 工具克隆仓库
    2. 如果 source_type 是 'local'，直接使用本地路径
    3. 使用 IdentifyDeploymentMethod 工具识别项目的部署方式
    4. 返回识别结果，包括包管理器、框架、运行时版本等信息
    """
    messages: List[Dict[str, Any]] = []
    
    if source_type == "git":
        if not source_path:
            raise ValueError("Git 仓库 URL 不能为空")
        if not destination:
            raise ValueError("目标目录不能为空")
        
        messages.append({
            "role": "user",
            "content": f"请帮我从 Git 仓库克隆项目并识别其部署方式。\n\n仓库 URL: {source_path}\n目标目录: {destination}" + (f"\n分支: {branch}" if branch else "")
        })
        
        messages.append({
            "role": "assistant",
            "content": "好的，我将执行以下步骤：\n1. 使用 CloneGitRepository 工具克隆 Git 仓库\n2. 使用 IdentifyDeploymentMethod 工具识别项目的部署方式和技术栈"
        })
        
    elif source_type == "local":
        if not source_path:
            raise ValueError("本地目录路径不能为空")
        
        messages.append({
            "role": "user",
            "content": f"请帮我识别本地项目的部署方式和技术栈。\n\n目录路径: {source_path}"
        })
        
        messages.append({
            "role": "assistant",
            "content": "好的，我将使用 IdentifyDeploymentMethod 工具分析项目目录，识别部署方式和技术栈。"
        })
    else:
        raise ValueError(f"不支持的 source_type: {source_type}，只支持 'git' 或 'local'")
    
    return messages


@prompts.append
def AnalyzeProjectStructure(
    directory: str = Field(description="要分析的项目目录路径", default="")
):
    """
    分析项目结构，识别部署方式、技术栈和配置文件。
    
    这个 prompt 会指导 agent：
    1. 使用 ListDirectory 工具查看项目目录结构
    2. 使用 IdentifyDeploymentMethod 工具识别部署方式
    3. 读取关键配置文件（如 package.json、requirements.txt 等）获取详细信息
    """
    if not directory:
        raise ValueError("目录路径不能为空")
    
    messages = [
        {
            "role": "user",
            "content": f"请帮我分析项目结构，识别部署方式和技术栈。\n\n项目目录: {directory}"
        },
        {
            "role": "assistant",
            "content": "好的，我将执行以下步骤：\n1. 使用 ListDirectory 工具查看项目目录结构\n2. 使用 IdentifyDeploymentMethod 工具识别部署方式和技术栈\n3. 根据识别结果，读取关键配置文件获取详细信息"
        }
    ]
    
    return messages


@prompts.append
def CodeDeployWorkflow(
    source_path: str = Field(description="代码来源路径，可以是本地文件路径或 Git 仓库 URL", default=""),
    source_type: str = Field(description="代码来源类型，'git' 表示从 Git 仓库克隆，'local' 表示使用本地目录", default="local"),
    application_name: str = Field(description="应用名称", default=""),
    deploy_region_id: str = Field(description="部署区域 ID", default="cn-hangzhou"),
    instance_ids: List[str] = Field(description="ECS 实例 ID 列表（可选，如果为空则新建实例）", default=[]),
    bucket_name: str = Field(description="OSS bucket 名称（可选，如果不提供则自动查找或创建）", default=""),
    region_id_oss: str = Field(description="OSS 区域 ID（可选，如果不提供则使用 deploy_region_id）", default="")
):
    """
    完整的代码部署工作流程，包括代码识别、构建、上传和部署。
    
    这个 prompt 会指导 agent 执行以下步骤：
    
    步骤 1：识别部署方式
    - 如果 source_type 是 'git'，使用 CloneGitRepository 工具克隆仓库
    - 如果 source_type 是 'local'，直接使用本地路径
    - 使用本地文件操作工具读取项目文件，识别部署方式（npm/python/java/go 等）
    - 输出：应用部署脚本和构建命令
    
    步骤 2：构建并上传到 OSS
    - 在本地执行构建命令，生成部署产物
    - 使用 OSS_PutObject 工具上传构建产物到 OSS
    - 输出：OSS 文件路径、bucket 名称、object 名称、version_id
    - 注意：如果未提供 bucket_name，code_deploy 工具会自动查找或创建 bucket（通过 tag: app_management=code_deploy）
    
    步骤 3：部署应用
    - 使用 code_deploy 工具调用应用管理 API
    - 依次调用：CreateApplication（如果不存在）、CreateApplicationGroup（如果不存在）、TagResources（可选，如果是已有资源需要打 tag）、DeployApplicationGroup
    - 输出：部署状态和服务链接
    """
    if not source_path:
        raise ValueError("代码来源路径不能为空")
    if not application_name:
        raise ValueError("应用名称不能为空")
    
    messages = [
        {
            "role": "user",
            "content": f"""请帮我完成应用的完整部署流程。

应用名称: {application_name}
代码来源: {source_path} ({source_type})
部署区域: {deploy_region_id}
ECS 实例: {instance_ids if instance_ids else '自动创建（未指定，code_deploy 工具会自动创建新实例）'}
OSS Bucket: {bucket_name if bucket_name else '自动查找或创建'}

请按照以下步骤执行：

**重要提示**：
- 如果未提供 instance_ids，code_deploy 工具会自动创建新的 ECS 实例，你不需要手动操作
- 如果未提供 bucket_name，code_deploy 工具会自动查找或创建 OSS bucket

步骤 1：识别部署方式
- {'使用 CloneGitRepository 工具克隆 Git 仓库' if source_type == 'git' else '使用本地路径'}
- 使用本地文件操作工具读取项目文件（package.json、requirements.txt、pom.xml 等）
- 识别项目的部署方式和技术栈（npm、python、java、go 等）
- 生成构建命令和部署脚本

步骤 2：构建并上传到 OSS
- 在本地执行构建命令，生成部署产物（tar.gz、zip 等压缩包）
- 使用 OSS_PutObject 工具上传构建产物
- 记录 OSS 文件信息（bucket_name、object_name、version_id）
- 注意：如果未提供 bucket_name，code_deploy 工具会自动查找或创建 bucket（通过 tag: app_management=code_deploy）

步骤 3：部署应用
- 使用 code_deploy 工具进行部署
- {"传入 instance_ids 参数（用户指定了要使用已有的 ECS 实例）" if instance_ids else "不传入 instance_ids 参数（用户未指定，code_deploy 工具会自动创建新的 ECS 实例）"}
- 传入正确的启动脚本（如果是压缩包，需要包含解压和进入目录的命令）
- 等待部署完成并返回部署状态

**重要提醒**：code_deploy 工具会自动处理 ECS 实例的创建，你不需要手动创建 ECS 实例。"""
        },
        {
            "role": "assistant",
            "content": """好的，我将按照完整的部署流程执行：

1. **识别部署方式**：读取项目文件，识别技术栈和构建方式
2. **构建并上传**：执行构建，处理 OSS bucket（查找或创建），上传产物
3. **部署应用**：调用 code_deploy 工具完成部署

让我开始执行..."""
        }
    ]
    
    return messages


@prompts.append
def DeployApplication(
    user_query: str = Field(description="用户的部署请求，包含应用名称、代码路径等信息", default=""),
    application_name: str = Field(description="应用名称", default=""),
    source_path: str = Field(description="代码来源路径，可以是本地文件路径或 Git 仓库 URL", default=""),
    deploy_region_id: str = Field(description="部署区域 ID", default="cn-hangzhou"),
    instance_ids: List[str] = Field(description="ECS 实例 ID 列表（可选，仅在用户明确指定要使用已有 ECS 实例时传入）", default=[])
):
    """
    当用户提到"完成部署"、"deploy"、"发布"等关键词时，自动触发代码部署流程。
    
    这个 prompt 会引导 agent 执行完整的代码部署流程：
    1. 识别项目的部署方式和技术栈
    2. 检查是否有符合规定的OSS Bucket，指定的tag，如果没有则创建一个，将构建产物上传到 OSS
    3. 使用 code_deploy 工具完成部署
    
    重要提示：
    - 如果用户未明确提到要使用已有的 ECS 实例，则不要传入 instance_ids 参数
    - code_deploy 工具会自动创建新的 ECS 实例，无需手动操作
    - 只有在用户明确指定要使用已有 ECS 实例时，才传入 instance_ids
    
    适用于用户说"帮我部署应用"、"部署这个项目"、"发布到阿里云"等场景。
    """
    # 如果用户提供了查询，尝试从中提取信息
    if user_query:
        # 检查用户是否明确提到要使用已有的 ECS 实例
        use_existing_ecs = any(keyword in user_query.lower() for keyword in ['已有实例', '现有实例', '已有ecs', '现有ecs', '使用实例', '指定实例', 'instance'])
        
        messages = [
            {
                "role": "user",
                "content": f"{user_query}\n\n请帮我完成部署。"
            },
            {
                "role": "assistant",
                "content": f"""
                    好的，我将帮您完成应用的部署流程。让我先了解项目信息，然后执行以下步骤：
                        1. **识别部署方式**：分析项目结构，识别技术栈（npm/python/java/go 等）和构建方式
                        2. **构建并上传**：执行构建命令，生成部署产物，上传到 OSS
                        3. **部署应用**：使用 code_deploy 工具将应用部署到阿里云
                        
                        **重要提示**：
                        - {"用户指定了要使用已有的 ECS 实例，我会在调用 code_deploy 时传入 instance_ids 参数" if use_existing_ecs else "用户未指定要使用已有的 ECS 实例，因此我不会传入 instance_ids 参数"}
                        - code_deploy 工具会自动处理 ECS 实例的创建：如果未传入 instance_ids，工具会自动创建新的 ECS 实例
                        - 你不需要手动创建 ECS 实例，code_deploy 工具会完成所有必要的操作
                        - 同样，如果未提供 bucket_name，code_deploy 工具也会自动查找或创建 OSS bucket
                        
                        让我开始执行...
                    """
            }
        ]
    else:
        # 如果没有用户查询，使用提供的参数
        if not application_name:
            raise ValueError("应用名称不能为空，请提供 application_name 或 user_query")
        
        if not source_path:
            raise ValueError("代码来源路径不能为空，请提供 source_path 或 user_query")
        
        # 调用 CodeDeployWorkflow 的逻辑
        # 检查是否提供了 instance_ids
        has_instance_ids = instance_ids and len(instance_ids) > 0
        
        messages = [
            {
                "role": "user",
                "content": f"""请帮我完成应用的完整部署流程。
                    应用名称: {application_name}
                    代码来源: {source_path}
                    部署区域: {deploy_region_id}
                    {"ECS 实例: " + str(instance_ids) if has_instance_ids else "ECS 实例: 自动创建（未指定，code_deploy 工具会自动创建新实例）"}
                    
                    请按照以下步骤执行：
                    
                    步骤 1：识别部署方式
                    - 使用本地文件操作工具读取项目文件（package.json、requirements.txt、pom.xml 等）
                    - 识别项目的部署方式和技术栈（npm、python、java、go 等）
                    - 生成构建命令和部署脚本
                    
                    步骤 2：构建并上传到 OSS
                    - 在本地执行构建命令，生成部署产物（tar.gz、zip 等压缩包）
                    - 使用 OSS_PutObject 工具上传构建产物
                    - 记录 OSS 文件信息（bucket_name、object_name、version_id）
                    - 注意：如果未提供 bucket_name，code_deploy 工具会自动查找或创建 bucket（通过 tag: app_management=code_deploy）
                    
                    步骤 3：部署应用
                    - 使用 code_deploy 工具进行部署
                    - {"传入 instance_ids 参数（用户指定了要使用已有的 ECS 实例）" if has_instance_ids else "不传入 instance_ids 参数（用户未指定，code_deploy 工具会自动创建新的 ECS 实例）"}
                    - 传入正确的启动脚本（如果是压缩包，需要包含解压和进入目录的命令）
                    - 等待部署完成并返回部署状态
                    
                    **重要提醒**：
                    - 你不需要手动创建 ECS 实例，code_deploy 工具会自动处理
                    - 如果未传入 instance_ids，code_deploy 工具会自动创建新的 ECS 实例
                    - 如果未提供 bucket_name，code_deploy 工具也会自动查找或创建 OSS bucket"""
                                },
                                {
                                    "role": "assistant",
                                    "content": f"""好的，我将按照完整的部署流程执行：
                    
                    1. **识别部署方式**：读取项目文件，识别技术栈和构建方式
                    2. **构建并上传**：执行构建，处理 OSS bucket（查找或创建），上传产物
                    3. **部署应用**：调用 code_deploy 工具完成部署
                       - {"将传入 instance_ids 参数，使用用户指定的 ECS 实例" if has_instance_ids else "不传入 instance_ids 参数，让 code_deploy 工具自动创建新的 ECS 实例"}
                    
                    **重要**：code_deploy 工具会自动处理 ECS 实例的创建，你不需要手动操作。让我开始执行..."""
            }
        ]
    
    return messages

