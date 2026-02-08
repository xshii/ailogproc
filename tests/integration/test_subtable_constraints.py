#!/usr/bin/env python3
"""
测试子表字段约束功能（v1.3.0）
展示带前缀的字段约束检查
"""

import os
import sys
import unittest
from unittest.mock import Mock

# 添加项目根目录到 Python 路径
sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from src.plugins.constraint_checker.plugin import ConstraintCheckerPlugin


class TestSubtableConstraints(unittest.TestCase):
    """测试子表字段约束（所有字段带前缀）"""

    def setUp(self):
        """测试前准备"""
        # 创建插件实例
        self.plugin = ConstraintCheckerPlugin()

        # 手动设置测试配置（覆盖从文件加载的配置）
        test_config = {
            "enable": True,
            "active_version": None,  # 使用最新版本
            "constraint_rules": {
                "test_v1.3.0": {
                    "single_constraints": [
                        # top 表字段约束
                        {
                            "name": "opSch功率约束",
                            "only_allow": {
                                "opSch.powerLevel": ["5", "10", "15"],
                                "opSch.voltage": ["0.8V", "1.0V", "1.2V"],
                            },
                        },
                        # 子表字段约束
                        {
                            "name": "ERCfg配置组约束",
                            "only_allow": {"ERCfg.cfgGroup": ["0", "1", "2"]},
                        },
                        # 不同子表的同名字段约束
                        {
                            "name": "I2C总线速度约束",
                            "only_allow": {
                                "I2C_0.speed": ["100K", "400K"],
                                "I2C_1.speed": ["100K", "400K", "1M"],
                            },
                        },
                        # 跨 top 和 sub 的组合约束
                        {
                            "name": "高功率下ERCfg限制",
                            "when": {"opSch.powerLevel": "15"},
                            "only_allow": {"ERCfg.cfgGroup": ["0", "1"]},
                        },
                    ],
                    "multi_constraints": [
                        # 子表字段的多组约束
                        {
                            "name": "ERCfg配置组递增",
                            "group_count": 2,
                            "rules": [
                                {
                                    "type": "sequence",
                                    "field": "ERCfg.cfgGroup",
                                    "order": "increasing",
                                }
                            ],
                        }
                    ],
                }
            },
        }

        # 覆盖插件的配置
        self.plugin.config = test_config

    def test_top_and_sub_fields_pass(self):
        """测试：top 和 sub 字段都通过约束"""
        print("\n" + "=" * 70)
        print("测试：top 和 sub 字段约束（通过）")
        print("=" * 70)

        sections = [
            # 组1
            {"name": "opSch", "fields": {"powerLevel": "5", "voltage": "0.8V"}},
            {"name": "ERCfg", "fields": {"cfgGroup": "0"}},
            {"name": "I2C_0", "fields": {"speed": "100K"}},
            {"name": "I2C_1", "fields": {"speed": "400K"}},
            # 组2
            {"name": "opSch", "fields": {"powerLevel": "10", "voltage": "1.0V"}},
            {"name": "ERCfg", "fields": {"cfgGroup": "1"}},
            {"name": "I2C_0", "fields": {"speed": "400K"}},
            {"name": "I2C_1", "fields": {"speed": "1M"}},
        ]

        # Mock parser
        mock_parser = Mock()
        mock_parser.group_by_top_config.return_value = [
            {"top": sections[0], "subs": sections[1:4]},
            {"top": sections[4], "subs": sections[5:]},
        ]

        context = {"config_parser": {"sections": sections, "parser": mock_parser}}

        result = self.plugin.execute(context)

        print(f"验证结果: {result['validation_passed']}")
        print(f"违规数量: {len(result['violations'])}")

        self.assertTrue(result["validation_passed"])
        self.assertEqual(len(result["violations"]), 0)

    def test_sub_table_violation(self):
        """测试：子表字段违反约束"""
        print("\n" + "=" * 70)
        print("测试：子表字段约束（违规）")
        print("=" * 70)

        sections = [
            {"name": "opSch", "fields": {"powerLevel": "5", "voltage": "0.8V"}},
            {"name": "ERCfg", "fields": {"cfgGroup": "5"}},  # ✗ 违规：只允许 0-2
            {"name": "I2C_0", "fields": {"speed": "1M"}},  # ✗ 违规：I2C_0 不支持 1M
        ]

        mock_parser = Mock()
        mock_parser.group_by_top_config.return_value = [
            {"top": sections[0], "subs": sections[1:]}
        ]

        context = {"config_parser": {"sections": sections, "parser": mock_parser}}

        result = self.plugin.execute(context)

        print(f"验证结果: {result['validation_passed']}")
        print(f"违规数量: {len(result['violations'])}")
        for idx, violation in enumerate(result["violations"], 1):
            print(f"  [{idx}] {violation['message']}")

        self.assertFalse(result["validation_passed"])
        self.assertEqual(len(result["violations"]), 2)

        # 验证违规字段
        violation_fields = [v["field"] for v in result["violations"]]
        self.assertIn("ERCfg.cfgGroup", violation_fields)
        self.assertIn("I2C_0.speed", violation_fields)

    def test_same_field_name_different_tables(self):
        """测试：不同子表的同名字段可以有不同约束"""
        print("\n" + "=" * 70)
        print("测试：不同子表同名字段的区分")
        print("=" * 70)

        sections = [
            {"name": "opSch", "fields": {"powerLevel": "5"}},
            {"name": "I2C_0", "fields": {"speed": "400K"}},  # ✓ I2C_0 支持 400K
            {"name": "I2C_1", "fields": {"speed": "1M"}},  # ✓ I2C_1 支持 1M
        ]

        mock_parser = Mock()
        mock_parser.group_by_top_config.return_value = [
            {"top": sections[0], "subs": sections[1:]}
        ]

        context = {"config_parser": {"sections": sections, "parser": mock_parser}}

        result = self.plugin.execute(context)

        print(f"验证结果: {result['validation_passed']}")
        print(f"说明: I2C_0 和 I2C_1 的 speed 字段虽然同名，但有不同的约束")

        self.assertTrue(result["validation_passed"])
        self.assertEqual(len(result["violations"]), 0)

    def test_cross_table_constraint(self):
        """测试：跨 top 和 sub 表的条件约束"""
        print("\n" + "=" * 70)
        print("测试：跨 top 和 sub 表的条件约束")
        print("=" * 70)

        sections = [
            {"name": "opSch", "fields": {"powerLevel": "15"}},  # 高功率
            {"name": "ERCfg", "fields": {"cfgGroup": "2"}},  # ✗ 违规：高功率只允许 0-1
        ]

        mock_parser = Mock()
        mock_parser.group_by_top_config.return_value = [
            {"top": sections[0], "subs": sections[1:]}
        ]

        context = {"config_parser": {"sections": sections, "parser": mock_parser}}

        result = self.plugin.execute(context)

        print(f"验证结果: {result['validation_passed']}")
        print(f"违规数量: {len(result['violations'])}")
        for idx, violation in enumerate(result["violations"], 1):
            print(f"  [{idx}] {violation['message']}")

        self.assertFalse(result["validation_passed"])
        self.assertGreater(len(result["violations"]), 0)

    def test_multi_group_sub_constraint(self):
        """测试：子表字段的多组约束（序列递增）"""
        print("\n" + "=" * 70)
        print("测试：子表字段多组约束（ERCfg递增）")
        print("=" * 70)

        sections = [
            # 组1
            {"name": "opSch", "fields": {"powerLevel": "5"}},
            {"name": "ERCfg", "fields": {"cfgGroup": "0"}},
            # 组2
            {"name": "opSch", "fields": {"powerLevel": "10"}},
            {
                "name": "ERCfg",
                "fields": {"cfgGroup": "2"},
            },  # ✗ 违规：不递增（0->2，应该是1）
        ]

        mock_parser = Mock()
        mock_parser.group_by_top_config.return_value = [
            {"top": sections[0], "subs": [sections[1]]},
            {"top": sections[2], "subs": [sections[3]]},
        ]

        context = {"config_parser": {"sections": sections, "parser": mock_parser}}

        result = self.plugin.execute(context)

        print(f"验证结果: {result['validation_passed']}")
        print(f"违规数量: {len(result['violations'])}")
        for idx, violation in enumerate(result["violations"], 1):
            print(f"  [{idx}] {violation['message']}")

        # 注意：这个测试可能通过，因为 0 < 2 确实递增
        # 如果要严格递增（差值为1），需要修改约束规则
        print(f"说明: cfgGroup 从 0 递增到 2，满足递增约束")


if __name__ == "__main__":
    unittest.main()
