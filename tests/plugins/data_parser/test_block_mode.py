"""
data_parser 插件 - 块模式（多二进制）测试
"""

import json
import os
import tempfile
from unittest.mock import patch

import pytest

from src.plugins.data_parser.plugin import DataParserPlugin


@pytest.fixture
def block_mode_config():
    """块模式配置"""
    return {
        "enable": True,
        "source": {
            "type": "log_file",
            "block_mode": True,
            "block_markers": {
                "type_marker": "@type:",
                "address_marker": "@address:",
                "size_marker": "@size:",
                "name_marker": "@name:",
            },
            "pattern": "^\\s*([0-9A-Fa-f\\s]+)\\s*$",
            "format": "spaced",
        },
        "fields": [],
        "validation": {},
        "output": {
            "format": "json",
            "export_binary": True,
            "binary_output_dir": "output/binaries",
            "binary_name_template": "{type}_{address}_{timestamp}.bin",
            "generate_manifest": True,
            "manifest_path": "output/manifest.json",
        },
    }


@pytest.fixture
def sample_log_file():
    """创建示例日志文件"""
    content = """
[2024-01-15 10:00:00] System boot

@type: firmware
@address: 0x1000
@name: test_fw
AA BB CC DD
EE FF 00 11

[2024-01-15 10:00:01] Loading config

@type: config
@address: 0x2000
11 22 33 44
55 66 77 88

@type: data
@address: 0x3000
@size: 8
FF EE DD CC
BB AA 99 88
"""

    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".log") as f:
        f.write(content)
        return f.name


@pytest.fixture
def plugin(block_mode_config):
    """创建插件实例"""
    with patch.object(DataParserPlugin, "_load_config", return_value=block_mode_config):
        return DataParserPlugin()


class TestDataParserBlockMode:
    """块模式测试类"""

    def test_extract_data_blocks(self, plugin, sample_log_file):
        """测试提取数据块"""
        try:
            blocks = plugin._extract_data_blocks(sample_log_file)

            assert len(blocks) == 3

            # 第一个块：firmware
            assert blocks[0]["type"] == "firmware"
            assert blocks[0]["address"] == 0x1000
            assert blocks[0]["name"] == "test_fw"
            assert blocks[0]["byte_count"] == 8

            # 第二个块：config
            assert blocks[1]["type"] == "config"
            assert blocks[1]["address"] == 0x2000

            # 第三个块：data
            assert blocks[2]["type"] == "data"
            assert blocks[2]["address"] == 0x3000
        finally:
            os.unlink(sample_log_file)

    def test_export_binaries(self, plugin, sample_log_file):
        """测试导出二进制文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            plugin.config["output"]["binary_output_dir"] = tmpdir

            try:
                blocks = plugin._extract_data_blocks(sample_log_file)
                timestamp = "20240115120000"
                binary_files = plugin._export_binaries(blocks, timestamp)

                assert len(binary_files) == 3

                # 验证文件存在
                for file_path in binary_files:
                    assert os.path.exists(file_path)
                    # 验证文件名包含时间戳
                    assert timestamp in os.path.basename(file_path)

                # 验证第一个文件内容
                with open(binary_files[0], "rb") as f:
                    content = f.read()
                    assert content == bytes([0xAA, 0xBB, 0xCC, 0xDD, 0xEE, 0xFF, 0x00, 0x11])

            finally:
                os.unlink(sample_log_file)

    def test_generate_manifest(self, plugin, sample_log_file):
        """测试生成manifest"""
        with tempfile.TemporaryDirectory() as tmpdir:
            plugin.config["output"]["binary_output_dir"] = tmpdir
            plugin.config["output"]["manifest_path"] = os.path.join(tmpdir, "manifest.json")

            try:
                blocks = plugin._extract_data_blocks(sample_log_file)
                timestamp = "20240115120000"
                binary_files = plugin._export_binaries(blocks, timestamp)
                manifest_path = plugin._generate_manifest(blocks, binary_files, timestamp)

                assert manifest_path is not None
                assert os.path.exists(manifest_path)

                # 验证manifest内容
                with open(manifest_path, encoding="utf-8") as f:
                    manifest = json.load(f)

                    assert manifest["total_blocks"] == 3
                    assert manifest["timestamp"] == timestamp
                    assert len(manifest["blocks"]) == 3

                    # 验证第一个块信息
                    block0 = manifest["blocks"][0]
                    assert block0["type"] == "firmware"
                    assert block0["address"] == "0x00001000"
                    assert block0["name"] == "test_fw"
                    assert block0["size"] == 8

            finally:
                os.unlink(sample_log_file)

    def test_execute_block_mode(self, plugin, sample_log_file):
        """测试完整的块模式执行"""
        with tempfile.TemporaryDirectory() as tmpdir:
            plugin.config["output"]["binary_output_dir"] = tmpdir
            plugin.config["output"]["manifest_path"] = os.path.join(tmpdir, "manifest.json")

            try:
                context = {"trace_file": sample_log_file}
                result = plugin.execute(context)

                assert len(result["data_blocks"]) == 3
                assert len(result["binary_files"]) == 3
                assert result["manifest_path"] is not None
                assert "timestamp" in result

                # 验证文件名包含时间戳
                for file_path in result["binary_files"]:
                    assert result["timestamp"] in os.path.basename(file_path)

                # 验证manifest
                with open(result["manifest_path"], encoding="utf-8") as f:
                    manifest = json.load(f)
                    assert manifest["total_blocks"] == 3
                    assert manifest["timestamp"] == result["timestamp"]

            finally:
                os.unlink(sample_log_file)

    def test_empty_log_file(self, plugin):
        """测试空日志文件"""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("No data here\n")
            log_file = f.name

        try:
            blocks = plugin._extract_data_blocks(log_file)
            assert len(blocks) == 0
        finally:
            os.unlink(log_file)

    def test_incomplete_block(self, plugin):
        """测试不完整的数据块（缺少16进制数据）"""
        content = """
@type: firmware
@address: 0x1000

@type: config
AA BB CC DD
"""

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write(content)
            log_file = f.name

        try:
            blocks = plugin._extract_data_blocks(log_file)
            # 只有config块有数据
            assert len(blocks) == 1
            assert blocks[0]["type"] == "config"
        finally:
            os.unlink(log_file)

    def test_address_formats(self, plugin):
        """测试不同的地址格式"""
        content = """
@type: test1
@address: 0x1000
AA BB

@type: test2
@address: 2000
CC DD
"""

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write(content)
            log_file = f.name

        try:
            blocks = plugin._extract_data_blocks(log_file)
            assert len(blocks) == 2
            assert blocks[0]["address"] == 0x1000
            assert blocks[1]["address"] == 0x2000
        finally:
            os.unlink(log_file)

    def test_large_dataset(self, plugin):
        """测试大数据集"""
        # 生成100个数据块
        content = ""
        for i in range(100):
            content += f"\n@type: block{i}\n"
            content += f"@address: 0x{i*0x1000:04X}\n"
            content += "AA BB CC DD EE FF 00 11\n"

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write(content)
            log_file = f.name

        with tempfile.TemporaryDirectory() as tmpdir:
            plugin.config["output"]["binary_output_dir"] = tmpdir

            try:
                blocks = plugin._extract_data_blocks(log_file)
                assert len(blocks) == 100

                binary_files = plugin._export_binaries(blocks)
                assert len(binary_files) == 100
            finally:
                os.unlink(log_file)

    def test_binary_file_naming(self, plugin):
        """测试二进制文件命名"""
        content = """
@type: my_firmware
@address: 0xABCD
@name: test_binary
11 22 33 44
"""

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write(content)
            log_file = f.name

        with tempfile.TemporaryDirectory() as tmpdir:
            plugin.config["output"]["binary_output_dir"] = tmpdir

            try:
                blocks = plugin._extract_data_blocks(log_file)
                binary_files = plugin._export_binaries(blocks)

                # 文件名应该包含类型和地址
                file_name = os.path.basename(binary_files[0])
                assert "my_firmware" in file_name
                assert "0000ABCD" in file_name
                assert file_name.endswith(".bin")
            finally:
                os.unlink(log_file)

    def test_mixed_valid_invalid_blocks(self, plugin):
        """测试混合有效和无效块"""
        content = """
@type: valid1
@address: 0x1000
AA BB CC DD

Invalid line here

@type: valid2
@address: 0x2000
EE FF 00 11

@type: no_data
@address: 0x3000

@type: valid3
@address: 0x4000
11 22 33 44
"""

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write(content)
            log_file = f.name

        try:
            blocks = plugin._extract_data_blocks(log_file)
            # 只有有数据的块
            assert len(blocks) == 3
            assert blocks[0]["type"] == "valid1"
            assert blocks[1]["type"] == "valid2"
            assert blocks[2]["type"] == "valid3"
        finally:
            os.unlink(log_file)
