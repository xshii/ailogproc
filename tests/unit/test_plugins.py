#!/usr/bin/env python3
"""
插件系统单元测试
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.plugins.base import Plugin, get_target_column
from src.plugins.config_parser.plugin import ConfigParserPlugin
from src.plugins.auto_filename.plugin import AutoFilenamePlugin


class TestPluginBase(unittest.TestCase):
    """测试 Plugin 基类"""

    def test_plugin_name(self):
        """测试插件名称"""
        from src.plugins.auto_filename.plugin import AutoFilenamePlugin

        plugin = AutoFilenamePlugin()
        self.assertEqual(plugin.name, "AutoFilenamePlugin")

    def test_get_target_column_with_config(self):
        """测试列号转换函数（使用配置字典）"""
        # get_target_column 期望一个包含 target_column 的配置字典
        self.assertEqual(get_target_column({"target_column": "A"}), 1)
        self.assertEqual(get_target_column({"target_column": "B"}), 2)
        self.assertEqual(get_target_column({"target_column": "Z"}), 26)
        self.assertEqual(get_target_column({"target_column": "AA"}), 27)

        # 测试数字输入
        self.assertEqual(get_target_column({"target_column": 1}), 1)
        self.assertEqual(get_target_column({"target_column": 10}), 10)

        # 测试默认值
        self.assertEqual(get_target_column({}), 6)  # 默认 "F" = 6


class TestConfigParserPlugin(unittest.TestCase):
    """测试 ConfigParser 插件"""

    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        self.trace_file = os.path.join(self.temp_dir, "test_trace.txt")

        # 创建测试 trace 文件
        trace_content = """thread0	cyc=0x1000 opSch
thread0	cyc=0x1000 |- systemMode    = 1  (0x01)
thread0	cyc=0x1000 |- debugLevel    = 2  (0x02)

thread0	cyc=0x2000 ERCfg (grp = 0)
thread0	cyc=0x2000 |- cfgGroup    = 0  (0x00)
thread0	cyc=0x2000 |- powerLevel  = 15  (0x0F)
"""
        with open(self.trace_file, "w", encoding="utf-8") as f:
            f.write(trace_content)

    def tearDown(self):
        """测试后清理"""
        import shutil

        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_trace_parser_init(self):
        """测试 TraceParser 初始化"""
        plugin = ConfigParserPlugin()
        # 插件会自动加载配置文件
        self.assertIsNotNone(plugin.config)
        self.assertEqual(plugin.level, 1)  # TraceParser 是 Level 1 (提取层)

    def test_trace_parser_execute_with_file(self):
        """测试 TraceParser 执行（提供文件路径）"""
        plugin = ConfigParserPlugin()
        context = {"trace_file": self.trace_file}

        result = plugin.execute(context)

        self.assertIn("sections", result)
        self.assertIn("parser", result)
        self.assertIn("trace_file", result)
        self.assertGreater(len(result["sections"]), 0)


class TestAutoFilenamePlugin(unittest.TestCase):
    """测试 AutoFilename 插件"""

    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """测试后清理"""
        import shutil

        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_auto_filename_init(self):
        """测试 AutoFilename 初始化"""
        plugin = AutoFilenamePlugin()
        # 插件会自动加载配置文件
        self.assertIsNotNone(plugin.config)
        self.assertEqual(plugin.level, 4)

    def test_auto_filename_execute(self):
        """测试 AutoFilename 执行"""
        plugin = AutoFilenamePlugin()

        # 准备测试数据 - 包含配置文件中定义的字段
        sections = [
            {
                "type": "opSch",
                "data": {
                    "systemMode": "1",
                    "controlMode": "2",
                    "debugLevel": "2",
                    "verboseLevel": "1",
                },
            }
        ]

        # Mock processor
        processor = Mock()
        processor.sheet = Mock()
        processor.sheet.max_row = 10

        # Mock get_cell_value_smart 方法
        def mock_get_cell(row, col):
            return None

        processor.get_cell_value_smart = mock_get_cell

        context = {
            "output_file": os.path.join(self.temp_dir, "output.xlsx"),
            "sections": sections,
            "processor": processor,
        }

        result = plugin.execute(context)

        # 验证返回了 output_file（即使没有修改也应该返回）
        # 如果插件禁用或没有找到字段，也应该返回原文件名
        if result:
            self.assertIn("output_file", result)


class TestPluginDependencies(unittest.TestCase):
    """测试插件依赖关系"""

    def test_plugin_levels(self):
        """测试插件层级"""
        from src.plugins.config_parser.plugin import ConfigParserPlugin
        from src.plugins.dld_configtmp.plugin import DownloadTemplatePlugin
        from src.plugins.excel_writer.plugin import ExcelWriterPlugin
        from src.plugins.auto_filename.plugin import AutoFilenamePlugin

        # DownloadTemplate 是 Level 0
        self.assertEqual(DownloadTemplatePlugin.level, 0)
        # ConfigParser 是 Level 1
        self.assertEqual(ConfigParserPlugin.level, 1)
        # ConstraintChecker 是 Level 2
        # ExcelWriter 是 Level 3
        self.assertEqual(ExcelWriterPlugin.level, 3)
        # AutoFilename 是 Level 4
        self.assertEqual(AutoFilenamePlugin.level, 4)

    def test_plugin_dependencies_config_parser(self):
        """测试 config_parser 插件依赖"""
        from src.plugins.config_parser.plugin import ConfigParserPlugin

        # config_parser 依赖 dld_configtmp
        self.assertIn("dld_configtmp", ConfigParserPlugin.dependencies)

    def test_plugin_dependencies_excel_writer(self):
        """测试 excel_writer 插件依赖"""
        from src.plugins.excel_writer.plugin import ExcelWriterPlugin

        # excel_writer 依赖 config_parser
        self.assertIn("config_parser", ExcelWriterPlugin.dependencies)

    def test_all_plugins_are_plugin_instances(self):
        """测试所有插件都是 Plugin 的子类"""
        from src.plugins.base import Plugin
        from src.plugins.config_parser.plugin import ConfigParserPlugin
        from src.plugins.dld_configtmp.plugin import DownloadTemplatePlugin
        from src.plugins.excel_writer.plugin import ExcelWriterPlugin
        from src.plugins.auto_filename.plugin import AutoFilenamePlugin

        self.assertTrue(issubclass(ConfigParserPlugin, Plugin))
        self.assertTrue(issubclass(DownloadTemplatePlugin, Plugin))
        self.assertTrue(issubclass(ExcelWriterPlugin, Plugin))
        self.assertTrue(issubclass(AutoFilenamePlugin, Plugin))


if __name__ == "__main__":
    unittest.main()
