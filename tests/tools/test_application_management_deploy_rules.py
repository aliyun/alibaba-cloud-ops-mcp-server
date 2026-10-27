import io
import json
import os
import tarfile
import tempfile
import zipfile
from unittest.mock import patch

import pytest

from alibaba_cloud_ops_mcp_server.tools import application_management_tools as amt


def make_tar(path, names, mode='w:gz'):
    """生成包含指定成员的 tar 包"""
    with tarfile.open(path, mode) as tar:
        for name in names:
            data = b'x'
            info = tarfile.TarInfo(name=name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))


def make_zip(path, names):
    """生成包含指定成员的 zip 包"""
    with zipfile.ZipFile(path, 'w') as zf:
        for name in names:
            zf.writestr(name, 'x')


def archive_analysis(archive_type='tar.gz', files=None):
    """构造 archive 类型的文件分析结果"""
    return {
        'file_type': 'archive',
        'archive_type': archive_type,
        'file_name': f'app.{archive_type}',
        'files_in_archive': files or [],
        'extracted_dir_name': None,
    }


def plain_analysis(files=None):
    """构造普通文件类型的文件分析结果"""
    return {
        'file_type': 'file',
        'archive_type': None,
        'file_name': 'app.jar',
        'files_in_archive': files or [],
        'extracted_dir_name': None,
    }


class TestExtractTopLevelDir:
    """测试 _extract_top_level_dir 函数"""

    def test_empty_members(self):
        assert amt._extract_top_level_dir([]) is None

    def test_single_top_level_dir(self):
        members = ['app/', 'app/main.py', 'app/lib/util.py']
        assert amt._extract_top_level_dir(members) == 'app'

    def test_multiple_top_level_dirs(self):
        members = ['app/main.py', 'docs/readme.md']
        assert amt._extract_top_level_dir(members) is None

    def test_skips_absolute_path_members(self):
        """以 / 开头的成员首段为空，应被忽略"""
        members = ['/app/main.py', 'app/lib.py']
        assert amt._extract_top_level_dir(members) == 'app'


class TestAnalyzeDeploymentFile:
    """测试 _analyze_deployment_file 函数"""

    def test_file_not_exists(self):
        result = amt._analyze_deployment_file('/path/does/not/exist/app.tar.gz')
        assert result == {'file_type': 'unknown', 'file_name': 'app.tar.gz'}

    def test_plain_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, 'app.jar')
            with open(file_path, 'wb') as f:
                f.write(b'binary')

            result = amt._analyze_deployment_file(file_path)

            assert result['file_type'] == 'file'
            assert result['archive_type'] is None
            assert result['files_in_archive'] == []

    @pytest.mark.parametrize('file_name', ['app.tar.gz', 'app.tgz'])
    def test_targz_archive(self, file_name):
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, file_name)
            make_tar(file_path, ['app/app.jar', 'app/start.sh'])

            result = amt._analyze_deployment_file(file_path)

            assert result['file_type'] == 'archive'
            assert result['archive_type'] == 'tar.gz'
            assert result['extracted_dir_name'] == 'app'
            assert 'app/app.jar' in result['files_in_archive']

    def test_targz_archive_broken(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, 'broken.tar.gz')
            with open(file_path, 'wb') as f:
                f.write(b'not a real gzip')

            result = amt._analyze_deployment_file(file_path)

            assert result['archive_type'] == 'tar.gz'
            assert result['files_in_archive'] == []

    def test_tar_archive(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, 'app.tar')
            make_tar(file_path, ['svc/main.py'], mode='w')

            result = amt._analyze_deployment_file(file_path)

            assert result['archive_type'] == 'tar'
            assert result['extracted_dir_name'] == 'svc'

    def test_tar_archive_broken(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, 'broken.tar')
            with open(file_path, 'wb') as f:
                f.write(b'garbage')

            result = amt._analyze_deployment_file(file_path)

            assert result['archive_type'] == 'tar'
            assert result['files_in_archive'] == []

    def test_zip_archive(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, 'app.zip')
            make_zip(file_path, ['web/index.js'])

            result = amt._analyze_deployment_file(file_path)

            assert result['archive_type'] == 'zip'
            assert result['extracted_dir_name'] == 'web'

    def test_zip_archive_broken(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, 'broken.zip')
            with open(file_path, 'wb') as f:
                f.write(b'garbage')

            result = amt._analyze_deployment_file(file_path)

            assert result['archive_type'] == 'zip'
            assert result['files_in_archive'] == []


class TestFindExecutableFiles:
    """测试 _find_executable_files 函数"""

    def test_collects_each_file_category(self):
        files = [
            'app/app.jar',
            'app/main.py',
            'app/package.json',
            'app/index.js',
            'app/start.sh',
            'app/requirements.txt',
            'app/Dockerfile',
        ]

        result = amt._find_executable_files(files, 'java')

        assert result['jar_files'] == ['app/app.jar']
        assert result['py_files'] == ['app/main.py']
        assert result['package_json'] == 'app/package.json'
        assert result['js_files'] == ['app/index.js']
        assert result['shell_scripts'] == ['app/start.sh']
        assert result['requirements_txt'] == 'app/requirements.txt'
        assert result['dockerfile'] == 'app/Dockerfile'
        # 非 golang 语言不收集无扩展名文件
        assert result['go_binaries'] == []

    def test_golang_binary_detection(self):
        files = ['bin/app', 'bin/README', 'bin/config', 'bin/notes.txt']

        result = amt._find_executable_files(files, 'golang')

        assert result['go_binaries'] == ['bin/app']


class TestGenerateStartCommandJava:
    """测试 Java 启动命令生成"""

    def test_jar_in_extracted_dir(self):
        analysis = archive_analysis(files=['app/app.jar'])
        cmd = amt._generate_start_command_by_rules(
            'release/app.tar.gz', 'java', analysis, extracted_dir_name='app'
        )
        assert cmd.startswith('[ -f app.tar.gz ] && tar -xzf app.tar.gz || exit 1')
        assert '[ -d app ] && cd app || exit 1' in cmd
        assert 'nohup java -jar app/app.jar' in cmd

    def test_jar_without_extracted_dir(self):
        analysis = archive_analysis(archive_type='tar', files=['app.jar'])
        cmd = amt._generate_start_command_by_rules(
            'release/app.tar', 'java', analysis, extracted_dir_name=None
        )
        assert 'tar -xf app.tar' in cmd
        assert '[ -f app.jar ] && nohup java -jar app.jar' in cmd

    def test_no_jar_with_extracted_dir_from_zip(self):
        analysis = archive_analysis(archive_type='zip', files=['app/readme.md'])
        cmd = amt._generate_start_command_by_rules(
            'release/app.zip', 'java', analysis, extracted_dir_name='app'
        )
        assert 'unzip -o app.zip' in cmd
        assert 'app/app.jar' in cmd

    def test_no_jar_plain_file(self):
        analysis = plain_analysis()
        cmd = amt._generate_start_command_by_rules('release/app.jar', 'java', analysis)
        assert cmd == '[ -f app.jar ] && nohup java -jar app.jar > /root/app.log 2>&1 &'


class TestGenerateStartCommandPython:
    """测试 Python 启动命令生成"""

    def test_preferred_py_file_in_extracted_dir(self):
        analysis = archive_analysis(files=['svc/util.py', 'svc/main.py'])
        cmd = amt._generate_start_command_by_rules(
            'release/app.tar.gz', 'python', analysis, extracted_dir_name='svc'
        )
        assert 'nohup python svc/main.py' in cmd

    def test_falls_back_to_first_py_file(self):
        analysis = archive_analysis(files=['svc/custom_entry.py'])
        cmd = amt._generate_start_command_by_rules(
            'release/app.tar.gz', 'python', analysis, extracted_dir_name=None
        )
        assert 'nohup python custom_entry.py' in cmd

    def test_no_py_file_with_extracted_dir(self):
        analysis = archive_analysis(files=['svc/readme.md'])
        cmd = amt._generate_start_command_by_rules(
            'release/app.tar.gz', 'python', analysis, extracted_dir_name='svc'
        )
        assert 'svc/app.py' in cmd

    def test_no_py_file_plain_file(self):
        analysis = plain_analysis()
        cmd = amt._generate_start_command_by_rules('release/app.py', 'python', analysis)
        assert cmd == '[ -f app.py ] && nohup python app.py > /root/app.log 2>&1 &'


class TestGenerateStartCommandNodejs:
    """测试 Node.js 启动命令生成"""

    def test_package_json_with_start_script(self):
        analysis = archive_analysis(files=['web/package.json', 'web/start.sh'])
        cmd = amt._generate_start_command_by_rules(
            'release/app.tar.gz', 'nodejs', analysis, extracted_dir_name='web'
        )
        assert 'npm install' in cmd
        assert 'nohup ./start.sh' in cmd

    def test_package_json_without_start_script(self):
        analysis = archive_analysis(files=['package.json'])
        cmd = amt._generate_start_command_by_rules(
            'release/app.tar.gz', 'nodejs', analysis, extracted_dir_name=None
        )
        assert 'npm install && nohup npm start' in cmd

    def test_preferred_js_file(self):
        analysis = archive_analysis(files=['web/util.js', 'web/index.js'])
        cmd = amt._generate_start_command_by_rules(
            'release/app.tar.gz', 'nodejs', analysis, extracted_dir_name='web'
        )
        assert 'nohup node web/index.js' in cmd

    def test_falls_back_to_first_js_file(self):
        analysis = archive_analysis(files=['web/custom.js'])
        cmd = amt._generate_start_command_by_rules(
            'release/app.tar.gz', 'nodejs', analysis, extracted_dir_name=None
        )
        assert 'nohup node custom.js' in cmd

    def test_no_js_file_returns_none(self):
        analysis = archive_analysis(files=['web/readme.md'])
        cmd = amt._generate_start_command_by_rules(
            'release/app.tar.gz', 'nodejs', analysis, extracted_dir_name='web'
        )
        assert cmd is None

    def test_js_file_without_resolvable_name_returns_none(self):
        """js 文件名无法解析出有效文件名时放弃生成（防御性分支）"""
        executable_files = {
            'jar_files': [], 'py_files': [], 'js_files': [''], 'go_binaries': [],
            'shell_scripts': [], 'package_json': None, 'requirements_txt': None,
            'dockerfile': None,
        }
        analysis = archive_analysis(files=[''])
        with patch.object(amt, '_find_executable_files', return_value=executable_files):
            cmd = amt._generate_start_command_by_rules(
                'release/app.tar.gz', 'nodejs', analysis, extracted_dir_name=None
            )
        assert cmd is None


class TestGenerateStartCommandGolang:
    """测试 Golang 启动命令生成"""

    def test_binary_found_in_extracted_dir(self):
        analysis = archive_analysis(files=['svc/app'])
        cmd = amt._generate_start_command_by_rules(
            'release/app.tar.gz', 'golang', analysis, extracted_dir_name='svc'
        )
        assert 'chmod +x svc/app' in cmd
        assert 'nohup ./svc/app' in cmd

    def test_no_binary_with_extracted_dir(self):
        analysis = archive_analysis(files=['svc/readme.md'])
        cmd = amt._generate_start_command_by_rules(
            'release/service.tar.gz', 'golang', analysis, extracted_dir_name='svc'
        )
        assert 'svc/service.tar' in cmd

    def test_no_binary_plain_file(self):
        analysis = plain_analysis(files=['readme.md'])
        cmd = amt._generate_start_command_by_rules('release/service', 'golang', analysis)
        assert cmd.startswith('[ -f service ] && chmod +x service')


class TestGenerateStartCommandDocker:
    """测试 Docker 启动命令生成"""

    def test_dockerfile_in_extracted_dir(self):
        analysis = archive_analysis(files=['app/Dockerfile'])
        cmd = amt._generate_start_command_by_rules(
            'release/app.tar.gz', 'docker', analysis,
            extracted_dir_name='app', application_name='My_App', port=8080
        )
        assert 'command -v docker' in cmd
        assert 'docker build -t my-app:latest .' in cmd
        assert '-p 8080:8080 my-app:latest' in cmd

    def test_dockerfile_without_extracted_dir(self):
        analysis = archive_analysis(files=['Dockerfile'])
        cmd = amt._generate_start_command_by_rules(
            'release/app.tar.gz', 'docker', analysis,
            extracted_dir_name=None, application_name=None, port=None
        )
        # 未提供 application_name 时使用默认镜像名，未提供端口时不做端口映射
        assert 'docker run -d --name app app:latest' in cmd

    def test_dockerfile_plain_file(self):
        analysis = plain_analysis(files=['Dockerfile'])
        cmd = amt._generate_start_command_by_rules(
            'release/Dockerfile', 'docker', analysis, application_name='demo', port=80
        )
        assert cmd.startswith('command -v docker')
        assert 'tar -xzf' not in cmd

    def test_without_dockerfile_returns_none(self):
        analysis = archive_analysis(files=['app/main.go'])
        cmd = amt._generate_start_command_by_rules(
            'release/app.tar.gz', 'docker', analysis, extracted_dir_name='app'
        )
        assert cmd is None


def test_generate_start_command_unknown_language_returns_none():
    """未知部署语言无法生成启动命令"""
    analysis = archive_analysis(files=['app/main.rb'])
    cmd = amt._generate_start_command_by_rules(
        'release/app.tar.gz', 'ruby', analysis, extracted_dir_name='app'
    )
    assert cmd is None


class TestGenerateStopCommand:
    """测试停止命令生成"""

    @pytest.mark.parametrize('language,expected', [
        ('java', "pkill -f 'java -jar' || true"),
        ('python', "pkill -f 'python.*\\.py' || true"),
        ('nodejs', "pkill -f 'node.*\\.js' || pkill -f 'npm start' || true"),
        ('golang', "pkill -f './app' || pkill -f './main' || pkill -f './server' || true"),
        ('ruby', "pkill -f 'app' || true"),
    ])
    def test_language_stop_commands(self, language, expected):
        assert amt._generate_stop_command_by_rules(language, plain_analysis()) == expected

    def test_docker_stop_command_uses_container_name(self):
        cmd = amt._generate_stop_command_by_rules(
            'docker', plain_analysis(), application_name='My_App'
        )
        assert cmd == 'docker stop my-app 2>/dev/null || true && docker rm my-app 2>/dev/null || true'

    def test_docker_stop_command_default_container_name(self):
        cmd = amt._generate_stop_command_by_rules('docker', plain_analysis())
        assert 'docker stop app ' in cmd


class TestGenerateStartStopCommands:
    """测试 _generate_start_stop_commands_by_rules 组合逻辑"""

    def test_success(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, 'app.tar.gz')
            make_tar(file_path, ['app/app.jar'])

            start_cmd, stop_cmd = amt._generate_start_stop_commands_by_rules(
                file_path, 'java', 'demo', 8080
            )

            assert 'nohup java -jar app/app.jar' in start_cmd
            assert stop_cmd == "pkill -f 'java -jar' || true"

    def test_start_command_cannot_be_generated(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, 'app.tar.gz')
            make_tar(file_path, ['app/readme.md'])

            start_cmd, stop_cmd = amt._generate_start_stop_commands_by_rules(
                file_path, 'nodejs', 'demo', 8080
            )

            assert start_cmd is None
            assert stop_cmd is not None

    def test_exception_returns_none_pair(self):
        with patch.object(amt, '_analyze_deployment_file', side_effect=Exception('boom')):
            assert amt._generate_start_stop_commands_by_rules('app.tar.gz', 'java') == (None, None)
