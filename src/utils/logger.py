"""
应用日志模块 - 统一的日志记录工具
支持控制台输出、文件重定向、日志等级配置、日志轮转
"""

import logging
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional


class AppLogger:
    """应用日志器 - 单例模式"""

    _instance: Optional["AppLogger"] = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if AppLogger._initialized:
            return

        self.logger = logging.getLogger("ailogproc")
        self.logger.setLevel(logging.DEBUG)  # 捕获所有级别
        self.logger.propagate = False

        # 默认只输出到控制台
        self._setup_console_handler()
        AppLogger._initialized = True

    def _setup_console_handler(self):
        """设置控制台处理器"""
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)  # 默认显示 INFO 及以上

        # 格式化器
        formatter = logging.Formatter(
            "%(message)s"  # 简洁格式，只显示消息
        )
        console_handler.setFormatter(formatter)

        self.logger.addHandler(console_handler)
        self._console_handler = console_handler

    def set_console_level(self, level: str):
        """设置控制台日志级别

        Args:
            level: 日志级别字符串 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        level_map = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL,
        }

        log_level = level_map.get(level.upper(), logging.INFO)
        self._console_handler.setLevel(log_level)

    def enable_file_logging(
        self,
        log_file: Optional[str] = None,
        level: str = "DEBUG",
        max_bytes: int = 1000 * 1024 * 1024,  # 1000MB
        backup_count: int = 5,  # 保留5个备份文件
    ):
        """启用文件日志记录（支持日志轮转）

        Args:
            log_file: 日志文件路径，None则使用默认路径（带时间后缀）
            level: 文件日志级别
            max_bytes: 单个日志文件最大字节数（默认1000MB）
            backup_count: 保留的备份文件数量（默认5个）
        """
        if log_file is None:
            # 生成默认日志文件名（带时间后缀）
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_dir = Path("logs")
            log_dir.mkdir(exist_ok=True)
            log_file = log_dir / f"app_{timestamp}.log"

        # 使用RotatingFileHandler实现日志轮转
        file_handler = RotatingFileHandler(
            filename=str(log_file),
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )

        level_map = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL,
        }
        file_handler.setLevel(level_map.get(level.upper(), logging.DEBUG))

        # 文件格式：包含时间戳和级别
        formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(formatter)

        self.logger.addHandler(file_handler)
        self._file_handler = file_handler

    def disable_console(self):
        """禁用控制台输出（仅输出到文件）"""
        if hasattr(self, "_console_handler"):
            self.logger.removeHandler(self._console_handler)

    def enable_console(self):
        """重新启用控制台输出"""
        if hasattr(self, "_console_handler"):
            if self._console_handler not in self.logger.handlers:
                self.logger.addHandler(self._console_handler)

    # 便捷方法
    def debug(self, msg, *args, **kwargs):
        """DEBUG 级别日志"""
        self.logger.debug(msg, *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        """INFO 级别日志"""
        self.logger.info(msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        """WARNING 级别日志"""
        self.logger.warning(msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        """ERROR 级别日志"""
        self.logger.error(msg, *args, **kwargs)

    def critical(self, msg, *args, **kwargs):
        """CRITICAL 级别日志"""
        self.logger.critical(msg, *args, **kwargs)

    def exception(self, msg, *args, **kwargs):
        """记录异常信息（包含堆栈跟踪）"""
        self.logger.exception(msg, *args, **kwargs)


# 全局日志器实例
_logger = AppLogger()


# 简化的函数接口（兼容 print 风格）
def log(msg, level="INFO"):
    """记录日志（兼容 print 风格）

    Args:
        msg: 消息内容
        level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    level_func = {
        "DEBUG": _logger.debug,
        "INFO": _logger.info,
        "WARNING": _logger.warning,
        "ERROR": _logger.error,
        "CRITICAL": _logger.critical,
    }

    func = level_func.get(level.upper(), _logger.info)
    func(msg)


# 快捷函数
def debug(msg):
    """DEBUG 日志"""
    _logger.debug(msg)


def info(msg):
    """INFO 日志"""
    _logger.info(msg)


def warning(msg):
    """WARNING 日志"""
    _logger.warning(msg)


def error(msg):
    """ERROR 日志"""
    _logger.error(msg)


def critical(msg):
    """CRITICAL 日志"""
    _logger.critical(msg)


def exception(msg):
    """异常日志（包含堆栈）"""
    _logger.exception(msg)


# 配置函数
def setup_logger(
    console_level="INFO",
    enable_file=False,
    log_file=None,
    file_level="DEBUG",
    max_bytes=1000 * 1024 * 1024,  # 1000MB
    backup_count=5,  # 保留5个备份
):
    """配置日志器

    Args:
        console_level: 控制台日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        enable_file: 是否启用文件日志
        log_file: 文件日志路径（None 使用默认，自动添加时间后缀）
        file_level: 文件日志级别
        max_bytes: 单个日志文件最大字节数（默认1000MB）
        backup_count: 保留的备份文件数量（默认5个）
    """
    _logger.set_console_level(console_level)

    if enable_file:
        _logger.enable_file_logging(log_file, file_level, max_bytes, backup_count)


def get_logger():
    """获取日志器实例"""
    return _logger
