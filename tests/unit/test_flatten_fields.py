#!/usr/bin/env python3
"""
测试字段扁平化功能（所有字段都带前缀）
"""

import os
import sys
import unittest

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.plugins.constraint_checker.plugin import ConstraintCheckerPlugin


class TestFlattenFields(unittest.TestCase):
    """测试扁平化字段功能"""

    def setUp(self):
        self.plugin = ConstraintCheckerPlugin()

    def test_flatten_top_fields(self):
        """测试 top 字段扁平化（带前缀）"""
        group = {
            "top": {
                "name": "opSch",
                "fields": {"powerLevel": "5", "voltage": "0.8V"},
            },
            "subs": [],
        }

        flat_fields = self.plugin._flatten_group_fields(group)

        # top 字段也应该带前缀
        self.assertEqual(flat_fields["opSch.powerLevel"], "5")
        self.assertEqual(flat_fields["opSch.voltage"], "0.8V")
        self.assertEqual(len(flat_fields), 2)

    def test_flatten_sub_fields(self):
        """测试子表字段扁平化（带前缀）"""
        group = {
            "top": {
                "name": "opSch",
                "fields": {"powerLevel": "5"},
            },
            "subs": [
                {"name": "subTable1", "fields": {"mode": "A", "speed": "100"}},
                {"name": "subTable2", "fields": {"mode": "X", "delay": "50"}},
            ],
        }

        flat_fields = self.plugin._flatten_group_fields(group)

        # 验证 top 字段
        self.assertEqual(flat_fields["opSch.powerLevel"], "5")

        # 验证子表字段（都带前缀）
        self.assertEqual(flat_fields["subTable1.mode"], "A")
        self.assertEqual(flat_fields["subTable1.speed"], "100")
        self.assertEqual(flat_fields["subTable2.mode"], "X")
        self.assertEqual(flat_fields["subTable2.delay"], "50")

        # 总共5个字段
        self.assertEqual(len(flat_fields), 5)

    def test_flatten_same_field_name_different_tables(self):
        """测试不同子表有相同字段名的情况"""
        group = {
            "top": {
                "name": "opSch",
                "fields": {"mode": "top_mode"},
            },
            "subs": [
                {"name": "I2C_0", "fields": {"mode": "fast", "address": "0x10"}},
                {"name": "I2C_1", "fields": {"mode": "slow", "address": "0x20"}},
                {"name": "SPI", "fields": {"mode": "master"}},
            ],
        }

        flat_fields = self.plugin._flatten_group_fields(group)

        # 所有 mode 字段都能区分
        self.assertEqual(flat_fields["opSch.mode"], "top_mode")
        self.assertEqual(flat_fields["I2C_0.mode"], "fast")
        self.assertEqual(flat_fields["I2C_1.mode"], "slow")
        self.assertEqual(flat_fields["SPI.mode"], "master")

        # 其他字段
        self.assertEqual(flat_fields["I2C_0.address"], "0x10")
        self.assertEqual(flat_fields["I2C_1.address"], "0x20")

        # 总共6个字段（1个top + 5个sub）
        self.assertEqual(len(flat_fields), 6)


if __name__ == "__main__":
    unittest.main()
