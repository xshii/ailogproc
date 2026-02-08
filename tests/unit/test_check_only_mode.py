#!/usr/bin/env python3
"""
测试 constraint_checker 的 check_only 模式
"""

import os
import sys
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.plugins.constraint_checker.plugin import ConstraintCheckerPlugin
from src.plugins import run_plugins


class TestCheckOnlyMode(unittest.TestCase):
    """测试仅检查模式"""

    def test_check_only_returns_stop_flag(self):
        """测试：check_only=True 时返回 stop_pipeline 标志"""
        print("\n" + "=" * 70)
        print("测试：check_only 模式返回停止标志")
        print("=" * 70)

        plugin = ConstraintCheckerPlugin()

        # 设置为仅检查模式
        plugin.config["check_only"] = True
        plugin.config["constraint_rules"] = {}

        # Mock parser
        mock_parser = Mock()
        mock_parser.group_by_top_config.return_value = []

        context = {
            "config_parser": {
                "sections": [],
                "parser": mock_parser
            }
        }

        result = plugin.execute(context)

        print(f"validation_passed: {result['validation_passed']}")
        print(f"stop_pipeline: {result.get('stop_pipeline', False)}")

        # 验证返回了停止标志
        self.assertTrue(result.get("stop_pipeline", False))
        print("✅ 返回了 stop_pipeline=True")

    def test_normal_mode_no_stop_flag(self):
        """测试：check_only=False 时不返回停止标志"""
        print("\n" + "=" * 70)
        print("测试：正常模式不返回停止标志")
        print("=" * 70)

        plugin = ConstraintCheckerPlugin()

        # 设置为正常模式
        plugin.config["check_only"] = False
        plugin.config["constraint_rules"] = {}

        # Mock parser
        mock_parser = Mock()
        mock_parser.group_by_top_config.return_value = []

        context = {
            "config_parser": {
                "sections": [],
                "parser": mock_parser
            }
        }

        result = plugin.execute(context)

        print(f"validation_passed: {result['validation_passed']}")
        print(f"stop_pipeline: {result.get('stop_pipeline', False)}")

        # 验证没有返回停止标志
        self.assertFalse(result.get("stop_pipeline", False))
        print("✅ 没有返回 stop_pipeline 标志")

    def test_pipeline_stops_on_check_only(self):
        """测试：check_only 模式下流水线提前终止"""
        print("\n" + "=" * 70)
        print("测试：check_only 模式下流水线提前终止")
        print("=" * 70)

        # Mock 插件
        mock_plugin1 = Mock()
        mock_plugin1.level = 1
        mock_plugin1.enabled = True
        mock_plugin1.dependencies = []
        mock_plugin1.__class__.__name__ = "Plugin1"
        mock_plugin1.execute.return_value = {"result": "plugin1"}

        mock_plugin2 = Mock()
        mock_plugin2.level = 2
        mock_plugin2.enabled = True
        mock_plugin2.dependencies = []
        mock_plugin2.__class__.__name__ = "Plugin2"
        # 返回停止标志
        mock_plugin2.execute.return_value = {
            "result": "plugin2",
            "stop_pipeline": True
        }

        mock_plugin3 = Mock()
        mock_plugin3.level = 3
        mock_plugin3.enabled = True
        mock_plugin3.dependencies = []
        mock_plugin3.__class__.__name__ = "Plugin3"
        mock_plugin3.execute.return_value = {"result": "plugin3"}

        plugins = [mock_plugin1, mock_plugin2, mock_plugin3]
        plugin_configs = {}
        context = {}

        # 执行插件
        result_context = run_plugins(plugins, plugin_configs, context)

        # 验证：plugin1 和 plugin2 执行了，plugin3 没有执行
        self.assertEqual(mock_plugin1.execute.call_count, 1)
        self.assertEqual(mock_plugin2.execute.call_count, 1)
        self.assertEqual(mock_plugin3.execute.call_count, 0)

        print("✅ Plugin1 执行了")
        print("✅ Plugin2 执行了（返回 stop_pipeline=True）")
        print("✅ Plugin3 被跳过（流水线已停止）")

    def test_pipeline_continues_without_stop_flag(self):
        """测试：没有停止标志时流水线继续执行"""
        print("\n" + "=" * 70)
        print("测试：没有停止标志时流水线继续执行")
        print("=" * 70)

        # Mock 插件
        mock_plugin1 = Mock()
        mock_plugin1.level = 1
        mock_plugin1.enabled = True
        mock_plugin1.dependencies = []
        mock_plugin1.__class__.__name__ = "Plugin1"
        mock_plugin1.execute.return_value = {"result": "plugin1"}

        mock_plugin2 = Mock()
        mock_plugin2.level = 2
        mock_plugin2.enabled = True
        mock_plugin2.dependencies = []
        mock_plugin2.__class__.__name__ = "Plugin2"
        # 不返回停止标志
        mock_plugin2.execute.return_value = {"result": "plugin2"}

        mock_plugin3 = Mock()
        mock_plugin3.level = 3
        mock_plugin3.enabled = True
        mock_plugin3.dependencies = []
        mock_plugin3.__class__.__name__ = "Plugin3"
        mock_plugin3.execute.return_value = {"result": "plugin3"}

        plugins = [mock_plugin1, mock_plugin2, mock_plugin3]
        plugin_configs = {}
        context = {}

        # 执行插件
        result_context = run_plugins(plugins, plugin_configs, context)

        # 验证：所有插件都执行了
        self.assertEqual(mock_plugin1.execute.call_count, 1)
        self.assertEqual(mock_plugin2.execute.call_count, 1)
        self.assertEqual(mock_plugin3.execute.call_count, 1)

        print("✅ Plugin1 执行了")
        print("✅ Plugin2 执行了（没有 stop_pipeline）")
        print("✅ Plugin3 也执行了（流水线继续）")


if __name__ == "__main__":
    unittest.main()
