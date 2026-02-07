"""
工具函数模块
"""
import re
from config.default_config import (
    EXTRACT_PARENTHESES,
    FIELD_NAME_MAPPING,
    TARGET_COLUMN
)


def extract_value(raw_value):
    """
    提取字段值
    如果配置了EXTRACT_PARENTHESES=True，则提取括号中的内容
    例如: "4096  (0x1000)" -> "0x1000"
          "12345" -> "12345"
    """
    if not EXTRACT_PARENTHESES:
        return raw_value.strip()
    
    # 查找括号中的内容
    match = re.search(r'\((.*?)\)', raw_value)
    if match:
        return match.group(1).strip()
    
    # 没有括号，返回原始值
    return raw_value.strip()


def map_field_name(log_field_name):
    """
    将日志中的字段名映射为Excel中的字段名
    如果在FIELD_NAME_MAPPING中有配置，则使用映射后的名称
    否则返回原字段名
    """
    if log_field_name in FIELD_NAME_MAPPING:
        return FIELD_NAME_MAPPING[log_field_name]
    return log_field_name


def get_target_column():
    """
    获取目标列号
    支持整数或字符串（列字母）
    """
    if isinstance(TARGET_COLUMN, int):
        return TARGET_COLUMN
    elif isinstance(TARGET_COLUMN, str):
        # 将列字母转换为列号 (A=1, B=2, ...)
        col_str = TARGET_COLUMN.upper()
        col_num = 0
        for char in col_str:
            col_num = col_num * 26 + (ord(char) - ord('A') + 1)
        return col_num
    else:
        raise ValueError(f"TARGET_COLUMN must be int or str, got {type(TARGET_COLUMN)}")
