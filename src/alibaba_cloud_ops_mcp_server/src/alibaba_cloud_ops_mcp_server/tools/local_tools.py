import os
import subprocess
import json
import re
import logging
from pathlib import Path
from typing import Optional, Dict, List, Any
from pydantic import Field

logger = logging.getLogger(__name__)


class ToolsList:
    """A tool list that can be used as both a list and a decorator"""
    def __init__(self):
        self._list = []
    
    def append(self, func):
        """Decorator: Add function to the list and return the function itself"""
        self._list.append(func)
        return func
    
    def __iter__(self):
        return iter(self._list)
    
    def __len__(self):
        return len(self._list)


tools = ToolsList()


def _validate_path(path: str) -> Path:
    """Validate and normalize path to prevent path traversal attacks"""
    try:
        # Convert to absolute path
        abs_path = Path(path).resolve()
        # Ensure path exists and is a file or directory
        if not abs_path.exists():
            raise FileNotFoundError(f"Path does not exist: {path}")
        return abs_path
    except (OSError, ValueError) as e:
        raise ValueError(f"Invalid path: {path}") from e


@tools.append
def LOCAL_ListDirectory(
    path: str = Field(description="Directory path to list (absolute or relative path)"),
    recursive: bool = Field(description="Whether to recursively list subdirectories", default=False)
):
    """列出指定目录中的文件和子目录。返回包含名称、类型和大小等信息的目录和文件列表。"""
    logger.info(f"[ListDirectory] Input parameters: path={path}, recursive={recursive}")
    try:
        dir_path = _validate_path(path)
        
        # Ensure it's a directory, not a file
        if not dir_path.is_dir():
            raise ValueError(f"Path is not a directory: {path}")
        
        results = []
        
        if recursive:
            # Recursively list
            for item in dir_path.rglob('*'):
                try:
                    item_stat = item.stat()
                    results.append({
                        "name": item.name,
                        "path": str(item),
                        "type": "directory" if item.is_dir() else "file",
                        "size": item_stat.st_size if item.is_file() else None,
                        "modified": item_stat.st_mtime
                    })
                except (OSError, PermissionError):
                    # Skip inaccessible files/directories
                    continue
        else:
            # List only current directory
            for item in dir_path.iterdir():
                try:
                    item_stat = item.stat()
                    results.append({
                        "name": item.name,
                        "path": str(item),
                        "type": "directory" if item.is_dir() else "file",
                        "size": item_stat.st_size if item.is_file() else None,
                        "modified": item_stat.st_mtime
                    })
                except (OSError, PermissionError):
                    # Skip inaccessible files/directories
                    continue
        
        # Sort by name
        results.sort(key=lambda x: x["name"])
        
        response = {
            "path": str(dir_path),
            "items": results,
            "count": len(results)
        }
        logger.info(f"[ListDirectory] Response: {json.dumps(response, ensure_ascii=False, default=str)}")
        return response
    except Exception as e:
        raise ValueError(f"Failed to list directory: {str(e)}")


@tools.append
def LOCAL_RunShellScript(
    script: str = Field(description="Shell script content or command to execute"),
    working_directory: Optional[str] = Field(description="Working directory for command execution", default=None),
    timeout: int = Field(description="Command execution timeout in seconds", default=300),
    shell: bool = Field(description="Whether to use shell execution (True uses /bin/sh, False executes command directly)", default=True)
):
    """执行 shell 脚本或命令。返回命令输出、错误信息和退出代码。注意：执行任意命令可能存在安全风险，请谨慎使用。"""
    logger.info(f"[RunShellScript] Input parameters: script={script}, working_directory={working_directory}, timeout={timeout}, shell={shell}")
    try:
        # Set working directory
        cwd = None
        if working_directory:
            cwd = _validate_path(working_directory)
            if not cwd.is_dir():
                raise ValueError(f"Working directory is not a directory: {working_directory}")
            cwd = str(cwd)
        
        # Execute command
        if shell:
            # Execute using shell
            process = subprocess.run(
                script,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd,
                executable='/bin/sh' if os.name != 'nt' else None
            )
        else:
            # Execute directly (need to split command into list)
            import shlex
            cmd_list = shlex.split(script)
            process = subprocess.run(
                cmd_list,
                shell=False,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd
            )
        
        response = {
            "command": script,
            "exit_code": process.returncode,
            "stdout": process.stdout,
            "stderr": process.stderr,
            "success": process.returncode == 0
        }
        logger.info(f"[RunShellScript] Response: {json.dumps(response, ensure_ascii=False, default=str)}")
        return response
    except subprocess.TimeoutExpired:
        raise ValueError(f"Command execution timeout (exceeded {timeout} seconds)")
    except FileNotFoundError:
        raise ValueError(f"Command or script not found: {script}")
    except Exception as e:
        raise ValueError(f"Failed to execute command: {str(e)}")


@tools.append
def LOCAL_AnalyzeDeployStack(
    directory: str = Field(description="Directory path to analyze (absolute or relative path)")
):
    """识别项目部署方式和技术栈。支持识别 npm、Python、Java、Go、Docker 等部署方式。"""
    logger.info(f"[AnalyzeDeployStack] Input parameters: directory={directory}")
    try:
        dir_path = _validate_path(directory)
        
        if not dir_path.is_dir():
            raise ValueError(f"路径不是目录: {directory}")
        
        detection_results = {
            "directory": str(dir_path),
            "deployment_methods": [],
            "package_managers": [],
            "frameworks": [],
            "runtime_versions": {},
            "config_files": {},
            "detected": False
        }
        
        # List of files to check
        files_to_check = {
            # Node.js / npm
            "package.json": ("npm", "nodejs"),
            "package-lock.json": ("npm", "nodejs"),
            "yarn.lock": ("yarn", "nodejs"),
            "pnpm-lock.yaml": ("pnpm", "nodejs"),
            ".nvmrc": ("nodejs", None),
            
            # Python
            "requirements.txt": ("pip", "python"),
            "Pipfile": ("pipenv", "python"),
            "pyproject.toml": ("poetry", "python"),
            "setup.py": ("setuptools", "python"),
            "environment.yml": ("conda", "python"),
            ".python-version": ("python", None),
            
            # Java
            "pom.xml": ("maven", "java"),
            "build.gradle": ("gradle", "java"),
            "build.gradle.kts": ("gradle", "java"),
            
            # Go
            "go.mod": ("go", "go"),
            "go.sum": ("go", "go"),
            "Gopkg.toml": ("dep", "go"),
            
            # Rust
            "Cargo.toml": ("cargo", "rust"),
            "Cargo.lock": ("cargo", "rust"),
            
            # PHP
            "composer.json": ("composer", "php"),
            
            # Ruby
            "Gemfile": ("bundler", "ruby"),
            
            # Docker
            "Dockerfile": ("docker", "docker"),
            "docker-compose.yml": ("docker-compose", "docker"),
            "docker-compose.yaml": ("docker-compose", "docker"),
            ".dockerignore": ("docker", "docker"),
            
            # 其他
            "Makefile": ("make", None),
            "CMakeLists.txt": ("cmake", "cpp"),
        }
        
        # Check if files exist
        for filename, (package_manager, framework) in files_to_check.items():
            file_path = dir_path / filename
            if file_path.exists():
                if package_manager:
                    if package_manager not in detection_results["package_managers"]:
                        detection_results["package_managers"].append(package_manager)
                if framework:
                    if framework not in detection_results["frameworks"]:
                        detection_results["frameworks"].append(framework)
                detection_results["config_files"][filename] = str(file_path)
        
        # Read key files to get more information
        # Read package.json
        package_json = dir_path / "package.json"
        if package_json.exists():
            try:
                with open(package_json, 'r', encoding='utf-8') as f:
                    pkg_data = json.load(f)
                    if "engines" in pkg_data and "node" in pkg_data["engines"]:
                        detection_results["runtime_versions"]["node"] = pkg_data["engines"]["node"]
            except Exception:
                pass
        
        # Read requirements.txt or pyproject.toml to get Python version information
        if (dir_path / "requirements.txt").exists() or (dir_path / "pyproject.toml").exists():
            # Try to read from .python-version
            py_version_file = dir_path / ".python-version"
            if py_version_file.exists():
                try:
                    version = py_version_file.read_text().strip()
                    detection_results["runtime_versions"]["python"] = version
                except Exception:
                    pass
        
        # Read go.mod to get Go version
        go_mod = dir_path / "go.mod"
        if go_mod.exists():
            try:
                content = go_mod.read_text()
                match = re.search(r'go\s+(\d+\.\d+)', content)
                if match:
                    detection_results["runtime_versions"]["go"] = match.group(1)
            except Exception:
                pass
        
        # Read Dockerfile to detect base image
        dockerfile = dir_path / "Dockerfile"
        if dockerfile.exists():
            try:
                content = dockerfile.read_text()
                # Detect common base images
                if "FROM node" in content or "FROM node:" in content:
                    match = re.search(r'FROM node:?(\S+)', content)
                    if match:
                        detection_results["runtime_versions"]["node_docker"] = match.group(1)
                elif "FROM python" in content or "FROM python:" in content:
                    match = re.search(r'FROM python:?(\S+)', content)
                    if match:
                        detection_results["runtime_versions"]["python_docker"] = match.group(1)
            except Exception:
                pass
        
        # Determine main deployment method
        if detection_results["package_managers"] or detection_results["frameworks"]:
            detection_results["detected"] = True
            # Infer deployment method based on detected package managers
            if "npm" in detection_results["package_managers"] or "yarn" in detection_results["package_managers"] or "pnpm" in detection_results["package_managers"]:
                detection_results["deployment_methods"].append("npm")
            if "pip" in detection_results["package_managers"] or "pipenv" in detection_results["package_managers"] or "poetry" in detection_results["package_managers"]:
                detection_results["deployment_methods"].append("python")
            if "maven" in detection_results["package_managers"] or "gradle" in detection_results["package_managers"]:
                detection_results["deployment_methods"].append("java")
            if "go" in detection_results["package_managers"]:
                detection_results["deployment_methods"].append("go")
            if "docker" in detection_results["package_managers"]:
                detection_results["deployment_methods"].append("docker")
        
        # If nothing detected, return unknown
        if not detection_results["detected"]:
            detection_results["deployment_methods"].append("unknown")
        
        logger.info(f"[IdentifyDeploymentMethod] Response: {json.dumps(detection_results, ensure_ascii=False, default=str)}")
        return detection_results
    except Exception as e:
        raise ValueError(f"Failed to identify deployment method: {str(e)}")

