"""
========================================
日志装饰器模块
用于记录函数的输入参数、输出结果和异常信息
========================================
"""

import logging
import json
import functools
from typing import Any, Callable, Dict
import traceback


# 配置日志格式
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def safe_json_dumps(obj: Any, max_length: int = 1000) -> str:
    """
    安全地将对象转换为JSON字符串，处理不可序列化的对象
    
    Args:
        obj: 要序列化的对象
        max_length: 最大字符串长度，超过会被截断
        
    Returns:
        JSON字符串
    """
    try:
        result = json.dumps(obj, ensure_ascii=False, default=str, indent=2)
        if len(result) > max_length:
            result = result[:max_length] + "... (truncated)"
        return result
    except Exception:
        return str(obj)[:max_length] + ("... (truncated)" if len(str(obj)) > max_length else "")


def log_function_calls(
    log_input: bool = True,
    log_output: bool = True,
    log_exceptions: bool = True,
    max_log_length: int = 1000,
    logger_name: str = None
) -> Callable:
    """
    日志装饰器，用于记录函数的输入、输出和异常
    
    Args:
        log_input: 是否记录输入参数
        log_output: 是否记录输出结果
        log_exceptions: 是否记录异常信息
        max_log_length: 日志内容最大长度
        logger_name: 自定义logger名称
        
    Returns:
        装饰器函数
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 使用自定义logger或默认logger
            func_logger = logging.getLogger(logger_name or f"{func.__module__}.{func.__name__}")
            
            function_name = f"{func.__module__}.{func.__name__}"
            
            # 记录函数开始执行
            func_logger.info(f"🚀 开始执行函数: {function_name}")
            
            # 记录输入参数
            if log_input:
                input_info = {
                    "args": args,
                    "kwargs": kwargs
                }
                func_logger.info(f"📥 输入参数: {safe_json_dumps(input_info, max_log_length)}")
            
            try:
                # 执行原函数
                result = func(*args, **kwargs)
                
                # 记录输出结果
                if log_output:
                    func_logger.info(f"📤 输出结果: {safe_json_dumps(result, max_log_length)}")
                
                func_logger.info(f"✅ 函数执行成功: {function_name}")
                return result
                
            except Exception as e:
                # 记录异常信息
                if log_exceptions:
                    error_info = {
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                        "traceback": traceback.format_exc()
                    }
                    func_logger.error(f"❌ 函数执行异常: {function_name}")
                    func_logger.error(f"🔥 异常详情: {safe_json_dumps(error_info, max_log_length * 2)}")
                
                # 重新抛出异常
                raise
                
        return wrapper
    return decorator


def simple_log(func: Callable = None) -> Callable:
    """
    简化版本的日志装饰器，使用默认配置
    
    Args:
        func: 要装饰的函数
        
    Returns:
        装饰后的函数
    """
    def decorator(f: Callable) -> Callable:
        if f is None:
            raise ValueError("simple_log装饰器必须应用于一个函数")
        return log_function_calls()(f)
    
    # 如果func不为None，说明是直接使用@simple_log而不是@simple_log()
    if func is not None:
        return decorator(func)
    
    # 如果func为None，说明是使用@simple_log()形式，返回装饰器
    return decorator


def tool_log(func: Callable = None) -> Callable:
    """
    专门为工具函数设计的日志装饰器
    
    Args:
        func: 要装饰的工具函数
        
    Returns:
        装饰后的函数
    """
    def decorator(f: Callable) -> Callable:
        if f is None:
            raise ValueError("tool_log装饰器必须应用于一个函数")
        
        return log_function_calls(
            log_input=True,
            log_output=True,
            log_exceptions=True,
            max_log_length=2000,
            logger_name=f"tools.{f.__name__}"
        )(f)
    
    # 如果func不为None，说明是直接使用@tool_log而不是@tool_log()
    if func is not None:
        return decorator(func)
    
    # 如果func为None，说明是使用@tool_log()形式，返回装饰器
    return decorator


# 示例使用方法
if __name__ == "__main__":
    
    @log_function_calls()
    def test_function(x: int, y: int, name: str = "test") -> Dict[str, Any]:
        """测试函数"""
        if x < 0:
            raise ValueError("x不能为负数")
        return {"result": x + y, "name": name}
    
    @simple_log
    def simple_test(message: str) -> str:
        """简单测试函数"""
        return f"处理消息: {message}"
    
    @tool_log
    def tool_test(config: Dict[str, Any]) -> str:
        """工具函数测试"""
        return f"工具执行结果: {config}"
    
    # 测试正常执行
    print("=== 测试正常执行 ===")
    result1 = test_function(1, 2, name="测试")
    print(f"返回结果: {result1}")
    
    print("\n=== 测试简单装饰器 ===")
    result2 = simple_test("Hello World")
    print(f"返回结果: {result2}")
    
    print("\n=== 测试工具装饰器 ===")
    result3 = tool_test({"key": "value", "number": 123})
    print(f"返回结果: {result3}")
    
    # 测试异常情况
    print("\n=== 测试异常情况 ===")
    try:
        test_function(-1, 2)
    except ValueError as e:
        print(f"捕获异常: {e}")