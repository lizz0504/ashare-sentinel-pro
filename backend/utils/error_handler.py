"""
Error Handling Utilities
统一的错误处理辅助函数
"""
from typing import Union, Dict, Any
from fastapi import HTTPException
import logging


def create_error_response(status_code: int, detail: Union[str, Dict[str, Any]]):
    """
    创建统一的错误响应

    Args:
        status_code: HTTP状态码
        detail: 错误详情

    Returns:
        HTTPException实例
    """
    return HTTPException(status_code=status_code, detail=detail)


def handle_api_error(func):
    """
    API错误处理装饰器
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except HTTPException:
            raise
        except Exception as e:
            logging.error(f"API Error in {func.__name__}: {str(e)}")
            raise create_error_response(500, f"Internal server error: {str(e)}")
    return wrapper


def safe_execute(operation_name: str, operation_func, *args, **kwargs):
    """
    安全执行操作，统一错误处理

    Args:
        operation_name: 操作名称
        operation_func: 操作函数
        *args, **kwargs: 操作参数

    Returns:
        操作结果，失败时返回None
    """
    try:
        result = operation_func(*args, **kwargs)
        return result
    except Exception as e:
        print(f"[ERROR] Failed to execute {operation_name}: {e}")
        return None