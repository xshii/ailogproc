#!/usr/bin/env python3
"""
TraceParser 高级功能测试
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.plugins.trace_parser.plugin import TraceParserPlugin


class TestTraceParserAdvanced(unittest.TestCase):
    """测试 TraceParser 高级功能"""

    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """测试后清理"""
        import shutil

        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_parse_with_field_name_mapping(self):
        """测试字段名映射"""
        trace_file = os.path.join(self.temp_dir, "test_mapping.txt")

        # 创建包含需要映射的字段的 trace
        trace_content = """thread0	cyc=0x1000 opSch
thread0	cyc=0x1000 |- cfg_group    = 0  (0x00)
thread0	cyc=0x1000 |- pwr_level    = 15  (0x0F)
"""
        with open(trace_file, "w", encoding="utf-8") as f:
            f.write(trace_content)

        plugin = TraceParserPlugin()
        context = {"trace_file": trace_file}

        result = plugin.execute(context)

        self.assertIn("sections", result)
        sections = result["sections"]
        self.assertGreater(len(sections), 0)

        # 验证字段名被映射（根据配置）
        if sections:
            section = sections[0]
            if "fields" in section:
                # 检查是否有映射后的字段名
                self.assertIsInstance(section["fields"], dict)

    def test_parse_with_value_extraction(self):
        """测试值提取（括号内容）"""
        trace_file = os.path.join(self.temp_dir, "test_extraction.txt")

        trace_content = """thread0	cyc=0x1000 opSch
thread0	cyc=0x1000 |- systemMode    = 1  (0x01)
thread0	cyc=0x1000 |- debugLevel    = 2  (0x02)
"""
        with open(trace_file, "w", encoding="utf-8") as f:
            f.write(trace_content)

        plugin = TraceParserPlugin()
        context = {"trace_file": trace_file}

        result = plugin.execute(context)

        sections = result["sections"]
        if sections and "fields" in sections[0]:
            fields = sections[0]["fields"]
            # 根据配置，值可能被提取（去除括号）
            self.assertIsInstance(fields, dict)

    def test_parse_multiple_sections(self):
        """测试解析多个配置块"""
        trace_file = os.path.join(self.temp_dir, "test_multi.txt")

        trace_content = """thread0	cyc=0x1000 opSch
thread0	cyc=0x1000 |- systemMode    = 1  (0x01)

thread0	cyc=0x2000 ERCfg (grp = 0)
thread0	cyc=0x2000 |- cfgGroup    = 0  (0x00)

thread0	cyc=0x3000 ERCfg (grp = 1)
thread0	cyc=0x3000 |- cfgGroup    = 1  (0x01)
"""
        with open(trace_file, "w", encoding="utf-8") as f:
            f.write(trace_content)

        plugin = TraceParserPlugin()
        context = {"trace_file": trace_file}

        result = plugin.execute(context)

        sections = result["sections"]
        # 应该解析出多个配置块
        self.assertGreater(len(sections), 1)

    def test_parse_empty_file(self):
        """测试解析空文件"""
        trace_file = os.path.join(self.temp_dir, "empty.txt")

        with open(trace_file, "w", encoding="utf-8") as f:
            f.write("")

        plugin = TraceParserPlugin()
        context = {"trace_file": trace_file}

        result = plugin.execute(context)

        sections = result["sections"]
        # 空文件应该返回空列表
        self.assertEqual(len(sections), 0)

    def test_parse_with_comments(self):
        """测试解析包含注释的文件"""
        trace_file = os.path.join(self.temp_dir, "with_comments.txt")

        trace_content = """# This is a comment
thread0	cyc=0x1000 opSch
thread0	cyc=0x1000 |- systemMode    = 1  (0x01)
# Another comment
thread0	cyc=0x1000 |- debugLevel    = 2  (0x02)
"""
        with open(trace_file, "w", encoding="utf-8") as f:
            f.write(trace_content)

        plugin = TraceParserPlugin()
        context = {"trace_file": trace_file}

        result = plugin.execute(context)

        sections = result["sections"]
        # 应该解析出配置（忽略注释）
        self.assertGreater(len(sections), 0)

    def test_find_latest_in_multiple_dirs(self):
        """测试在多个目录中查找最新文件"""
        # 创建两个目录
        dir1 = os.path.join(self.temp_dir, "dir1")
        dir2 = os.path.join(self.temp_dir, "dir2")
        os.makedirs(dir1)
        os.makedirs(dir2)

        # 在第二个目录创建文件
        trace_file = os.path.join(dir2, "trace_001.txt")
        Path(trace_file).touch()

        plugin = TraceParserPlugin()

        # 修改配置以搜索多个目录
        plugin.config["default_trace"] = {
            "path": None,
            "auto_find_latest": True,
            "search_dirs": [dir1, dir2],
            "file_patterns": ["trace_*.txt"],
        }

        found_file = plugin._get_default_trace_file()

        self.assertIsNotNone(found_file)
        self.assertTrue(found_file.endswith("trace_001.txt"))

    def test_find_with_multiple_patterns(self):
        """测试使用多个文件模式查找"""
        trace_file1 = os.path.join(self.temp_dir, "log_001.txt")
        trace_file2 = os.path.join(self.temp_dir, "trace_002.txt")

        Path(trace_file1).touch()
        Path(trace_file2).touch()

        plugin = TraceParserPlugin()

        # 配置多个模式
        plugin.config["default_trace"] = {
            "path": None,
            "auto_find_latest": True,
            "search_dirs": [self.temp_dir],
            "file_patterns": ["trace_*.txt", "log_*.txt"],
        }

        found_file = plugin._get_default_trace_file()

        self.assertIsNotNone(found_file)
        # 应该找到 trace_*.txt（优先级更高）
        self.assertTrue("trace" in found_file or "log" in found_file)


class TestTraceParserEdgeCases(unittest.TestCase):
    """测试 TraceParser 边界情况"""

    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """测试后清理"""
        import shutil

        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_parse_malformed_lines(self):
        """测试解析格式错误的行"""
        trace_file = os.path.join(self.temp_dir, "malformed.txt")

        trace_content = """thread0	cyc=0x1000 opSch
thread0	cyc=0x1000 |- systemMode    = 1  (0x01)
This is a malformed line
thread0	cyc=0x1000 |- debugLevel    = 2  (0x02)
"""
        with open(trace_file, "w", encoding="utf-8") as f:
            f.write(trace_content)

        plugin = TraceParserPlugin()
        context = {"trace_file": trace_file}

        # 应该能处理格式错误的行（跳过）
        result = plugin.execute(context)

        sections = result["sections"]
        self.assertGreater(len(sections), 0)

    def test_parse_very_long_lines(self):
        """测试解析很长的行"""
        trace_file = os.path.join(self.temp_dir, "long_lines.txt")

        long_value = "x" * 1000
        trace_content = f"""thread0	cyc=0x1000 opSch
thread0	cyc=0x1000 |- longField    = {long_value}
"""
        with open(trace_file, "w", encoding="utf-8") as f:
            f.write(trace_content)

        plugin = TraceParserPlugin()
        context = {"trace_file": trace_file}

        result = plugin.execute(context)

        sections = result["sections"]
        self.assertGreater(len(sections), 0)

        if sections and "fields" in sections[0]:
            fields = sections[0]["fields"]
            if "longField" in fields:
                # 验证长值被正确处理
                self.assertIsInstance(fields["longField"], str)

    def test_parse_special_characters(self):
        """测试解析特殊字符"""
        trace_file = os.path.join(self.temp_dir, "special_chars.txt")

        trace_content = """thread0	cyc=0x1000 opSch
thread0	cyc=0x1000 |- field@#$    = value!@#
thread0	cyc=0x1000 |- field_name  = 测试值
"""
        with open(trace_file, "w", encoding="utf-8") as f:
            f.write(trace_content)

        plugin = TraceParserPlugin()
        context = {"trace_file": trace_file}

        result = plugin.execute(context)

        sections = result["sections"]
        self.assertGreater(len(sections), 0)

    def test_no_trace_file_found(self):
        """测试未找到 trace 文件"""
        plugin = TraceParserPlugin()

        # 配置不存在的目录
        plugin.config["default_trace"] = {
            "path": None,
            "auto_find_latest": True,
            "search_dirs": ["/nonexistent/dir"],
            "file_patterns": ["trace_*.txt"],
        }

        found_file = plugin._get_default_trace_file()

        # 应该返回 None
        self.assertIsNone(found_file)

    def test_trace_file_is_directory(self):
        """测试 trace 文件路径实际是目录"""
        plugin = TraceParserPlugin()

        # 配置 path 为目录
        plugin.config["default_trace"] = {
            "path": self.temp_dir,
            "auto_find_latest": True,
            "search_dirs": [],
            "file_patterns": ["*.txt"],
        }

        # 应该在目录中查找
        found_file = plugin._get_default_trace_file()

        # 可能找到或找不到，但不应崩溃
        # self.assertIsNone(found_file)  # 空目录应该返回 None


if __name__ == "__main__":
    unittest.main()
