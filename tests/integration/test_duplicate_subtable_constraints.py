#!/usr/bin/env python3
"""
测试重复子表的约束检查
展示如何对多个同名子表进行不同的约束
"""

import os
import sys
import unittest
from unittest.mock import Mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.plugins.constraint_checker.plugin import ConstraintCheckerPlugin


class TestDuplicateSubtableConstraints(unittest.TestCase):
    """测试重复子表的约束"""

    def setUp(self):
        """测试前准备"""
        self.plugin = ConstraintCheckerPlugin()

        # 配置约束规则
        test_config = {
            "enable": True,
            "active_version": None,
            "constraint_rules": {
                "test_duplicate": {
                    "single_constraints": [
                        # top 表约束
                        {
                            "name": "opSch功率约束",
                            "only_allow": {
                                "opSch.powerLevel": ["5", "10", "15"]
                            }
                        },
                        # 不同 I2C 总线有不同的速度限制
                        {
                            "name": "I2C总线速度约束",
                            "only_allow": {
                                "I2C.0.speed": ["100K", "400K"],      # I2C_0 不支持高速
                                "I2C.1.speed": ["100K", "400K", "1M"], # I2C_1 支持高速
                                "I2C.2.speed": ["100K"]                # I2C_2 只支持低速
                            }
                        },
                        # 不同 I2C 总线的地址范围约束
                        {
                            "name": "I2C地址约束",
                            "only_allow": {
                                "I2C.0.addr": ["0x10", "0x20", "0x30"],
                                "I2C.1.addr": ["0x40", "0x50", "0x60"],
                                "I2C.2.addr": ["0x70", "0x80"]
                            }
                        }
                    ],
                    "multi_constraints": []
                }
            }
        }

        self.plugin.config = test_config

    def test_multiple_i2c_pass(self):
        """测试：多个 I2C 配置都符合约束"""
        print("\n" + "=" * 70)
        print("测试：多个同名 I2C 子表（通过）")
        print("=" * 70)

        sections = [
            {"name": "opSch", "fields": {"powerLevel": "5"}},
            {"name": "I2C", "fields": {"speed": "100K", "addr": "0x10"}},  # I2C.0
            {"name": "I2C", "fields": {"speed": "1M", "addr": "0x40"}},    # I2C.1
            {"name": "I2C", "fields": {"speed": "100K", "addr": "0x70"}},  # I2C.2
        ]

        mock_parser = Mock()
        mock_parser.group_by_top_config.return_value = [
            {
                "top": sections[0],
                "subs": sections[1:]
            }
        ]

        context = {
            "config_parser": {
                "sections": sections,
                "parser": mock_parser
            }
        }

        result = self.plugin.execute(context)

        print(f"验证结果: {result['validation_passed']}")
        print(f"违规数量: {len(result['violations'])}")

        self.assertTrue(result['validation_passed'])
        self.assertEqual(len(result['violations']), 0)

    def test_i2c_speed_violation(self):
        """测试：某个 I2C 的速度违反约束"""
        print("\n" + "=" * 70)
        print("测试：I2C 速度约束违规")
        print("=" * 70)

        sections = [
            {"name": "opSch", "fields": {"powerLevel": "5"}},
            {"name": "I2C", "fields": {"speed": "100K", "addr": "0x10"}},  # I2C.0 ✓
            {"name": "I2C", "fields": {"speed": "400K", "addr": "0x40"}},  # I2C.1 ✓
            {"name": "I2C", "fields": {"speed": "400K", "addr": "0x70"}},  # I2C.2 ✗ 只支持100K
        ]

        mock_parser = Mock()
        mock_parser.group_by_top_config.return_value = [
            {
                "top": sections[0],
                "subs": sections[1:]
            }
        ]

        context = {
            "config_parser": {
                "sections": sections,
                "parser": mock_parser
            }
        }

        result = self.plugin.execute(context)

        print(f"验证结果: {result['validation_passed']}")
        print(f"违规数量: {len(result['violations'])}")
        for idx, violation in enumerate(result['violations'], 1):
            print(f"  [{idx}] {violation['message']}")

        self.assertFalse(result['validation_passed'])
        self.assertEqual(len(result['violations']), 1)

        # 验证违规字段是 I2C.2.speed
        self.assertEqual(result['violations'][0]['field'], 'I2C.2.speed')
        self.assertEqual(result['violations'][0]['value'], '400K')

    def test_i2c_addr_violation(self):
        """测试：I2C 地址冲突（地址范围约束）"""
        print("\n" + "=" * 70)
        print("测试：I2C 地址约束违规")
        print("=" * 70)

        sections = [
            {"name": "opSch", "fields": {"powerLevel": "5"}},
            {"name": "I2C", "fields": {"speed": "100K", "addr": "0x10"}},  # I2C.0 ✓
            {"name": "I2C", "fields": {"speed": "400K", "addr": "0x10"}},  # I2C.1 ✗ 应该用0x40-0x60
            {"name": "I2C", "fields": {"speed": "100K", "addr": "0x70"}},  # I2C.2 ✓
        ]

        mock_parser = Mock()
        mock_parser.group_by_top_config.return_value = [
            {
                "top": sections[0],
                "subs": sections[1:]
            }
        ]

        context = {
            "config_parser": {
                "sections": sections,
                "parser": mock_parser
            }
        }

        result = self.plugin.execute(context)

        print(f"验证结果: {result['validation_passed']}")
        print(f"违规数量: {len(result['violations'])}")
        for idx, violation in enumerate(result['violations'], 1):
            print(f"  [{idx}] {violation['message']}")

        self.assertFalse(result['validation_passed'])
        self.assertGreater(len(result['violations']), 0)

        # 验证违规字段是 I2C.1.addr
        violation_fields = [v['field'] for v in result['violations']]
        self.assertIn('I2C.1.addr', violation_fields)

    def test_real_world_scenario(self):
        """测试：真实场景 - 3个I2C总线，每个有不同的限制"""
        print("\n" + "=" * 70)
        print("真实场景：3个I2C总线配置")
        print("=" * 70)
        print("说明：")
        print("  - I2C.0: 低速总线（传感器）- 100K/400K, 地址0x10-0x30")
        print("  - I2C.1: 高速总线（显示器）- 支持1M, 地址0x40-0x60")
        print("  - I2C.2: 超低速总线（EEPROM）- 仅100K, 地址0x70-0x80")
        print("=" * 70)

        sections = [
            {"name": "opSch", "fields": {"powerLevel": "10"}},
            {"name": "I2C", "fields": {"speed": "400K", "addr": "0x10"}},  # 传感器
            {"name": "I2C", "fields": {"speed": "1M", "addr": "0x50"}},    # 显示器
            {"name": "I2C", "fields": {"speed": "100K", "addr": "0x80"}},  # EEPROM
            {"name": "SPI", "fields": {"mode": "master"}},
        ]

        mock_parser = Mock()
        mock_parser.group_by_top_config.return_value = [
            {
                "top": sections[0],
                "subs": sections[1:]
            }
        ]

        context = {
            "config_parser": {
                "sections": sections,
                "parser": mock_parser
            }
        }

        result = self.plugin.execute(context)

        print(f"\n验证结果: {result['validation_passed']}")
        print(f"违规数量: {len(result['violations'])}")

        if result['validation_passed']:
            print("✅ 所有I2C总线配置都符合约束")
        else:
            for idx, violation in enumerate(result['violations'], 1):
                print(f"  [{idx}] {violation['message']}")

        self.assertTrue(result['validation_passed'])


if __name__ == "__main__":
    unittest.main()
