"""
Workflow 集成测试 - 测试完整的插件执行流程
"""

import os
import tempfile
import shutil
from unittest.mock import Mock, patch

import pytest

from src.workflow import process_log_to_excel


class TestWorkflowIntegration:
    """测试完整的 workflow 流程"""

    @pytest.fixture
    def temp_dir(self):
        """创建临时目录"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def sample_trace_file(self, temp_dir):
        """创建示例 trace 文件"""
        trace_content = """thread0	cyc=0x1000 opSch
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
"""
        trace_file = os.path.join(temp_dir, "test_trace.txt")
        with open(trace_file, "w", encoding="utf-8") as f:
            f.write(trace_content)
        return trace_file

    @pytest.fixture
    def template_file(self):
        """使用现有的模板文件"""
        template_path = "templates/template_a_column.xlsx"
        if not os.path.exists(template_path):
            # 如果 templates 目录没有，使用 examples 的
            template_path = "examples/templates/template_a_column.xlsx"
        return template_path

    @pytest.fixture
    def mock_api_response(self):
        """Mock API 响应数据"""
        return {
            "version": "v1.0.0",
            "download_url": "https://example.com/template.xlsx",
            "hash": "abc123def456",
        }

    def test_workflow_with_mocked_api(
        self, temp_dir, sample_trace_file, template_file, mock_api_response
    ):
        """测试完整 workflow - mock API 下载"""
        # 准备输出文件路径
        output_file = os.path.join(temp_dir, "output.xlsx")

        # Mock requests.get 来模拟 API 调用
        with patch("requests.get") as mock_get:
            # 设置 API metadata 响应
            mock_metadata_response = Mock()
            mock_metadata_response.json.return_value = mock_api_response
            mock_metadata_response.raise_for_status = Mock()

            # 设置文件下载响应（返回实际模板内容）
            mock_file_response = Mock()
            with open(template_file, "rb") as f:
                template_content = f.read()
            mock_file_response.content = template_content
            mock_file_response.raise_for_status = Mock()

            # 配置 mock: 第一次调用返回 metadata，第二次返回文件
            mock_get.side_effect = [mock_metadata_response, mock_file_response]

            # 执行 workflow
            result_file = process_log_to_excel(
                excel_file=template_file,
                trace_file=sample_trace_file,
                output_file=output_file,
            )

            # 验证结果
            assert result_file is not None
            assert os.path.exists(result_file)
            assert result_file.endswith(".xlsx")

            print(f"\n✓ 测试通过！输出文件: {result_file}")

    def test_workflow_without_api_download(
        self, temp_dir, sample_trace_file, template_file
    ):
        """测试 workflow - 不使用 API 下载（使用本地模板）"""
        output_file = os.path.join(temp_dir, "output_local.xlsx")

        # 执行 workflow（dld_configtmp 默认 download_enabled=false）
        result_file = process_log_to_excel(
            excel_file=template_file,
            trace_file=sample_trace_file,
            output_file=output_file,
        )

        # 验证结果
        assert result_file is not None
        assert os.path.exists(result_file)

        print(f"\n✓ 测试通过！输出文件: {result_file}")

    def test_workflow_with_default_trace_file(self, temp_dir, template_file):
        """测试 workflow - 使用默认 trace 文件配置"""
        # 在 logs 目录创建 trace 文件
        logs_dir = "logs"
        os.makedirs(logs_dir, exist_ok=True)

        trace_content = """thread0	cyc=0x1000 opSch
thread0	cyc=0x1000 |- systemMode    = 1  (0x01)
thread0	cyc=0x1000 |- debugLevel    = 2  (0x02)
"""
        trace_file = os.path.join(logs_dir, "logs_test.txt")
        with open(trace_file, "w", encoding="utf-8") as f:
            f.write(trace_content)

        try:
            output_file = os.path.join(temp_dir, "output_default.xlsx")

            # 不传入 trace_file，让插件从配置中查找
            # 注意：需要先修改配置启用默认 trace
            result_file = process_log_to_excel(
                excel_file=template_file,
                trace_file=trace_file,  # 暂时还是传入，因为配置默认 path=null
                output_file=output_file,
            )

            assert result_file is not None
            assert os.path.exists(result_file)

            print(f"\n✓ 测试通过！输出文件: {result_file}")

        finally:
            # 清理测试文件
            if os.path.exists(trace_file):
                os.remove(trace_file)

    def test_trace_parser_extracts_sections(self, sample_trace_file, template_file):
        """测试 trace_parser 是否正确提取配置块"""
        # 执行 workflow
        result_file = process_log_to_excel(
            excel_file=template_file,
            trace_file=sample_trace_file,
        )

        # 验证文件生成
        assert result_file is not None
        assert os.path.exists(result_file)

        # TODO: 可以进一步验证 Excel 内容是否正确
        print("\n✓ Trace 解析测试通过！")


class TestDldTmpPluginMocking:
    """专门测试 dld_configtmp 插件的 API 调用"""

    def test_api_download_with_full_mock(self):
        """测试完整的 API 下载流程 mock"""
        from src.plugins.dld_configtmp import DownloadTemplatePlugin

        # Mock 配置
        mock_config = {
            "enable": True,
            "download_enabled": True,
            "storage": {
                "templates_dir": "templates",
                "backup_dir": "templates/backups",
                "manifest_file": "templates/manifest.json",
            },
            "api": {
                "url": "https://api.example.com/templates/latest",
                "timeout": 30,
                "headers": {"User-Agent": "test"},
            },
            "version": {
                "check_updates": True,
                "max_backups": 5,
            },
            "validation": {
                "verify_hash": False,  # 测试时关闭 hash 验证
                "verify_format": True,
            },
        }

        # Mock API 响应
        mock_api_response = {
            "version": "v2.0.0",
            "download_url": "https://example.com/template_v2.xlsx",
            "hash": "test_hash_123",
        }

        with patch("requests.get") as mock_get:
            # 准备 mock 响应
            mock_metadata_resp = Mock()
            mock_metadata_resp.json.return_value = mock_api_response
            mock_metadata_resp.raise_for_status = Mock()

            mock_file_resp = Mock()
            mock_file_resp.content = b"fake_excel_content"
            mock_file_resp.raise_for_status = Mock()

            mock_get.side_effect = [mock_metadata_resp, mock_file_resp]

            # 创建插件实例（需要 mock config）
            with patch.object(
                DownloadTemplatePlugin, "_load_config", return_value=mock_config
            ):
                plugin = DownloadTemplatePlugin()

                # 执行插件
                context = {}
                result = plugin.execute(context)

                # 验证结果
                assert result is not None
                assert "template_path" in result
                assert "version" in result
                assert result["version"] == "v2.0.0"

                print("\n✓ API Mock 测试通过！")
                print(f"  模板路径: {result['template_path']}")
                print(f"  版本: {result['version']}")
                print(f"  是否下载: {result['downloaded']}")


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "-s"])
