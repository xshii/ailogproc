#!/usr/bin/env python3
"""
测试 top_keyword 配置的优先级
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.plugins.constraint_checker.plugin import ConstraintCheckerPlugin


class TestTopKeywordConfig(unittest.TestCase):
    """测试 top 关键字配置的获取"""

    def test_default_top_keyword(self):
        """测试：默认值"""
        plugin = ConstraintCheckerPlugin()

        # 没有任何配置，使用默认值
        top_keyword = plugin._get_top_keyword(context={})

        print(f"\n默认 top_keyword: {top_keyword}")
        self.assertEqual(top_keyword, "opSch")

    def test_from_constraint_checker_config(self):
        """测试：从 constraint_checker 自己的配置获取（优先级最高）"""
        plugin = ConstraintCheckerPlugin()

        # 覆盖配置
        plugin.config["top_keyword"] = "MainConfig"

        context = {
            "excel_writer_config": {
                "top_table": {
                    "log_keyword": "DifferentKeyword"
                }
            }
        }

        top_keyword = plugin._get_top_keyword(context)

        print(f"\nconstraint_checker 配置的 top_keyword: {top_keyword}")
        # 应该使用 constraint_checker 的配置，而非 excel_writer 的
        self.assertEqual(top_keyword, "MainConfig")

    def test_from_excel_writer_config(self):
        """测试：从 excel_writer_config 获取"""
        plugin = ConstraintCheckerPlugin()

        context = {
            "excel_writer_config": {
                "top_table": {
                    "log_keyword": "CustomTop"
                }
            }
        }

        top_keyword = plugin._get_top_keyword(context)

        print(f"\nexcel_writer 配置的 top_keyword: {top_keyword}")
        self.assertEqual(top_keyword, "CustomTop")

    def test_priority_order(self):
        """测试：优先级顺序"""
        plugin = ConstraintCheckerPlugin()

        print("\n测试优先级顺序：")

        # 1. 无配置 → 默认值
        top_keyword = plugin._get_top_keyword(context={})
        print(f"  1. 无配置: {top_keyword}")
        self.assertEqual(top_keyword, "opSch")

        # 2. excel_writer 有配置 → 使用 excel_writer 的
        context = {
            "excel_writer_config": {
                "top_table": {
                    "log_keyword": "ExcelTop"
                }
            }
        }
        top_keyword = plugin._get_top_keyword(context)
        print(f"  2. excel_writer 配置: {top_keyword}")
        self.assertEqual(top_keyword, "ExcelTop")

        # 3. constraint_checker 也有配置 → 使用 constraint_checker 的（优先级更高）
        plugin.config["top_keyword"] = "ConstraintTop"
        top_keyword = plugin._get_top_keyword(context)
        print(f"  3. constraint_checker 配置（优先）: {top_keyword}")
        self.assertEqual(top_keyword, "ConstraintTop")

    def test_missing_excel_writer_config(self):
        """测试：context 中没有 excel_writer_config"""
        plugin = ConstraintCheckerPlugin()

        # context 中没有 excel_writer_config
        context = {
            "some_other_config": {}
        }

        top_keyword = plugin._get_top_keyword(context)

        print(f"\n缺少 excel_writer_config: {top_keyword}")
        # 应该回退到默认值
        self.assertEqual(top_keyword, "opSch")


if __name__ == "__main__":
    unittest.main()
