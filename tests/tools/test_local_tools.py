import pytest
import tempfile
import os
import json
from unittest.mock import patch, MagicMock
from alibaba_cloud_ops_mcp_server.tools import local_tools


class TestToolsList:
    """测试 ToolsList 类"""
    
    def test_tools_list_append(self):
        """测试 ToolsList.append 方法"""
        tools = local_tools.ToolsList()
        
        @tools.append
        def test_func():
            return 'test'
        
        assert len(tools) == 1
        assert test_func in tools._list
    
    def test_tools_list_iter(self):
        """测试 ToolsList 迭代"""
        tools = local_tools.ToolsList()
        
        @tools.append
        def func1():
            pass
        
        @tools.append
        def func2():
            pass
        
        funcs = list(tools)
        assert len(funcs) == 2


class TestValidatePath:
    """测试 _validate_path 函数"""
    
    def test_validate_path_exists(self):
        """测试验证存在的路径"""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = local_tools._validate_path(tmpdir)
            assert result.exists()
    
    def test_validate_path_not_exists(self):
        """测试验证不存在的路径"""
        # FileNotFoundError 会被捕获并转成 ValueError
        with pytest.raises(ValueError, match="Invalid path"):
            local_tools._validate_path('/nonexistent/path/12345')
    
    def test_validate_path_invalid(self):
        """测试验证无效路径"""
        with pytest.raises(ValueError):
            local_tools._validate_path('\x00invalid')


class TestLocalListDirectory:
    """测试 LOCAL_ListDirectory 函数"""
    
    def test_list_directory_success(self):
        """测试列出目录成功"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建测试文件和目录
            test_file = os.path.join(tmpdir, 'test_file.txt')
            test_dir = os.path.join(tmpdir, 'test_dir')
            with open(test_file, 'w') as f:
                f.write('test content')
            os.makedirs(test_dir)
            
            result = local_tools.LOCAL_ListDirectory(path=tmpdir, recursive=False)
            
            # 比较真实路径（解决 /var -> /private/var 符号链接问题）
            from pathlib import Path
            assert Path(result['path']).resolve() == Path(tmpdir).resolve()
            assert result['count'] == 2
            names = [item['name'] for item in result['items']]
            assert 'test_file.txt' in names
            assert 'test_dir' in names
    
    def test_list_directory_recursive(self):
        """测试递归列出目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建嵌套目录结构
            sub_dir = os.path.join(tmpdir, 'subdir')
            os.makedirs(sub_dir)
            nested_file = os.path.join(sub_dir, 'nested.txt')
            with open(nested_file, 'w') as f:
                f.write('nested')
            
            result = local_tools.LOCAL_ListDirectory(path=tmpdir, recursive=True)
            
            names = [item['name'] for item in result['items']]
            assert 'subdir' in names
            assert 'nested.txt' in names
    
    def test_list_directory_not_a_directory(self):
        """测试路径不是目录"""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b'test')
            temp_file = f.name
        
        try:
            with pytest.raises(ValueError, match="Path is not a directory"):
                local_tools.LOCAL_ListDirectory(path=temp_file, recursive=False)
        finally:
            os.unlink(temp_file)
    
    def test_list_directory_not_exists(self):
        """测试目录不存在"""
        with pytest.raises(ValueError, match="Failed to list directory"):
            local_tools.LOCAL_ListDirectory(path='/nonexistent/dir', recursive=False)


class TestLocalRunShellScript:
    """测试 LOCAL_RunShellScript 函数"""
    
    def test_run_shell_script_success(self):
        """测试运行 shell 脚本成功"""
        result = local_tools.LOCAL_RunShellScript(
            script='echo "hello world"',
            working_directory=None,
            timeout=30,
            shell=True
        )
        
        assert result['success'] is True
        assert result['exit_code'] == 0
        assert 'hello world' in result['stdout']
    
    def test_run_shell_script_with_working_directory(self):
        """测试指定工作目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = local_tools.LOCAL_RunShellScript(
                script='pwd',
                working_directory=tmpdir,
                timeout=30,
                shell=True
            )
            
            assert result['success'] is True
            assert tmpdir in result['stdout']
    
    def test_run_shell_script_non_shell_mode(self):
        """测试非 shell 模式"""
        result = local_tools.LOCAL_RunShellScript(
            script='echo hello',
            working_directory=None,
            timeout=30,
            shell=False
        )
        
        assert result['success'] is True
        assert 'hello' in result['stdout']
    
    def test_run_shell_script_error(self):
        """测试脚本执行失败"""
        result = local_tools.LOCAL_RunShellScript(
            script='exit 1',
            working_directory=None,
            timeout=30,
            shell=True
        )
        
        assert result['success'] is False
        assert result['exit_code'] == 1
    
    def test_run_shell_script_timeout(self):
        """测试脚本超时"""
        with pytest.raises(ValueError, match="timeout"):
            local_tools.LOCAL_RunShellScript(
                script='sleep 10',
                working_directory=None,
                timeout=1,
                shell=True
            )
    
    def test_run_shell_script_invalid_working_directory(self):
        """测试无效的工作目录"""
        with pytest.raises(ValueError):
            local_tools.LOCAL_RunShellScript(
                script='echo test',
                working_directory='/nonexistent/dir',
                timeout=30,
                shell=True
            )


class TestLocalAnalyzeDeployStack:
    """测试 LOCAL_AnalyzeDeployStack 函数"""
    
    def test_analyze_nodejs_project(self):
        """测试分析 Node.js 项目"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建 package.json
            package_json = os.path.join(tmpdir, 'package.json')
            with open(package_json, 'w') as f:
                json.dump({'name': 'test', 'engines': {'node': '>=16'}}, f)
            
            result = local_tools.LOCAL_AnalyzeDeployStack(directory=tmpdir)
            
            assert result['detected'] is True
            assert 'npm' in result['package_managers']
            assert 'nodejs' in result['frameworks']
            assert 'npm' in result['deployment_methods']
    
    def test_analyze_python_project(self):
        """测试分析 Python 项目"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建 requirements.txt
            req_file = os.path.join(tmpdir, 'requirements.txt')
            with open(req_file, 'w') as f:
                f.write('flask==2.0.0\n')
            
            result = local_tools.LOCAL_AnalyzeDeployStack(directory=tmpdir)
            
            assert result['detected'] is True
            assert 'pip' in result['package_managers']
            assert 'python' in result['frameworks']
            assert 'python' in result['deployment_methods']
    
    def test_analyze_java_project(self):
        """测试分析 Java 项目"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建 pom.xml
            pom_file = os.path.join(tmpdir, 'pom.xml')
            with open(pom_file, 'w') as f:
                f.write('<project></project>')
            
            result = local_tools.LOCAL_AnalyzeDeployStack(directory=tmpdir)
            
            assert result['detected'] is True
            assert 'maven' in result['package_managers']
            assert 'java' in result['frameworks']
            assert 'java' in result['deployment_methods']
    
    def test_analyze_go_project(self):
        """测试分析 Go 项目"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建 go.mod
            go_mod = os.path.join(tmpdir, 'go.mod')
            with open(go_mod, 'w') as f:
                f.write('module test\ngo 1.20\n')
            
            result = local_tools.LOCAL_AnalyzeDeployStack(directory=tmpdir)
            
            assert result['detected'] is True
            assert 'go' in result['package_managers']
            assert 'go' in result['frameworks']
            assert 'go' in result['deployment_methods']
            assert result['runtime_versions'].get('go') == '1.20'
    
    def test_analyze_docker_project(self):
        """测试分析 Docker 项目"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建 Dockerfile
            dockerfile = os.path.join(tmpdir, 'Dockerfile')
            with open(dockerfile, 'w') as f:
                f.write('FROM python:3.9\nRUN pip install flask\n')
            
            result = local_tools.LOCAL_AnalyzeDeployStack(directory=tmpdir)
            
            assert result['detected'] is True
            assert 'docker' in result['package_managers']
            assert 'docker' in result['deployment_methods']
    
    def test_analyze_unknown_project(self):
        """测试分析未知项目类型"""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = local_tools.LOCAL_AnalyzeDeployStack(directory=tmpdir)
            
            assert result['detected'] is False
            assert 'unknown' in result['deployment_methods']
    
    def test_analyze_not_a_directory(self):
        """测试路径不是目录"""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b'test')
            temp_file = f.name
        
        try:
            with pytest.raises(ValueError, match="不是目录"):
                local_tools.LOCAL_AnalyzeDeployStack(directory=temp_file)
        finally:
            os.unlink(temp_file)
    
    def test_analyze_with_python_version_file(self):
        """测试读取 .python-version 文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建 requirements.txt
            req_file = os.path.join(tmpdir, 'requirements.txt')
            with open(req_file, 'w') as f:
                f.write('flask==2.0.0\n')
            
            # 创建 .python-version
            py_version = os.path.join(tmpdir, '.python-version')
            with open(py_version, 'w') as f:
                f.write('3.10.0')
            
            result = local_tools.LOCAL_AnalyzeDeployStack(directory=tmpdir)
            
            assert result['runtime_versions'].get('python') == '3.10.0'
