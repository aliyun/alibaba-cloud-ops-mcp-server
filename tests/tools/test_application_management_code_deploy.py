import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import alibabacloud_oss_v2 as oss
import pytest

from alibaba_cloud_ops_mcp_server.tools import application_management_tools as amt

MODULE = 'alibaba_cloud_ops_mcp_server.tools.application_management_tools'

BASE_ARGS = dict(
    name='demo-app',
    deploy_region_id='cn-hangzhou',
    application_group_name='demo-group',
    object_name='app.tar.gz',
    deploy_language='java',
    port=8080,
)


def call_code_deploy(**overrides):
    """以完整参数调用 OOS_CodeDeploy，避免使用 Field 默认值"""
    kwargs = dict(BASE_ARGS)
    kwargs.setdefault('project_path', '/tmp/project')
    kwargs.setdefault('application_start', 'start.sh')
    kwargs.setdefault('application_stop', 'stop.sh')
    kwargs.setdefault('instance_ids', ['i-1'])
    kwargs.setdefault('file_path', 'app.tar.gz')
    kwargs.update(overrides)
    return amt.OOS_CodeDeploy(**kwargs)


class TestCodeDeployProjectPath:
    """测试 OOS_CodeDeploy 的项目根路径推断逻辑"""

    def test_uses_provided_project_path(self):
        """显式提供 project_path 时直接使用"""
        with patch(f'{MODULE}.set_project_path') as mock_set:
            result = call_code_deploy(project_path='/my/project', instance_ids=None)

            mock_set.assert_called_once_with('/my/project')
            assert result['error'] == 'ECS_INSTANCE_REQUIRED'
            assert '/my/project' not in result['message']

    def test_infers_project_root_from_relative_file_path(self, monkeypatch):
        """未提供 project_path 时，从相对文件路径向上查找项目标识文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir).resolve()
            (project_root / 'package.json').write_text('{}', encoding='utf-8')
            (project_root / 'dist').mkdir()
            (project_root / 'dist' / 'app.tar.gz').write_bytes(b'x')
            monkeypatch.chdir(project_root)

            with patch(f'{MODULE}.set_project_path') as mock_set:
                result = call_code_deploy(
                    project_path=None,
                    file_path=os.path.join('dist', 'app.tar.gz'),
                    instance_ids=[],
                )

                mock_set.assert_called_once_with(str(project_root))
                assert result['error'] == 'ECS_INSTANCE_REQUIRED'

    def test_falls_back_to_file_directory_when_no_project_root(self):
        """向上查找到文件系统根仍未命中项目标识文件时，使用文件所在目录"""
        with patch(f'{MODULE}.set_project_path') as mock_set, \
             patch('pathlib.Path.exists', return_value=False):
            result = call_code_deploy(
                project_path=None,
                file_path='/app.tar.gz',
                instance_ids=None,
            )

            mock_set.assert_called_once_with(str(Path('/app.tar.gz').resolve().parent))
            assert result['error'] == 'ECS_INSTANCE_REQUIRED'

    def test_instance_required_message_includes_links(self):
        """未提供实例 ID 时返回购买与安全组配置引导"""
        with patch(f'{MODULE}.set_project_path'):
            result = call_code_deploy(project_path='/my/project', instance_ids=None)

            assert result['region_id'] == 'cn-hangzhou'
            assert 'ecs-buy.aliyun.com' in result['ecs_purchase_link']
            assert 'securityGroup' in result['security_group_link']
            assert 'port 8080' in result['instructions']


class TestCodeDeployValidation:
    """测试 OOS_CodeDeploy 的前置校验"""

    def test_returns_error_when_instances_missing(self):
        with patch(f'{MODULE}.set_project_path'), \
             patch(f'{MODULE}._check_ecs_instances_exist', return_value=(False, ['i-missing'])):
            result = call_code_deploy(instance_ids=['i-1', 'i-missing'])

            assert result['error'] == 'ECS_INSTANCE_NOT_FOUND'
            assert result['missing_instance_ids'] == ['i-missing']
            assert 'i-missing' in result['instructions']

    def test_raises_when_file_does_not_exist(self, monkeypatch):
        with tempfile.TemporaryDirectory() as tmpdir:
            monkeypatch.chdir(tmpdir)

            with patch(f'{MODULE}.set_project_path'), \
                 patch(f'{MODULE}._check_ecs_instances_exist', return_value=(True, [])), \
                 patch(f'{MODULE}.ensure_code_deploy_dirs'):
                with pytest.raises(FileNotFoundError, match='File does not exist'):
                    call_code_deploy(file_path='missing.tar.gz')


def deploy_patches(release_path, bucket='code-deploy-1234', put_object_resp=None):
    """构造 OOS_CodeDeploy 成功路径所需的依赖 patch"""
    return [
        patch(f'{MODULE}.set_project_path'),
        patch(f'{MODULE}._check_ecs_instances_exist', return_value=(True, [])),
        patch(f'{MODULE}.ensure_code_deploy_dirs'),
        patch(f'{MODULE}.get_release_path', return_value=release_path),
        patch(f'{MODULE}.get_or_create_bucket_for_code_deploy', return_value=bucket),
        patch('alibaba_cloud_ops_mcp_server.tools.oss_tools.OSS_PutObject',
              return_value=put_object_resp or {'version_id': 'v1'}),
        patch(f'{MODULE}.create_client'),
        patch(f'{MODULE}.save_application_info'),
    ]


class TestCodeDeploySuccess:
    """测试 OOS_CodeDeploy 的成功部署路径"""

    def test_copies_file_and_creates_application_and_group(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / 'app.tar.gz'
            source.write_bytes(b'payload')
            release_dir = Path(tmpdir) / 'release'
            release_dir.mkdir()
            release_path = release_dir / 'app.tar.gz'

            stack = deploy_patches(release_path)
            with stack[0], stack[1], stack[2], stack[3], stack[4], stack[5], stack[6], stack[7], \
                 patch(f'{MODULE}._check_application_exists', return_value=False), \
                 patch(f'{MODULE}._check_application_group_exists', return_value=False), \
                 patch(f'{MODULE}._handle_new_application_group') as mock_new, \
                 patch(f'{MODULE}._handle_existing_application_group') as mock_existing:
                result = call_code_deploy(file_path=str(source), instance_ids=['i-1'])

            # 产物被复制到 release 目录
            assert release_path.read_bytes() == b'payload'
            mock_new.assert_called_once()
            mock_existing.assert_not_called()
            assert result['bucket_name'] == 'code-deploy-1234'
            assert result['port'] == 8080
            assert 'appName=demo-app' in result['service_link']
            assert '/server/i-1/group' in result['security_group_link']
            assert 'Deployment Successful' in result['security_group_instructions']

    def test_file_already_in_release_directory_and_existing_group(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            release_path = Path(tmpdir) / 'app.tar.gz'
            release_path.write_bytes(b'payload')

            stack = deploy_patches(release_path, bucket='existing-bucket')
            with stack[0], stack[1], stack[2], stack[3], stack[4], stack[5], stack[6], stack[7], \
                 patch(f'{MODULE}._check_application_exists', return_value=True), \
                 patch(f'{MODULE}._check_application_group_exists', return_value=True), \
                 patch(f'{MODULE}._handle_new_application_group') as mock_new, \
                 patch(f'{MODULE}._handle_existing_application_group') as mock_existing:
                result = call_code_deploy(
                    file_path=str(release_path),
                    deploy_region_id='cn-beijing',
                    instance_ids=['i-2'],
                )

            mock_existing.assert_called_once()
            mock_new.assert_not_called()
            assert result['deploy_region_id'] == 'cn-beijing'
            assert result['bucket_name'] == 'existing-bucket'

    def test_security_group_link_without_usable_instance_id(self):
        """实例 ID 列表非空但首个 ID 为空时回退到地域级安全组链接"""
        with tempfile.TemporaryDirectory() as tmpdir:
            release_path = Path(tmpdir) / 'app.tar.gz'
            release_path.write_bytes(b'payload')

            stack = deploy_patches(release_path)
            with stack[0], stack[1], stack[2], stack[3], stack[4], stack[5], stack[6], stack[7], \
                 patch(f'{MODULE}._check_application_exists', return_value=True), \
                 patch(f'{MODULE}._check_application_group_exists', return_value=True), \
                 patch(f'{MODULE}._handle_existing_application_group'):
                result = call_code_deploy(file_path=str(release_path), instance_ids=[''])

            assert result['security_group_link'].endswith('/securityGroup/region/cn-hangzhou')

    def test_saves_deployment_info(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            release_path = Path(tmpdir) / 'app.tar.gz'
            release_path.write_bytes(b'payload')

            stack = deploy_patches(release_path)
            with stack[0], stack[1], stack[2], stack[3], stack[4], stack[5], stack[6], \
                 patch(f'{MODULE}.save_application_info') as mock_save, \
                 patch(f'{MODULE}._check_application_exists', return_value=True), \
                 patch(f'{MODULE}._check_application_group_exists', return_value=True), \
                 patch(f'{MODULE}._handle_existing_application_group'):
                call_code_deploy(file_path=str(release_path), instance_ids=['i-1'])

            saved = mock_save.call_args[0][0]['last_deployment']
            assert saved['application_name'] == 'demo-app'
            assert saved['application_group_name'] == 'demo-group'
            assert saved['instance_ids'] == ['i-1']


class TestCodeDeployCommandGeneration:
    """测试 OOS_CodeDeploy 的启停命令自动生成"""

    def test_auto_generates_start_and_stop_commands(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            release_path = Path(tmpdir) / 'app.tar.gz'
            release_path.write_bytes(b'payload')

            stack = deploy_patches(release_path)
            with stack[0], stack[1], stack[2], stack[3], stack[4], stack[5], stack[6], stack[7], \
                 patch(f'{MODULE}._generate_start_stop_commands_by_rules',
                       return_value=('generated-start', 'generated-stop')) as mock_gen, \
                 patch(f'{MODULE}._check_application_exists', return_value=True), \
                 patch(f'{MODULE}._check_application_group_exists', return_value=True), \
                 patch(f'{MODULE}._handle_existing_application_group') as mock_existing:
                call_code_deploy(
                    file_path=str(release_path),
                    application_start=None,
                    application_stop=None,
                )

            mock_gen.assert_called_once_with(str(release_path), 'java', 'demo-app', 8080)
            args = mock_existing.call_args[0]
            assert 'generated-start' in args
            assert 'generated-stop' in args

    def test_returns_error_when_start_command_cannot_be_generated(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            release_path = Path(tmpdir) / 'app.tar.gz'
            release_path.write_bytes(b'payload')

            stack = deploy_patches(release_path)
            with stack[0], stack[1], stack[2], stack[3], \
                 patch(f'{MODULE}._generate_start_stop_commands_by_rules', return_value=(None, 'stop')):
                result = call_code_deploy(
                    file_path=str(release_path),
                    application_start=None,
                    application_stop=None,
                )

            assert result['error'] == 'START_COMMAND_REQUIRED'
            assert result['deploy_language'] == 'java'
            assert '启动命令生成失败' in result['instructions']


class TestCodeDeployOssFailure:
    """测试 OOS_CodeDeploy 的 OSS 异常处理"""

    def test_returns_error_when_oss_not_activated(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            release_path = Path(tmpdir) / 'app.tar.gz'
            release_path.write_bytes(b'payload')

            operation_error = oss.exceptions.OperationError(
                name='PutBucket', error=Exception('not activated')
            )
            with patch(f'{MODULE}.set_project_path'), \
                 patch(f'{MODULE}._check_ecs_instances_exist', return_value=(True, [])), \
                 patch(f'{MODULE}.ensure_code_deploy_dirs'), \
                 patch(f'{MODULE}.get_release_path', return_value=release_path), \
                 patch(f'{MODULE}.get_or_create_bucket_for_code_deploy', side_effect=operation_error):
                result = call_code_deploy(file_path=str(release_path))

            assert result['error'] == 'OSS_SERVICE_NOT_ACTIVATED'
            assert result['oss_console_link'] == 'https://oss.console.aliyun.com/'
            assert 'OSS服务未开通' in result['instructions']
