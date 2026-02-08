#!/usr/bin/env python3
"""
配置约束检查插件测试
"""

import os
import sys
import unittest
from unittest.mock import Mock

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.plugins.constraint_checker.plugin import ConstraintCheckerPlugin


class TestConstraintChecker(unittest.TestCase):
    """测试 ConstraintChecker 插件"""

    def setUp(self):
        """测试前准备"""
        self.plugin = ConstraintCheckerPlugin()

    def test_plugin_init(self):
        """测试插件初始化"""
        self.assertIsNotNone(self.plugin.config)
        self.assertEqual(self.plugin.level, 2)
        self.assertIn("config_parser", self.plugin.dependencies)

    def test_get_active_rules(self):
        """测试获取激活规则"""
        version, rules = self.plugin._get_active_rules()
        self.assertIsNotNone(version)
        self.assertIsNotNone(rules)
        # 应该返回最新版本（按版本号排序）
        self.assertTrue(version.startswith("1."))

    def test_single_constraint_only_allow_pass(self):
        """测试单组约束 - only_allow 通过"""
        # 准备测试数据
        sections = [
            {
                "name": "opSch",
                "fields": {
                    "systemMode": "1",
                    "debugLevel": "2",
                    "powerMode": "low",
                },
            }
        ]

        # Mock parser
        parser = Mock()
        parser.group_by_top_config = Mock(
            return_value=[{"top": sections[0], "subs": []}]
        )

        context = {"config_parser": {"sections": sections, "parser": parser}}

        result = self.plugin.execute(context)

        # 验证通过
        self.assertTrue(result.get("validation_passed"))
        self.assertEqual(len(result.get("violations", [])), 0)

    def test_single_constraint_only_allow_fail(self):
        """测试单组约束 - only_allow 失败"""
        # 准备测试数据（debugLevel=5 不在允许列表中）
        sections = [
            {
                "name": "opSch",
                "fields": {
                    "systemMode": "1",
                    "debugLevel": "5",  # 不允许的值
                    "powerMode": "low",
                },
            }
        ]

        # Mock parser
        parser = Mock()
        parser.group_by_top_config = Mock(
            return_value=[{"top": sections[0], "subs": []}]
        )

        context = {"config_parser": {"sections": sections, "parser": parser}}

        result = self.plugin.execute(context)

        # 验证失败
        self.assertFalse(result.get("validation_passed"))
        self.assertGreater(len(result.get("violations", [])), 0)

    def test_single_constraint_forbid_fail(self):
        """测试单组约束 - forbid 失败"""
        # 准备测试数据（dangerousFlag=1 被禁止）
        sections = [
            {
                "name": "opSch",
                "fields": {
                    "systemMode": "1",
                    "debugLevel": "2",
                    "dangerousFlag": "1",  # 禁止的值
                },
            }
        ]

        # Mock parser
        parser = Mock()
        parser.group_by_top_config = Mock(
            return_value=[{"top": sections[0], "subs": []}]
        )

        context = {"config_parser": {"sections": sections, "parser": parser}}

        result = self.plugin.execute(context)

        # 验证失败
        self.assertFalse(result.get("validation_passed"))
        violations = result.get("violations", [])
        self.assertGreater(len(violations), 0)
        self.assertEqual(violations[0]["type"], "forbid")

    def test_multi_constraint_same_value_pass(self):
        """测试多组约束 - same_value 通过"""
        # 准备测试数据（两组的 systemMode 相同，ERCfg.cfgGroup 递增）
        sections = [
            {"name": "opSch", "fields": {"systemMode": "1"}},
            {"name": "ERCfg", "fields": {"cfgGroup": "0"}},
            {"name": "opSch", "fields": {"systemMode": "1"}},
            {"name": "ERCfg", "fields": {"cfgGroup": "1"}},
        ]

        # Mock parser
        parser = Mock()
        parser.group_by_top_config = Mock(
            return_value=[
                {"top": sections[0], "subs": [sections[1]]},
                {"top": sections[2], "subs": [sections[3]]},
            ]
        )

        context = {"config_parser": {"sections": sections, "parser": parser}}

        result = self.plugin.execute(context)

        # same_value 约束应该通过
        self.assertTrue(result.get("validation_passed"))

    def test_multi_constraint_same_value_fail(self):
        """测试多组约束 - same_value 失败"""
        # 准备测试数据（两组的 systemMode 不同）
        sections = [
            {"name": "opSch", "fields": {"systemMode": "1"}},
            {"name": "ERCfg", "fields": {}},
            {"name": "opSch", "fields": {"systemMode": "2"}},
        ]

        # Mock parser
        parser = Mock()
        parser.group_by_top_config = Mock(
            return_value=[
                {"top": sections[0], "subs": [sections[1]]},
                {"top": sections[2], "subs": []},
            ]
        )

        context = {"config_parser": {"sections": sections, "parser": parser}}

        result = self.plugin.execute(context)

        # same_value 约束应该失败
        violations = result.get("violations", [])
        # 查找 same_value 类型的违规
        same_value_violations = [v for v in violations if v["type"] == "same_value"]
        if same_value_violations:
            self.assertFalse(result.get("validation_passed"))

    def test_empty_sections(self):
        """测试空配置列表"""
        context = {"config_parser": {"sections": [], "parser": None}}

        result = self.plugin.execute(context)

        # 应该直接通过
        self.assertTrue(result.get("validation_passed"))
        self.assertEqual(len(result.get("violations", [])), 0)

    def test_match_conditions(self):
        """测试条件匹配"""
        fields = {"systemMode": "1", "debugLevel": "2"}

        # 单条件匹配
        self.assertTrue(self.plugin._match_conditions(fields, {"systemMode": "1"}))

        # 多条件匹配（全部满足）
        self.assertTrue(
            self.plugin._match_conditions(
                fields, {"systemMode": "1", "debugLevel": "2"}
            )
        )

        # 条件不匹配
        self.assertFalse(self.plugin._match_conditions(fields, {"systemMode": "2"}))

        # 部分条件不匹配
        self.assertFalse(
            self.plugin._match_conditions(
                fields, {"systemMode": "1", "debugLevel": "3"}
            )
        )


if __name__ == "__main__":
    unittest.main()
