import pytest
import json
from unittest.mock import patch, MagicMock
from alibaba_cloud_ops_mcp_server.tools import application_management_tools


class TestOOSGetLastDeploymentInfo:
    """测试 OOS_GetLastDeploymentInfo 函数"""
    
    def test_get_last_deployment_info_exists(self):
        """测试获取存在的部署信息"""
        with patch('alibaba_cloud_ops_mcp_server.tools.application_management_tools.load_application_info') as mock_load:
            mock_load.return_value = {
                'last_deployment': {
                    'application_name': 'test-app',
                    'deploy_region_id': 'cn-hangzhou'
                }
            }
            
            result = application_management_tools.OOS_GetLastDeploymentInfo()
            
            assert result['message'] == 'Successfully retrieved last deployment information'
            assert result['info']['application_name'] == 'test-app'
    
    def test_get_last_deployment_info_not_exists(self):
        """测试获取不存在的部署信息"""
        with patch('alibaba_cloud_ops_mcp_server.tools.application_management_tools.load_application_info') as mock_load:
            mock_load.return_value = {}
            
            result = application_management_tools.OOS_GetLastDeploymentInfo()
            
            assert result['message'] == 'No information found about the last deployment'
            assert result['info'] == {}


class TestOOSGetDeployStatus:
    """测试 OOS_GetDeployStatus 函数"""
    
    def test_get_deploy_status(self):
        """测试获取部署状态"""
        with patch('alibaba_cloud_ops_mcp_server.tools.application_management_tools.create_client') as mock_create, \
             patch('alibaba_cloud_ops_mcp_server.tools.application_management_tools._list_application_group_deployment') as mock_list:
            mock_client = MagicMock()
            mock_create.return_value = mock_client
            mock_list.return_value = {'status': 'Deployed'}
            
            result = application_management_tools.OOS_GetDeployStatus(
                name='test-app',
                application_group_name='test-group'
            )
            
            assert result['status'] == 'Deployed'


class TestECSDescribeInstances:
    """测试 ECS_DescribeInstances 函数"""
    
    def test_describe_instances_success(self):
        """测试查询实例成功"""
        with patch('alibaba_cloud_ops_mcp_server.tools.application_management_tools._describe_instances_with_retry') as mock_describe:
            mock_response = MagicMock()
            mock_describe.return_value = mock_response
            
            result = application_management_tools.ECS_DescribeInstances(
                instance_ids=['i-test123'],
                region_id='cn-hangzhou'
            )
            
            assert result is mock_response
    
    def test_describe_instances_empty_ids(self):
        """测试空实例 ID 列表"""
        with pytest.raises(ValueError, match="instance_ids is required"):
            application_management_tools.ECS_DescribeInstances(
                instance_ids=[],
                region_id='cn-hangzhou'
            )


class TestHelperFunctions:
    """测试辅助函数"""
    
    def test_check_application_exists_true(self):
        """测试应用存在"""
        mock_client = MagicMock()
        
        result = application_management_tools._check_application_exists(mock_client, 'test-app')
        
        assert result is True
    
    def test_check_application_exists_false(self):
        """测试应用不存在"""
        mock_client = MagicMock()
        mock_error = Exception('test')
        mock_error.code = 'EntityNotExists.Application'
        mock_client.get_application.side_effect = mock_error
        
        result = application_management_tools._check_application_exists(mock_client, 'nonexistent-app')
        
        assert result is False
    
    def test_check_application_group_exists_true(self):
        """测试应用分组存在"""
        mock_client = MagicMock()
        
        result = application_management_tools._check_application_group_exists(
            mock_client, 'test-app', 'test-group'
        )
        
        assert result is True
    
    def test_check_application_group_exists_false(self):
        """测试应用分组不存在"""
        mock_client = MagicMock()
        mock_error = Exception('test')
        mock_error.code = 'EntityNotExists.ApplicationGroup'
        mock_client.get_application_group.side_effect = mock_error
        
        result = application_management_tools._check_application_group_exists(
            mock_client, 'test-app', 'nonexistent-group'
        )
        
        assert result is False
    
    def test_create_deploy_parameters(self):
        """测试创建部署参数"""
        result = application_management_tools._create_deploy_parameters(
            name='test-app',
            application_group_name='test-group',
            region_id_oss='cn-hangzhou',
            bucket_name='test-bucket',
            object_name='test.tar.gz',
            version_id='v1',
            is_internal_oss=True,
            port=8080,
            instance_ids=['i-test123'],
            application_start='./start.sh',
            application_stop='./stop.sh',
            deploy_language='java'
        )
        
        assert result['Parameters']['ApplicationName'] == 'test-app'
        assert result['Parameters']['Port'] == 8080
        assert result['Parameters']['BucketName'] == 'test-bucket'
    
    def test_create_location_and_hooks(self):
        """测试创建位置和钩子配置"""
        result = application_management_tools._create_location_and_hooks(
            region_id_oss='cn-hangzhou',
            bucket_name='test-bucket',
            object_name='test.tar.gz',
            version_id='v1',
            deploy_region_id='cn-hangzhou',
            application_start='./start.sh',
            application_stop='./stop.sh'
        )
        
        assert result['location']['bucketName'] == 'test-bucket'
        assert result['hooks']['applicationStart'] == './start.sh'
    
    def test_create_revision_deploy_parameters(self):
        """测试创建修订部署参数"""
        result = application_management_tools._create_revision_deploy_parameters()
        
        assert 'StartExecutionParameters' in result
        assert 'Parameters' in result['StartExecutionParameters']


class TestDescribeInstancesWithRetry:
    """测试 _describe_instances_with_retry 函数"""
    
    def test_describe_instances_success_first_try(self):
        """测试第一次就成功"""
        with patch('alibaba_cloud_ops_mcp_server.tools.application_management_tools.create_ecs_client') as mock_create:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_client.describe_instances.return_value = mock_response
            mock_create.return_value = mock_client
            
            request = MagicMock()
            result = application_management_tools._describe_instances_with_retry('cn-hangzhou', request)
            
            assert result is mock_response
    
    def test_describe_instances_retry_on_bad_fd(self):
        """测试 Bad file descriptor 错误重试"""
        with patch('alibaba_cloud_ops_mcp_server.tools.application_management_tools.create_ecs_client') as mock_create, \
             patch('alibaba_cloud_ops_mcp_server.tools.application_management_tools.time.sleep'):
            mock_client = MagicMock()
            mock_response = MagicMock()
            
            # 前两次抛出异常，第三次成功
            class BadFdError(Exception):
                pass
            
            error = BadFdError('UnretryableException: Bad file descriptor')
            mock_client.describe_instances.side_effect = [error, error, mock_response]
            mock_create.return_value = mock_client
            
            request = MagicMock()
            result = application_management_tools._describe_instances_with_retry('cn-hangzhou', request)
            
            assert result is mock_response


class TestCheckEcsInstancesExist:
    """测试 _check_ecs_instances_exist 函数"""
    
    def test_all_instances_exist(self):
        """测试所有实例都存在"""
        with patch('alibaba_cloud_ops_mcp_server.tools.application_management_tools._describe_instances_with_retry') as mock_describe:
            mock_response = MagicMock()
            mock_instance = MagicMock()
            mock_instance.instance_id = 'i-test123'
            mock_response.body.instances.instance = [mock_instance]
            mock_describe.return_value = mock_response
            
            all_exist, missing = application_management_tools._check_ecs_instances_exist(
                'cn-hangzhou', ['i-test123']
            )
            
            assert all_exist is True
            assert missing == []
    
    def test_some_instances_missing(self):
        """测试部分实例不存在"""
        with patch('alibaba_cloud_ops_mcp_server.tools.application_management_tools._describe_instances_with_retry') as mock_describe:
            mock_response = MagicMock()
            mock_instance = MagicMock()
            mock_instance.instance_id = 'i-test123'
            mock_response.body.instances.instance = [mock_instance]
            mock_describe.return_value = mock_response
            
            all_exist, missing = application_management_tools._check_ecs_instances_exist(
                'cn-hangzhou', ['i-test123', 'i-missing456']
            )
            
            assert all_exist is False
            assert 'i-missing456' in missing
    
    def test_empty_instance_ids(self):
        """测试空实例 ID 列表"""
        all_exist, missing = application_management_tools._check_ecs_instances_exist('cn-hangzhou', [])
        
        assert all_exist is True
        assert missing == []


class TestCheckInstanceHasTag:
    """测试 _check_instance_has_tag 函数"""
    
    def test_instance_has_tag(self):
        """测试实例有标签"""
        with patch('alibaba_cloud_ops_mcp_server.tools.application_management_tools._describe_instances_with_retry') as mock_describe:
            mock_response = MagicMock()
            mock_instance = MagicMock()
            mock_tag = MagicMock()
            mock_tag.tag_key = 'app-test'
            mock_tag.tag_value = 'test-group'
            mock_instance.tags.tag = [mock_tag]
            mock_response.body.instances.instance = [mock_instance]
            mock_describe.return_value = mock_response
            
            result = application_management_tools._check_instance_has_tag(
                'cn-hangzhou', 'i-test123', 'app-test', 'test-group'
            )
            
            assert result is True
    
    def test_instance_no_tag(self):
        """测试实例没有标签"""
        with patch('alibaba_cloud_ops_mcp_server.tools.application_management_tools._describe_instances_with_retry') as mock_describe:
            mock_response = MagicMock()
            mock_instance = MagicMock()
            mock_instance.tags.tag = []
            mock_response.body.instances.instance = [mock_instance]
            mock_describe.return_value = mock_response
            
            result = application_management_tools._check_instance_has_tag(
                'cn-hangzhou', 'i-test123', 'app-test', 'test-group'
            )
            
            assert result is False


class TestEnsureInstancesTagged:
    """测试 _ensure_instances_tagged 函数"""
    
    def test_all_already_tagged(self):
        """测试所有实例已打标签"""
        with patch('alibaba_cloud_ops_mcp_server.tools.application_management_tools._check_instance_has_tag') as mock_check:
            mock_check.return_value = True
            
            application_management_tools._ensure_instances_tagged(
                'cn-hangzhou', 'test-app', 'test-group', ['i-test123']
            )
            
            # 不应该调用打标签
            # 测试通过即可
    
    def test_tag_instances(self):
        """测试给实例打标签"""
        with patch('alibaba_cloud_ops_mcp_server.tools.application_management_tools._check_instance_has_tag') as mock_check, \
             patch('alibaba_cloud_ops_mcp_server.tools.application_management_tools.create_ecs_client') as mock_create:
            mock_check.return_value = False
            mock_client = MagicMock()
            mock_create.return_value = mock_client
            
            application_management_tools._ensure_instances_tagged(
                'cn-hangzhou', 'test-app', 'test-group', ['i-test123']
            )
            
            mock_client.tag_resources.assert_called_once()
    
    def test_empty_instance_ids(self):
        """测试空实例 ID 列表"""
        application_management_tools._ensure_instances_tagged(
            'cn-hangzhou', 'test-app', 'test-group', []
        )
        # 不应该报错


class TestListApplicationGroupDeployment:
    """测试 _list_application_group_deployment 函数"""
    
    def test_list_deployment_with_execution(self):
        """测试列出部署信息（有执行记录）"""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.body.application_group.status = 'Deployed'
        mock_response.body.application_group.execution_id = 'exec-123'
        mock_client.get_application_group.return_value = mock_response
        
        mock_exec_response = MagicMock()
        mock_client.list_executions.return_value = mock_exec_response
        
        result = application_management_tools._list_application_group_deployment(
            mock_client, 'test-app', 'test-group', ['Deployed']
        )
        
        assert result['status'] == 'Deployed'
        assert result['execution_id'] == 'exec-123'
    
    def test_list_deployment_no_execution(self):
        """测试列出部署信息（无执行记录）"""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.body.application_group.status = 'Deployed'
        mock_response.body.application_group.execution_id = None
        mock_client.get_application_group.return_value = mock_response
        
        result = application_management_tools._list_application_group_deployment(
            mock_client, 'test-app', 'test-group', ['Deployed']
        )
        
        assert result['status'] == 'Deployed'
        assert result['deploy_execution_info'] is None

    def test_list_deployment_list_executions_error(self):
        """测试查询执行记录失败时忽略执行信息"""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.body.application_group.status = 'Deploying'
        mock_response.body.application_group.execution_id = 'exec-123'
        mock_client.get_application_group.return_value = mock_response
        mock_client.list_executions.side_effect = Exception('list failed')

        result = application_management_tools._list_application_group_deployment(
            mock_client, 'test-app', 'test-group', ['Deployed']
        )

        assert result['status'] == 'Deploying'
        assert result['deploy_execution_info'] is None


class TestDescribeInstancesWithRetryErrors:
    """测试 _describe_instances_with_retry 的异常分支"""

    def test_raises_non_retryable_error(self):
        """非可重试错误直接抛出"""
        with patch('alibaba_cloud_ops_mcp_server.tools.application_management_tools.create_ecs_client') as mock_create:
            mock_client = MagicMock()
            mock_client.describe_instances.side_effect = ValueError('invalid parameter')
            mock_create.return_value = mock_client

            with pytest.raises(ValueError, match='invalid parameter'):
                application_management_tools._describe_instances_with_retry('cn-hangzhou', MagicMock())

    def test_raises_last_exception_when_loop_exhausted(self):
        """重试循环耗尽后由兜底逻辑抛出最后一次异常"""
        class BadFdError(Exception):
            pass

        # 收窄重试循环的迭代次数，使循环正常结束后进入兜底分支
        with patch('alibaba_cloud_ops_mcp_server.tools.application_management_tools.create_ecs_client') as mock_create, \
             patch('alibaba_cloud_ops_mcp_server.tools.application_management_tools.time.sleep'), \
             patch('alibaba_cloud_ops_mcp_server.tools.application_management_tools.range',
                   lambda _: [0, 1], create=True):
            mock_client = MagicMock()
            mock_client.describe_instances.side_effect = BadFdError(
                'UnretryableException: Bad file descriptor'
            )
            mock_create.return_value = mock_client

            with pytest.raises(BadFdError):
                application_management_tools._describe_instances_with_retry('cn-hangzhou', MagicMock())


class TestCheckInstanceHasTagError:
    """测试 _check_instance_has_tag 查询失败的分支"""

    def test_returns_false_on_error(self):
        with patch('alibaba_cloud_ops_mcp_server.tools.application_management_tools._describe_instances_with_retry') as mock_describe:
            mock_describe.side_effect = Exception('query failed')

            result = application_management_tools._check_instance_has_tag(
                'cn-hangzhou', 'i-test123', 'app-test', 'test-group'
            )

            assert result is False


class TestTagMultipleInstances:
    """测试 _tag_multiple_instances 函数"""

    def test_tags_remaining_instances(self):
        """为除首个实例外的其余实例打标签"""
        with patch('alibaba_cloud_ops_mcp_server.tools.application_management_tools._ensure_instances_tagged') as mock_ensure:
            application_management_tools._tag_multiple_instances(
                'cn-hangzhou', 'test-app', 'test-group', ['i-1', 'i-2', 'i-3']
            )

            mock_ensure.assert_called_once_with('cn-hangzhou', 'test-app', 'test-group', ['i-2', 'i-3'])

    def test_single_instance_does_nothing(self):
        """只有一个实例时无需额外打标签"""
        with patch('alibaba_cloud_ops_mcp_server.tools.application_management_tools._ensure_instances_tagged') as mock_ensure:
            application_management_tools._tag_multiple_instances(
                'cn-hangzhou', 'test-app', 'test-group', ['i-1']
            )

            mock_ensure.assert_not_called()


class TestExistenceCheckErrors:
    """测试应用/应用分组存在性检查遇到非预期错误时向上抛出"""

    def test_check_application_exists_unexpected_error(self):
        mock_client = MagicMock()
        error = Exception('internal error')
        error.code = 'InternalError'
        mock_client.get_application.side_effect = error

        with pytest.raises(Exception, match='internal error'):
            application_management_tools._check_application_exists(mock_client, 'test-app')

    def test_check_application_group_exists_unexpected_error(self):
        mock_client = MagicMock()
        error = Exception('internal error')
        error.code = 'InternalError'
        mock_client.get_application_group.side_effect = error

        with pytest.raises(Exception, match='internal error'):
            application_management_tools._check_application_group_exists(
                mock_client, 'test-app', 'test-group'
            )


class TestHandleApplicationGroup:
    """测试应用分组部署请求的构建"""

    def test_handle_new_application_group(self):
        """新建应用分组时创建分组并构建部署请求"""
        with patch('alibaba_cloud_ops_mcp_server.tools.application_management_tools._ensure_instances_tagged') as mock_ensure:
            mock_client = MagicMock()

            request = application_management_tools._handle_new_application_group(
                mock_client, 'test-app', 'test-group', 'cn-hangzhou',
                'cn-hangzhou', 'test-bucket', 'app.tar.gz', 'v1',
                True, 8080, ['i-1'], 'start.sh', 'stop.sh', 'java'
            )

            mock_client.create_application_group.assert_called_once()
            mock_ensure.assert_called_once_with('cn-hangzhou', 'test-app', 'test-group', ['i-1'])
            assert request.application_name == 'test-app'
            deploy_parameters = json.loads(request.deploy_parameters)
            assert deploy_parameters['Parameters']['CreateEcsOption'] == 'ExistECS'
            assert deploy_parameters['Parameters']['PackageName'].startswith('ACS-Extension-java')

    def test_handle_existing_application_group(self):
        """已存在应用分组时创建部署版本并构建部署请求"""
        with patch('alibaba_cloud_ops_mcp_server.tools.application_management_tools._ensure_instances_tagged'), \
             patch('alibaba_cloud_ops_mcp_server.tools.application_management_tools._tools_api_call') as mock_api_call:
            mock_api_call.return_value = {'body': {'Revision': {'RevisionId': 2048}}}

            request = application_management_tools._handle_existing_application_group(
                'test-app', 'test-group', 'cn-hangzhou', 'cn-hangzhou', 'test-bucket',
                'app.tar.gz', 'v1', 'start.sh', 'stop.sh', ['i-1']
            )

            mock_api_call.assert_called_once()
            assert request.revision_id == '2048'
            deploy_parameters = json.loads(request.deploy_parameters)
            inner = json.loads(json.loads(deploy_parameters['StartExecutionParameters'])['Parameters'])
            assert inner['deployRevisionId'] == '2048'
            assert inner['applicationGroupName'] == 'test-group'

