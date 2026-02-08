"""
data_parser 插件单元测试
"""

import os
import json
import tempfile
import pytest
from unittest.mock import patch
from src.plugins.data_parser.plugin import DataParserPlugin


@pytest.fixture
def basic_config():
    """基本配置"""
    return {
        "enable": True,
        "source": {
            "type": "direct",
            "pattern": "DATA:\\s*([0-9A-Fa-f\\s]+)",
            "format": "spaced",
        },
        "fields": [
            {
                "name": "header",
                "offset": 0,
                "length": 1,
                "type": "uint8",
                "description": "数据包头",
            },
            {
                "name": "length",
                "offset": 1,
                "length": 2,
                "type": "uint16",
                "endian": "big",
                "description": "数据长度",
            },
            {
                "name": "type",
                "offset": 3,
                "length": 1,
                "type": "uint8",
                "description": "数据类型",
            },
        ],
        "value_mapping": {
            "type": {
                0x01: "CONFIG",
                0x02: "STATUS",
                0x03: "DATA",
            }
        },
        "validation": {
            "verify_checksum": False,
            "verify_header": False,
        },
        "output": {
            "format": "json",
            "include_raw": True,
            "json_path": "output/data_parsed.json",
        },
    }


@pytest.fixture
def plugin(basic_config):
    """创建插件实例"""
    with patch.object(DataParserPlugin, "_load_config", return_value=basic_config):
        return DataParserPlugin()


class TestDataParserPlugin:
    """DataParserPlugin 测试类"""

    def test_plugin_initialization(self, basic_config):
        """测试插件初始化"""
        with patch.object(DataParserPlugin, "_load_config", return_value=basic_config):
            plugin = DataParserPlugin()
            assert plugin.enabled is True
            assert plugin.level == 1
            assert plugin.dependencies == []

    def test_hex_to_bytes_spaced(self, plugin):
        """测试解析空格分隔的16进制"""
        hex_str = "1A 02 FF 3C"
        result = plugin._hex_to_bytes(hex_str)
        assert result == [0x1A, 0x02, 0xFF, 0x3C]

    def test_hex_to_bytes_compact(self, plugin):
        """测试解析紧凑格式的16进制"""
        plugin.config["source"]["format"] = "compact"
        hex_str = "1A02FF3C"
        result = plugin._hex_to_bytes(hex_str)
        assert result == [0x1A, 0x02, 0xFF, 0x3C]

    def test_hex_to_bytes_invalid(self, plugin):
        """测试无效的16进制字符串"""
        hex_str = "ZZ 02 FF"
        result = plugin._hex_to_bytes(hex_str)
        assert result is None

    def test_parse_field_uint8(self, plugin):
        """测试解析uint8字段"""
        byte_array = [0xAA, 0x00, 0x05, 0x01]
        field_def = {
            "name": "header",
            "offset": 0,
            "length": 1,
            "type": "uint8",
        }
        result = plugin._parse_field(byte_array, field_def, {})
        assert result == 0xAA

    def test_parse_field_uint16_big_endian(self, plugin):
        """测试解析uint16字段（大端）"""
        byte_array = [0xAA, 0x01, 0x02, 0x03]
        field_def = {
            "name": "length",
            "offset": 1,
            "length": 2,
            "type": "uint16",
            "endian": "big",
        }
        result = plugin._parse_field(byte_array, field_def, {})
        assert result == 0x0102  # (0x01 << 8) | 0x02

    def test_parse_field_uint16_little_endian(self, plugin):
        """测试解析uint16字段（小端）"""
        byte_array = [0xAA, 0x01, 0x02, 0x03]
        field_def = {
            "name": "length",
            "offset": 1,
            "length": 2,
            "type": "uint16",
            "endian": "little",
        }
        result = plugin._parse_field(byte_array, field_def, {})
        assert result == 0x0201  # (0x02 << 8) | 0x01

    def test_parse_field_uint32_big_endian(self, plugin):
        """测试解析uint32字段"""
        byte_array = [0x00, 0x01, 0x02, 0x03, 0x04]
        field_def = {
            "name": "value",
            "offset": 1,
            "length": 4,
            "type": "uint32",
            "endian": "big",
        }
        result = plugin._parse_field(byte_array, field_def, {})
        assert result == 0x01020304

    def test_parse_field_hex(self, plugin):
        """测试解析hex字段"""
        byte_array = [0xAA, 0x1A, 0x2B, 0x3C]
        field_def = {
            "name": "data",
            "offset": 1,
            "length": 3,
            "type": "hex",
        }
        result = plugin._parse_field(byte_array, field_def, {})
        assert result == "1A 2B 3C"

    def test_parse_field_string(self, plugin):
        """测试解析string字段"""
        byte_array = [0xAA, 0x41, 0x42, 0x43, 0x00]  # ABC\0
        field_def = {
            "name": "name",
            "offset": 1,
            "length": 4,
            "type": "string",
        }
        result = plugin._parse_field(byte_array, field_def, {})
        assert result == "ABC"

    def test_parse_field_out_of_bounds(self, plugin):
        """测试字段超出范围"""
        byte_array = [0xAA, 0x01]
        field_def = {
            "name": "data",
            "offset": 1,
            "length": 5,  # 超出
            "type": "hex",
        }
        result = plugin._parse_field(byte_array, field_def, {})
        assert result is None

    def test_calculate_offset_integer(self, plugin):
        """测试整数偏移"""
        result = plugin._calculate_offset(5, [0] * 10)
        assert result == 5

    def test_calculate_offset_end(self, plugin):
        """测试end-N偏移"""
        byte_array = [0] * 10
        result = plugin._calculate_offset("end-1", byte_array)
        assert result == 9

    def test_parse_hex_string_success(self, plugin):
        """测试成功解析完整数据包"""
        hex_str = "AA 00 05 01"
        result = plugin._parse_hex_string(hex_str, 0)

        assert result is not None
        assert result["header"] == 0xAA
        assert result["length"] == 0x0005
        assert result["type"] == 0x01
        assert result["type_name"] == "CONFIG"  # 值映射

    def test_parse_hex_string_invalid_format(self, plugin):
        """测试无效格式"""
        hex_str = "ZZ YY"
        result = plugin._parse_hex_string(hex_str, 0)
        assert result is None

    def test_execute_with_direct_input_single(self, plugin):
        """测试直接输入单条数据"""
        context = {"hex_data": "AA 00 05 01"}
        result = plugin.execute(context)

        assert len(result["parsed_data"]) == 1
        assert result["parsed_data"][0]["header"] == 0xAA
        assert result["raw_data"] == ["AA 00 05 01"]

    def test_execute_with_direct_input_multiple(self, plugin):
        """测试直接输入多条数据"""
        context = {"hex_data": ["AA 00 05 01", "BB 00 03 02"]}
        result = plugin.execute(context)

        assert len(result["parsed_data"]) == 2
        assert result["parsed_data"][0]["header"] == 0xAA
        assert result["parsed_data"][1]["header"] == 0xBB

    def test_execute_with_empty_input(self, plugin):
        """测试空输入"""
        context = {}
        result = plugin.execute(context)

        assert result["parsed_data"] == []
        assert result["raw_data"] == []

    def test_extract_from_log(self, plugin):
        """测试从日志提取"""
        plugin.config["source"]["type"] = "log_file"

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("Some log line\n")
            f.write("DATA: 1A 02 FF 3C\n")
            f.write("Another line\n")
            f.write("DATA: AA BB CC\n")
            log_file = f.name

        try:
            result = plugin._extract_from_log(log_file)
            assert len(result) == 2
            assert result[0] == "1A 02 FF 3C"
            assert result[1] == "AA BB CC"
        finally:
            os.unlink(log_file)

    def test_execute_from_log_file(self, plugin):
        """测试从日志文件执行"""
        plugin.config["source"]["type"] = "log_file"

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("DATA: AA 00 05 01\n")
            f.write("DATA: BB 00 03 02\n")
            log_file = f.name

        try:
            context = {"trace_file": log_file}
            result = plugin.execute(context)

            assert len(result["parsed_data"]) == 2
            assert result["parsed_data"][0]["header"] == 0xAA
        finally:
            os.unlink(log_file)

    def test_generate_report(self, plugin):
        """测试生成JSON报告"""
        parsed_results = [
            {"index": 0, "header": 0xAA, "length": 5, "type": 1},
            {"index": 1, "header": 0xBB, "length": 3, "type": 2},
        ]
        raw_data = ["AA 00 05 01", "BB 00 03 02"]

        with tempfile.TemporaryDirectory() as tmpdir:
            plugin.config["output"]["json_path"] = os.path.join(tmpdir, "report.json")
            path = plugin._generate_report(parsed_results, raw_data)

            assert path is not None
            assert os.path.exists(path)

            # 验证报告内容
            with open(path, "r", encoding="utf-8") as f:
                report = json.load(f)
                assert report["total_count"] == 2
                assert report["parsed_count"] == 2
                assert report["success_rate"] == 1.0
                assert len(report["data"]) == 2

    def test_value_mapping(self, plugin):
        """测试值映射"""
        parsed = {"type": 0x01, "other": 123}
        plugin._apply_value_mapping(parsed)

        assert parsed["type_name"] == "CONFIG"
        assert "other_name" not in parsed  # 没有映射的不处理

    def test_validation_header_success(self, plugin):
        """测试header验证成功"""
        plugin.config["validation"]["verify_header"] = True
        plugin.config["validation"]["expected_header"] = 0xAA

        byte_array = [0xAA, 0x01, 0x02]
        result = plugin._validate(byte_array)
        assert result is True

    def test_validation_header_failure(self, plugin):
        """测试header验证失败"""
        plugin.config["validation"]["verify_header"] = True
        plugin.config["validation"]["expected_header"] = 0xAA

        byte_array = [0xBB, 0x01, 0x02]
        result = plugin._validate(byte_array)
        assert result is False

    def test_large_dataset(self, plugin):
        """测试大数据集"""
        # 生成1000条数据
        hex_data = [f"AA {i:02X} {(i*2):02X} 01" for i in range(1000)]
        context = {"hex_data": hex_data}

        result = plugin.execute(context)
        assert len(result["parsed_data"]) == 1000

    def test_mixed_valid_invalid_data(self, plugin):
        """测试混合有效和无效数据"""
        context = {
            "hex_data": [
                "AA 00 05 01",  # 有效
                "ZZ YY XX",  # 无效
                "BB 00 03 02",  # 有效
            ]
        }
        result = plugin.execute(context)

        # 只有2条有效
        assert len(result["parsed_data"]) == 2
        assert len(result["raw_data"]) == 3

    def test_compact_format(self, plugin):
        """测试紧凑格式"""
        plugin.config["source"]["format"] = "compact"
        context = {"hex_data": "AA000501"}

        result = plugin.execute(context)
        assert len(result["parsed_data"]) == 1
        assert result["parsed_data"][0]["header"] == 0xAA

    def test_edge_case_empty_byte_array(self, plugin):
        """测试空字节数组"""
        hex_str = ""
        result = plugin._parse_hex_string(hex_str, 0)
        assert result is None

    def test_edge_case_single_byte(self, plugin):
        """测试单字节数据"""
        hex_str = "AA"
        result = plugin._parse_hex_string(hex_str, 0)

        # 应该能解析header，但其他字段会失败
        assert result is not None
        assert result["header"] == 0xAA
