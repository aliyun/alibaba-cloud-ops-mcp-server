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
