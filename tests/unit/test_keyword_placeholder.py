#!/usr/bin/env python3
"""
测试 keyword_mapping 中的占位符功能
"""

import os
import sys
import unittest
from unittest.mock import Mock

sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from src.plugins.excel_writer.plugin import ExcelWriterPlugin


class TestKeywordPlaceholder(unittest.TestCase):
    """测试关键字占位符（x）替换"""

    def setUp(self):
        self.plugin = ExcelWriterPlugin()

        # 模拟配置
        self.plugin.config = {
            "enable": True,
            "keyword_mapping": {
                "IN__x__Cfg": r"InxCfg\d+",  # 占位符关键字（使用 __x__）
                "ExCfg-ER": r"ERCfg\s*\(grp\s*=\s*\d+\)",  # 普通关键字
            },
            "top_table": {"log_keyword": "opSch"},
        }

    def test_find_matching_keyword_with_placeholder(self):
        """测试：占位符关键字匹配"""
        print("\n" + "=" * 70)
        print("测试：占位符关键字匹配")
        print("=" * 70)

        keyword_mapping = self.plugin.config["keyword_mapping"]

        # 测试不同的日志 section name
        test_cases = [
            ("InxCfg0", "IN0Cfg"),  # 第一个索引
            ("InxCfg1", "IN1Cfg"),  # 第二个索引
            ("InxCfg2", "IN2Cfg"),  # 第三个索引
            ("InxCfg5", "IN5Cfg"),  # 跳号索引
        ]

        for log_section, expected_excel_keyword in test_cases:
            result = self.plugin._find_matching_keyword(log_section, keyword_mapping)
            print(
                f"  日志: {log_section:15} → Excel: {result:10} (期望: {expected_excel_keyword})"
            )
            self.assertEqual(result, expected_excel_keyword)

    def test_find_matching_keyword_without_placeholder(self):
        """测试：普通关键字匹配（无占位符）"""
        print("\n" + "=" * 70)
        print("测试：普通关键字匹配")
        print("=" * 70)

        keyword_mapping = self.plugin.config["keyword_mapping"]

        test_cases = [
            ("ERCfg (grp = 0)", "ExCfg-ER"),
            ("ERCfg (grp = 1)", "ExCfg-ER"),
        ]

        for log_section, expected_excel_keyword in test_cases:
            result = self.plugin._find_matching_keyword(log_section, keyword_mapping)
            print(f"  日志: {log_section:20} → Excel: {result}")
            self.assertEqual(result, expected_excel_keyword)

    def test_scan_sub_table_positions_with_placeholder(self):
        """测试：扫描带占位符的子表位置"""
        print("\n" + "=" * 70)
        print("测试：扫描带占位符的子表位置")
        print("=" * 70)

        # Mock processor
        mock_processor = Mock()

        # 模拟 Excel 中有 IN0Cfg, IN1Cfg, IN2Cfg
        def mock_find_sub_table(keyword):
            positions = {
                "IN0Cfg": (10, 15),
                "IN1Cfg": (20, 25),
                "IN2Cfg": (30, 35),
            }
            if keyword in positions:
                return positions[keyword]
            return None, None

        mock_processor.find_sub_table = mock_find_sub_table

        keyword_mapping = {"IN__x__Cfg": r"InxCfg\d+"}

        # 执行扫描
        keyword_info = self.plugin._scan_sub_table_positions(
            mock_processor, keyword_mapping
        )

        print(f"\n扫描结果：")
        for keyword, info in sorted(keyword_info.items()):
            print(
                f"  {keyword}: 行 {info['orig_start']}-{info['orig_end']}, "
                f"模板: {info.get('template', 'N/A')}, "
                f"索引: {info.get('index', 'N/A')}"
            )

        # 验证
        self.assertIn("IN0Cfg", keyword_info)
        self.assertIn("IN1Cfg", keyword_info)
        self.assertIn("IN2Cfg", keyword_info)

        # 验证位置信息
        self.assertEqual(keyword_info["IN0Cfg"]["orig_start"], 10)
        self.assertEqual(keyword_info["IN0Cfg"]["index"], 0)
        self.assertEqual(keyword_info["IN0Cfg"]["template"], "IN__x__Cfg")

        self.assertEqual(keyword_info["IN1Cfg"]["orig_start"], 20)
        self.assertEqual(keyword_info["IN1Cfg"]["index"], 1)

        self.assertEqual(keyword_info["IN2Cfg"]["orig_start"], 30)
        self.assertEqual(keyword_info["IN2Cfg"]["index"], 2)

    def test_complete_workflow(self):
        """测试：完整工作流"""
        print("\n" + "=" * 70)
        print("测试：完整工作流（日志 → Excel 映射）")
        print("=" * 70)

        # Mock processor
        mock_processor = Mock()

        def mock_find_sub_table(keyword):
            positions = {
                "IN0Cfg": (10, 15),
                "IN1Cfg": (20, 25),
                "IN2Cfg": (30, 35),
            }
            return positions.get(keyword, (None, None))

        mock_processor.find_sub_table = mock_find_sub_table

        keyword_mapping = {"IN__x__Cfg": r"InxCfg\d+"}

        # 1. 扫描 Excel 中的子表位置
        keyword_info = self.plugin._scan_sub_table_positions(
            mock_processor, keyword_mapping
        )

        # 2. 模拟日志 sections
        log_sections = [
            {"name": "InxCfg0", "fields": {"mode": "A"}},
            {"name": "InxCfg1", "fields": {"mode": "B"}},
            {"name": "InxCfg2", "fields": {"mode": "C"}},
        ]

        print("\n日志 sections → Excel 关键字映射：")
        for section in log_sections:
            log_name = section["name"]
            excel_keyword = self.plugin._find_matching_keyword(
                log_name, keyword_mapping
            )

            # 验证是否在 keyword_info 中
            if excel_keyword in keyword_info:
                row_range = f"行 {keyword_info[excel_keyword]['orig_start']}-{keyword_info[excel_keyword]['orig_end']}"
                status = "✓"
            else:
                row_range = "未找到"
                status = "✗"

            print(
                f"  {status} 日志: {log_name:10} → Excel: {excel_keyword:10} ({row_range})"
            )

            # 断言
            self.assertIn(excel_keyword, keyword_info)


if __name__ == "__main__":
    unittest.main()
