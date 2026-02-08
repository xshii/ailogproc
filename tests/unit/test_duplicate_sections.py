#!/usr/bin/env python3
"""
测试重复子表名的处理
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.plugins.constraint_checker.plugin import ConstraintCheckerPlugin


class TestDuplicateSections(unittest.TestCase):
    """测试重复子表名"""

    def setUp(self):
        self.plugin = ConstraintCheckerPlugin()

    def test_duplicate_section_names(self):
        """测试：多个同名子表（当前实现会覆盖）"""
        group = {
            "top": {
                "name": "opSch",
                "fields": {"powerLevel": "5"},
            },
            "subs": [
                {"name": "I2C", "fields": {"speed": "100K", "addr": "0x10"}},
                {"name": "I2C", "fields": {"speed": "400K", "addr": "0x20"}},
                {"name": "I2C", "fields": {"speed": "1M", "addr": "0x30"}},
                {"name": "SPI", "fields": {"mode": "master"}},
            ],
        }

        flat_fields = self.plugin._flatten_group_fields(group)

        print("\n扁平化结果：")
        for key, value in sorted(flat_fields.items()):
            print(f"  {key}: {value}")

        # 验证：应该有3个 I2C 的字段，使用索引区分
        self.assertEqual(flat_fields["I2C.0.speed"], "100K")
        self.assertEqual(flat_fields["I2C.0.addr"], "0x10")
        self.assertEqual(flat_fields["I2C.1.speed"], "400K")
        self.assertEqual(flat_fields["I2C.1.addr"], "0x20")
        self.assertEqual(flat_fields["I2C.2.speed"], "1M")
        self.assertEqual(flat_fields["I2C.2.addr"], "0x30")

        # 单个 SPI 不添加索引
        self.assertEqual(flat_fields["SPI.mode"], "master")

        print("\n✅ 修复成功：3个 I2C 配置块都保留了，使用索引区分")

    def test_single_section_no_index(self):
        """测试：单个子表不添加索引"""
        group = {
            "top": {"name": "opSch", "fields": {"powerLevel": "5"}},
            "subs": [
                {"name": "SPI", "fields": {"mode": "master"}},
            ],
        }

        flat_fields = self.plugin._flatten_group_fields(group)

        print("\n扁平化结果（单个子表）：")
        for key, value in sorted(flat_fields.items()):
            print(f"  {key}: {value}")

        # 单个 section 不应该有索引
        self.assertEqual(flat_fields["SPI.mode"], "master")
        self.assertNotIn("SPI.0.mode", flat_fields)

        print("✅ 单个子表不添加索引")

    def test_mixed_duplicate_and_single(self):
        """测试：混合场景（有重复的和单个的）"""
        group = {
            "top": {"name": "opSch", "fields": {"powerLevel": "5"}},
            "subs": [
                {"name": "I2C", "fields": {"speed": "100K"}},
                {"name": "I2C", "fields": {"speed": "400K"}},
                {"name": "SPI", "fields": {"mode": "master"}},
                {"name": "UART", "fields": {"baud": "9600"}},
            ],
        }

        flat_fields = self.plugin._flatten_group_fields(group)

        print("\n扁平化结果（混合场景）：")
        for key, value in sorted(flat_fields.items()):
            print(f"  {key}: {value}")

        # 重复的 I2C 有索引
        self.assertEqual(flat_fields["I2C.0.speed"], "100K")
        self.assertEqual(flat_fields["I2C.1.speed"], "400K")

        # 单个的 SPI 和 UART 没有索引
        self.assertEqual(flat_fields["SPI.mode"], "master")
        self.assertEqual(flat_fields["UART.baud"], "9600")

        print("✅ 重复的添加索引，单个的不添加索引")


if __name__ == "__main__":
    unittest.main()
