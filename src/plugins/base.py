"""
插件基类
"""

import os
from abc import ABC, abstractmethod

import yaml


class Plugin(ABC):
    """
    插件基类

    插件层级：
    - Level 1: Extractor（提取层）- 从日志中提取信息
    - Level 2: Processor（处理层）- 处理提取的数据
    - Level 3: 小插件 - 轻量级收尾工作
    """

    # 插件层级（子类需要设置）
    level = 0  # 1=Extractor, 2=Processor, 3=小插件

    # 依赖的插件名列表（子类可选设置）
    dependencies = []

    def __init__(self):
        """初始化插件，自动加载配置文件"""
        self.config = self._load_config()
        self.enabled = self.config.get("enable", True)

    def _load_config(self) -> dict:
        """从插件目录加载 config.yaml"""
        # 获取插件类所在的目录
        plugin_dir = os.path.dirname(
            os.path.abspath(self.__class__.__module__.replace(".", os.sep) + ".py")
        )

        # 查找 config.yaml
        config_file = os.path.join(plugin_dir, "config.yaml")

        if not os.path.exists(config_file):
            # 尝试从实际模块路径查找
            import inspect

            plugin_file = inspect.getfile(self.__class__)
            plugin_dir = os.path.dirname(plugin_file)
            config_file = os.path.join(plugin_dir, "config.yaml")

        if os.path.exists(config_file):
            with open(config_file, encoding="utf-8") as f:
                return yaml.safe_load(f) or {}

        # 如果配置文件不存在，返回默认配置
        return {"enable": True}

    @abstractmethod
    def execute(self, context: dict) -> dict:
        """
        执行插件逻辑

        Args:
            context: 包含所有上游插件输出的字典
                    例如: {
                        'trace_file': '/path/to/trace.txt',
                        'excel_file': '/path/to/template.xlsx',
                        'config_parser': {'sections': [...], ...},
                        'excel_writer': {'output_file': '/path/to/output.xlsx', ...},
                    }

        Returns:
            dict: 当前插件的输出，会被合并到 context 中
        """

    @property
    def name(self) -> str:
        """返回插件名称（类名）"""
        return self.__class__.__name__


# ==================== 公共工具函数 ====================


def get_target_column(config: dict) -> int:
    """
    获取目标列号
    支持整数或字符串（列字母）

    Args:
        config: 配置字典

    Returns:
        int: 列号（从1开始）
    """
    target_column = config.get("target_column", "F")

    if isinstance(target_column, int):
        return target_column
    if isinstance(target_column, str):
        # 将列字母转换为列号 (A=1, B=2, ...)
        col_str = target_column.upper()
        col_num = 0
        for char in col_str:
            col_num = col_num * 26 + (ord(char) - ord("A") + 1)
        return col_num

    raise ValueError(f"target_column must be int or str, got {type(target_column)}")
