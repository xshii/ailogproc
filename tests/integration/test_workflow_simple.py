#!/usr/bin/env python3
"""
简单的 Workflow 集成测试 - 使用 unittest
"""

import os
import sys
import tempfile
import shutil
import unittest
from unittest.mock import Mock, patch
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.workflow import process_log_to_excel


class TestWorkflowIntegration(unittest.TestCase):
    """测试完整的 workflow 流程"""

    def setUp(self):
        """测试前准备"""
        # 创建临时目录
        self.temp_dir = tempfile.mkdtemp()

        # 创建示例 trace 文件
        self.trace_content = """thread0	cyc=0x1000 opSch
thread0	cyc=0x1000 |- systemMode    = 1  (0x01)
thread0	cyc=0x1000 |- debugLevel    = 2  (0x02)

thread0	cyc=0x2000 ERCfg (grp = 0)
thread0	cyc=0x2000 |- cfgGroup    = 0  (0x00)
thread0	cyc=0x2000 |- powerLevel  = 15  (0x0F)

thread0	cyc=0x3000 TXCfg (grp = 0)
thread0	cyc=0x3000 |- cfgGroup    = 0  (0x00)
thread0	cyc=0x3000 |- txPower     = 30  (0x1E)

thread0	cyc=0x4000 ERCfg2 (grp = 1)
thread0	cyc=0x4000 |- cfgGroup    = 1  (0x01)
thread0	cyc=0x4000 |- powerLevel  = 20  (0x14)

thread0	cyc=0x5aa2 opSch
thread0	cyc=0x5aa2 |- systemMode    = 2  (0x02)
thread0	cyc=0x5aa2 |- debugLevel    = 3  (0x03)
"""
        self.trace_file = os.path.join(self.temp_dir, "test_trace.txt")
        with open(self.trace_file, "w", encoding="utf-8") as f:
            f.write(self.trace_content)

        # 使用现有模板
        self.template_file = "templates/template_a_column.xlsx"
        if not os.path.exists(self.template_file):
            self.template_file = "examples/templates/template_a_column.xlsx"

    def tearDown(self):
        """测试后清理"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_workflow_basic(self):
        """测试基本 workflow 执行"""
        print("\n" + "=" * 60)
        print("测试 1: 基本 Workflow 执行")
        print("=" * 60)

        output_file = os.path.join(self.temp_dir, "output.xlsx")

        # 执行 workflow
        result_file = process_log_to_excel(
            excel_file=self.template_file,
            trace_file=self.trace_file,
            output_file=output_file,
        )

        # 验证结果（注意：auto_filename 可能会修改文件名）
        self.assertIsNotNone(result_file, "应该返回输出文件路径")
        self.assertTrue(os.path.exists(result_file), f"输出文件应该存在: {result_file}")
        self.assertTrue(result_file.endswith(".xlsx"), "输出文件应该是 .xlsx 格式")

        # 验证文件在正确的目录
        self.assertEqual(
            os.path.dirname(result_file), self.temp_dir, "文件应该在临时目录"
        )

        print(f"✓ 测试通过！")
        print(f"  原始文件名: {output_file}")
        print(f"  实际文件名: {result_file}")
        print(f"  文件大小: {os.path.getsize(result_file)} bytes")

    def test_workflow_with_mocked_api(self):
        """测试 Workflow - Mock API 下载"""
        print("\n" + "=" * 60)
        print("测试 2: Mock API 下载")
        print("=" * 60)

        output_file = os.path.join(self.temp_dir, "output_api.xlsx")

        # Mock API 响应
        mock_api_response = {
            "version": "v1.0.0",
            "download_url": "https://example.com/template.xlsx",
            "hash": "abc123",
        }

        # 只 mock requests 如果它存在
        try:
            import requests

            with patch("requests.get") as mock_get:
                # 设置 metadata 响应
                mock_metadata_response = Mock()
                mock_metadata_response.json.return_value = mock_api_response
                mock_metadata_response.raise_for_status = Mock()

                # 设置文件下载响应
                mock_file_response = Mock()
                with open(self.template_file, "rb") as f:
                    template_content = f.read()
                mock_file_response.content = template_content
                mock_file_response.raise_for_status = Mock()

                # 配置 mock
                mock_get.side_effect = [mock_metadata_response, mock_file_response]

                # 执行 workflow
                result_file = process_log_to_excel(
                    excel_file=self.template_file,
                    trace_file=self.trace_file,
                    output_file=output_file,
                )

                # 验证结果（auto_filename 可能修改文件名）
                self.assertIsNotNone(result_file)
                self.assertTrue(
                    os.path.exists(result_file), f"文件应该存在: {result_file}"
                )

                print(f"✓ API Mock 测试通过！")
                print(f"  API 被调用次数: {mock_get.call_count}")
                print(f"  原始文件名: {output_file}")
                print(f"  实际文件名: {result_file}")

        except ImportError:
            print("⚠️  requests 未安装，跳过 API mock 测试")
            self.skipTest("requests module not available")

    def test_trace_parser_sections(self):
        """测试 Trace Parser 解析配置块"""
        print("\n" + "=" * 60)
        print("测试 3: Trace Parser 配置块解析")
        print("=" * 60)

        from src.plugins.config_parser import ConfigParserPlugin

        # 创建插件实例
        plugin = ConfigParserPlugin()

        # 执行解析
        context = {"trace_file": self.trace_file}
        result = plugin.execute(context)

        # 验证结果
        self.assertIn("sections", result, "应该返回 sections")
        self.assertIn("parser", result, "应该返回 parser 实例")

        sections = result["sections"]
        self.assertGreater(len(sections), 0, "应该解析出至少一个配置块")
        self.assertEqual(len(sections), 5, "应该解析出 5 个配置块")

        print(f"✓ 解析测试通过！")
        print(f"  解析出的配置块数量: {len(sections)}")
        print(f"  配置块名称: {[s['name'] for s in sections]}")

        # 验证配置块内容
        opsch_sections = [s for s in sections if s["name"] == "opSch"]
        self.assertEqual(len(opsch_sections), 2, "应该有 2 个 opSch 配置块")

        # 验证 ERCfg2 配置块
        ercfg2_sections = [s for s in sections if s["name"] == "ERCfg2 (grp = 1)"]
        self.assertEqual(len(ercfg2_sections), 1, "应该有 1 个 ERCfg2 配置块")

        first_opsch = opsch_sections[0]
        self.assertIn("fields", first_opsch, "配置块应该有 fields")
        print(f"  第一个 opSch 字段: {first_opsch['fields']}")

        first_ercfg2 = ercfg2_sections[0]
        print(f"  ERCfg2 字段: {first_ercfg2['fields']}")

    def test_plugin_execution_order(self):
        """测试插件执行顺序"""
        print("\n" + "=" * 60)
        print("测试 4: 插件执行顺序")
        print("=" * 60)

        from src.plugins import load_plugins

        # 加载插件
        plugins, plugin_configs = load_plugins()

        # 验证插件加载
        self.assertGreater(len(plugins), 0, "应该加载至少一个插件")

        # 检查插件按 level 排序
        levels = [p.level for p in plugins]
        sorted_levels = sorted(levels)
        self.assertEqual(levels, sorted_levels, "插件应该按 level 排序")

        print(f"✓ 插件顺序测试通过！")
        print(f"  已加载插件数量: {len(plugins)}")
        for plugin in plugins:
            plugin_key = None
            from src.plugins import PLUGIN_REGISTRY

            for key, cls in PLUGIN_REGISTRY.items():
                if isinstance(plugin, cls):
                    plugin_key = key
                    break
            print(f"  - Level {plugin.level}: {plugin_key}")


def run_tests():
    """运行所有测试"""
    print("\n")
    print("=" * 60)
    print("Workflow 集成测试")
    print("=" * 60)

    # 创建测试套件
    suite = unittest.TestLoader().loadTestsFromTestCase(TestWorkflowIntegration)

    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # 打印总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    print(f"运行测试数: {result.testsRun}")
    print(f"成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失败: {len(result.failures)}")
    print(f"错误: {len(result.errors)}")
    print("=" * 60)

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
