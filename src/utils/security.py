"""
安全工具函数 - 提供路径验证、输入校验等安全功能
"""

import os
from pathlib import Path
from typing import Optional


class SecurityError(Exception):
    """安全相关的异常"""


def validate_path(
    base_dir: str, file_path: str, must_exist: bool = False
) -> str:
    """
    验证文件路径的安全性，防止路径遍历攻击.

    Args:
        base_dir: 基础目录（必须是绝对路径）
        file_path: 要验证的文件路径（可以是相对路径或绝对路径）
        must_exist: 是否要求路径必须存在

    Returns:
        str: 验证后的绝对路径

    Raises:
        SecurityError: 如果检测到路径遍历攻击
        FileNotFoundError: 如果 must_exist=True 且文件不存在
        ValueError: 如果参数无效

    Examples:
        >>> validate_path("/data", "file.txt")
        '/data/file.txt'
        >>> validate_path("/data", "../etc/passwd")  # 抛出 SecurityError
    """
    if not base_dir:
        raise ValueError("base_dir cannot be empty")

    if not file_path:
        raise ValueError("file_path cannot be empty")

    # 确保base_dir是绝对路径
    abs_base = os.path.abspath(base_dir)

    # 如果file_path是绝对路径，直接使用；否则相对于base_dir
    if os.path.isabs(file_path):
        abs_path = os.path.abspath(file_path)
    else:
        abs_path = os.path.abspath(os.path.join(abs_base, file_path))

    # 规范化路径（解析符号链接）
    try:
        real_path = os.path.realpath(abs_path)
        real_base = os.path.realpath(abs_base)
    except (OSError, RuntimeError) as e:
        raise SecurityError(f"Failed to resolve path: {e}") from e

    # 检查路径是否在基础目录内
    if not real_path.startswith(real_base + os.sep) and real_path != real_base:
        raise SecurityError(
            f"Path traversal detected: '{file_path}' resolves outside '{base_dir}'"
        )

    # 检查路径是否存在（如果需要）
    if must_exist and not os.path.exists(real_path):
        raise FileNotFoundError(f"Path does not exist: {real_path}")

    return real_path


def validate_file_extension(
    file_path: str, allowed_extensions: list[str]
) -> bool:
    """
    验证文件扩展名是否在允许列表中.

    Args:
        file_path: 文件路径
        allowed_extensions: 允许的扩展名列表（包含点号，如 ['.xlsx', '.xls']）

    Returns:
        bool: 是否为允许的扩展名

    Examples:
        >>> validate_file_extension("data.xlsx", [".xlsx", ".xls"])
        True
        >>> validate_file_extension("script.py", [".xlsx", ".xls"])
        False
    """
    if not file_path:
        return False

    # 获取文件扩展名（转为小写）
    _, ext = os.path.splitext(file_path.lower())

    # 确保allowed_extensions中的扩展名也是小写
    allowed_lower = [e.lower() for e in allowed_extensions]

    return ext in allowed_lower


def sanitize_filename(filename: str, replacement: str = "_") -> str:
    """
    清理文件名，移除危险字符.

    Args:
        filename: 原始文件名
        replacement: 用于替换危险字符的字符串

    Returns:
        str: 清理后的文件名

    Examples:
        >>> sanitize_filename("file<>name.txt")
        'file__name.txt'
        >>> sanitize_filename("../../etc/passwd", "")
        'etcpasswd'
    """
    if not filename:
        return ""

    # Windows和Unix通用的危险字符
    dangerous_chars = '<>:"|?*\\/\x00'

    # 移除危险字符
    safe_name = "".join(
        replacement if c in dangerous_chars else c for c in filename
    )

    # 移除开头的点号（隐藏文件）和空格
    safe_name = safe_name.lstrip(". ")

    # 确保不为空
    if not safe_name:
        safe_name = "unnamed"

    return safe_name


def validate_directory_writable(directory: str) -> bool:
    """
    检查目录是否可写.

    Args:
        directory: 目录路径

    Returns:
        bool: 目录是否存在且可写

    Examples:
        >>> validate_directory_writable("/tmp")
        True
        >>> validate_directory_writable("/nonexistent")
        False
    """
    if not directory:
        return False

    try:
        # 确保目录存在
        if not os.path.isdir(directory):
            return False

        # 检查写权限
        return os.access(directory, os.W_OK)
    except (OSError, ValueError):
        return False


def create_safe_directory(directory: str, mode: int = 0o755) -> bool:
    """
    安全地创建目录（如果不存在）.

    Args:
        directory: 目录路径
        mode: 目录权限模式（默认 0o755）

    Returns:
        bool: 是否成功创建或已存在

    Examples:
        >>> create_safe_directory("/tmp/test_dir")
        True
    """
    if not directory:
        return False

    try:
        # 使用 exist_ok=True 避免竞争条件
        os.makedirs(directory, mode=mode, exist_ok=True)
        return True
    except (OSError, PermissionError):
        return False
