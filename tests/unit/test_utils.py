#!/usr/bin/env python3
"""
工具函数和日志系统单元测试
"""

import os
import sys
import tempfile
import unittest
import logging
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.logger import AppLogger


class TestAppLogger(unittest.TestCase):
    """测试 AppLogger 类"""

    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        # 重置单例
        AppLogger._instance = None
        AppLogger._initialized = False

    def tearDown(self):
        """测试后清理"""
        import shutil

        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

        # 清理 logger 单例
        AppLogger._instance = None
        AppLogger._initialized = False

        # 清理 logger handlers
        logger = logging.getLogger("ailogproc")
        logger.handlers.clear()

    def test_singleton(self):
        """测试单例模式"""
        logger1 = AppLogger()
        logger2 = AppLogger()
        self.assertIs(logger1, logger2)

    def test_init_console_only(self):
        """测试只初始化控制台输出"""
        logger = AppLogger()

        self.assertIsNotNone(logger.logger)
        self.assertEqual(logger.logger.level, logging.DEBUG)

    def test_set_console_level(self):
        """测试设置控制台日志级别"""
        logger = AppLogger()

        logger.set_console_level("DEBUG")
        # 验证级别已更改（通过检查 handler）
        for handler in logger.logger.handlers:
            if isinstance(handler, logging.StreamHandler):
                self.assertEqual(handler.level, logging.DEBUG)

    def test_enable_file_logging(self):
        """测试启用文件日志"""
        log_file = os.path.join(self.temp_dir, "test.log")
        logger = AppLogger()

        logger.enable_file_logging(log_file=log_file, level="DEBUG")

        # 写入日志
        logger.logger.info("Test log message")

        # 验证日志文件已创建
        self.assertTrue(os.path.exists(log_file))

        # 验证日志内容
        with open(log_file, "r", encoding="utf-8") as f:
            content = f.read()
            self.assertIn("Test log message", content)

    def test_auto_log_file_naming(self):
        """测试自动生成日志文件名"""
        logger = AppLogger()

        # 不指定文件名，应自动生成
        logger.enable_file_logging(level="DEBUG")

        # 验证 logs 目录已创建
        logs_dir = Path("logs")
        self.assertTrue(logs_dir.exists())

        # 验证日志文件已创建（格式: app_YYYYMMDD_HHMMSS.log）
        log_files = list(logs_dir.glob("app_*.log"))
        self.assertGreater(len(log_files), 0)

        # 清理测试生成的日志
        for log_file in log_files:
            if log_file.name.startswith("app_"):
                log_file.unlink()

    def test_disable_console(self):
        """测试禁用控制台输出"""
        logger = AppLogger()

        logger.disable_console()

        # 验证没有 StreamHandler
        has_stream_handler = any(
            isinstance(h, logging.StreamHandler) for h in logger.logger.handlers
        )
        self.assertFalse(has_stream_handler)

    def test_log_rotation(self):
        """测试日志轮转配置"""
        log_file = os.path.join(self.temp_dir, "rotation_test.log")
        logger = AppLogger()

        max_bytes = 1024  # 1KB
        backup_count = 3

        logger.enable_file_logging(
            log_file=log_file, max_bytes=max_bytes, backup_count=backup_count
        )

        # 写入大量日志触发轮转
        for i in range(100):
            logger.logger.info(f"Test log message {i} " * 10)

        # 验证备份文件已创建
        backup_files = list(Path(self.temp_dir).glob("rotation_test.log.*"))
        self.assertGreater(len(backup_files), 0)

    def test_log_levels(self):
        """测试不同日志级别"""
        log_file = os.path.join(self.temp_dir, "levels_test.log")
        logger = AppLogger()
        logger.enable_file_logging(log_file=log_file, level="DEBUG")

        # 写入不同级别的日志
        logger.logger.debug("Debug message")
        logger.logger.info("Info message")
        logger.logger.warning("Warning message")
        logger.logger.error("Error message")

        # 验证所有级别都被记录
        with open(log_file, "r", encoding="utf-8") as f:
            content = f.read()
            self.assertIn("Debug message", content)
            self.assertIn("Info message", content)
            self.assertIn("Warning message", content)
            self.assertIn("Error message", content)


class TestUtilityFunctions(unittest.TestCase):
    """测试工具函数"""

    def test_info_function(self):
        """测试 info 函数"""
        from src.utils import info

        # 不应该抛出异常
        try:
            info("Test info message")
        except Exception as e:
            self.fail(f"info() raised {e}")

    def test_warning_function(self):
        """测试 warning 函数"""
        from src.utils import warning

        try:
            warning("Test warning message")
        except Exception as e:
            self.fail(f"warning() raised {e}")

    def test_error_function(self):
        """测试 error 函数"""
        from src.utils import error

        try:
            error("Test error message")
        except Exception as e:
            self.fail(f"error() raised {e}")

    def test_debug_function(self):
        """测试 debug 函数"""
        from src.utils import debug

        try:
            debug("Test debug message")
        except Exception as e:
            self.fail(f"debug() raised {e}")

    def test_get_logger(self):
        """测试 get_logger 函数"""
        from src.utils import get_logger

        logger = get_logger()
        self.assertIsNotNone(logger)
        self.assertIsInstance(logger, AppLogger)

    def test_setup_logger(self):
        """测试 setup_logger 函数"""
        from src.utils import setup_logger, get_logger

        temp_dir = tempfile.mkdtemp()
        log_file = os.path.join(temp_dir, "setup_test.log")

        try:
            setup_logger(
                console_level="INFO",
                enable_file=True,
                log_file=log_file,
                file_level="DEBUG",
            )

            # 写入测试日志
            logger = get_logger()
            logger.logger.info("Test message")

            # 验证日志文件创建
            self.assertTrue(os.path.exists(log_file))

        except Exception as e:
            self.fail(f"setup_logger() raised {e}")
        finally:
            # 清理
            import shutil

            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)


class TestPluginBaseUtils(unittest.TestCase):
    """测试插件基础工具函数"""

    def test_get_target_column_letters(self):
        """测试字母列号转换"""
        from src.plugins.base import get_target_column

        # 单字母
        self.assertEqual(get_target_column({"target_column": "A"}), 1)
        self.assertEqual(get_target_column({"target_column": "B"}), 2)
        self.assertEqual(get_target_column({"target_column": "C"}), 3)
        self.assertEqual(get_target_column({"target_column": "Z"}), 26)

        # 双字母
        self.assertEqual(get_target_column({"target_column": "AA"}), 27)
        self.assertEqual(get_target_column({"target_column": "AB"}), 28)
        self.assertEqual(get_target_column({"target_column": "AZ"}), 52)
        self.assertEqual(get_target_column({"target_column": "BA"}), 53)

    def test_get_target_column_numbers(self):
        """测试数字列号"""
        from src.plugins.base import get_target_column

        self.assertEqual(get_target_column({"target_column": 1}), 1)
        self.assertEqual(get_target_column({"target_column": 26}), 26)
        self.assertEqual(get_target_column({"target_column": 100}), 100)

    def test_get_target_column_lowercase(self):
        """测试小写字母"""
        from src.plugins.base import get_target_column

        self.assertEqual(get_target_column({"target_column": "a"}), 1)
        self.assertEqual(get_target_column({"target_column": "z"}), 26)
        self.assertEqual(get_target_column({"target_column": "aa"}), 27)

    def test_get_target_column_default(self):
        """测试默认列号"""
        from src.plugins.base import get_target_column

        # 不指定 target_column，应返回默认值 "F" (6)
        self.assertEqual(get_target_column({}), 6)


if __name__ == "__main__":
    unittest.main()
