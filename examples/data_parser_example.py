#!/usr/bin/env python3
"""
data_parser 插件使用示例
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.plugins.data_parser.plugin import DataParserPlugin


def example_1_basic_parsing():
    """示例1: 基本解析"""
    print("=" * 60)
    print("示例1: 基本16进制数据解析")
    print("=" * 60)

    # 模拟配置
    config = {
        "enable": True,
        "source": {"type": "direct", "format": "spaced"},
        "fields": [
            {"name": "header", "offset": 0, "length": 1, "type": "uint8"},
            {"name": "length", "offset": 1, "length": 2, "type": "uint16", "endian": "big"},
            {"name": "cmd", "offset": 3, "length": 1, "type": "uint8"},
            {"name": "data", "offset": 4, "length": 4, "type": "hex"},
        ],
        "value_mapping": {
            "cmd": {0x01: "READ", 0x02: "WRITE", 0x03: "STATUS"}
        },
        "validation": {"verify_checksum": False, "verify_header": False},
        "output": {"format": "json", "include_raw": True, "json_path": "output/example1.json"},
    }

    # 创建插件（使用mock的config）
    plugin = DataParserPlugin.__new__(DataParserPlugin)
    plugin.config = config
    plugin.enabled = True

    # 准备数据
    context = {
        "hex_data": [
            "AA 00 05 01 1A 2B 3C 4D",  # READ命令
            "AB 00 08 02 FF EE DD CC",  # WRITE命令
            "AC 00 03 03 11 22 33 44",  # STATUS命令
        ]
    }

    # 执行解析
    result = plugin.execute(context)

    # 显示结果
    print(f"\n解析结果: {len(result['parsed_data'])}/{len(result['raw_data'])} 条成功\n")
    for item in result["parsed_data"]:
        print(f"索引 {item['index']}:")
        print(f"  Header: 0x{item['header']:02X}")
        print(f"  Length: {item['length']}")
        print(f"  Command: 0x{item['cmd']:02X} ({item.get('cmd_name', 'UNKNOWN')})")
        print(f"  Data: {item['data']}")
        print()


def example_2_protocol_parsing():
    """示例2: 模拟串口协议解析"""
    print("=" * 60)
    print("示例2: 串口通信协议解析")
    print("=" * 60)
    print("协议格式: [起始符(1B)] [地址(1B)] [命令(1B)] [数据(8B)] [校验和(1B)]")
    print()

    config = {
        "enable": True,
        "source": {"type": "direct", "format": "spaced"},
        "fields": [
            {"name": "start", "offset": 0, "length": 1, "type": "uint8"},
            {"name": "addr", "offset": 1, "length": 1, "type": "uint8"},
            {"name": "cmd", "offset": 2, "length": 1, "type": "uint8"},
            {"name": "data", "offset": 3, "length": 8, "type": "hex"},
            {"name": "checksum", "offset": 11, "length": 1, "type": "uint8"},
        ],
        "value_mapping": {
            "cmd": {
                0x10: "QUERY_STATUS",
                0x20: "SET_CONFIG",
                0x30: "READ_DATA",
                0x40: "WRITE_DATA",
            }
        },
        "validation": {"verify_checksum": False, "verify_header": True, "expected_header": 0xAA},
        "output": {"format": "json", "include_raw": True, "json_path": "output/example2.json"},
    }

    plugin = DataParserPlugin.__new__(DataParserPlugin)
    plugin.config = config
    plugin.enabled = True

    # 串口数据包
    context = {
        "hex_data": [
            "AA 01 10 00 00 00 00 00 00 00 00 BB",  # 查询状态
            "AA 02 20 FF FF FF FF 00 00 00 00 CC",  # 设置配置
            "AA 03 30 1A 2B 3C 4D 5E 6F 70 81 DD",  # 读取数据
        ]
    }

    result = plugin.execute(context)

    print(f"解析结果: {len(result['parsed_data'])} 条数据包\n")
    for item in result["parsed_data"]:
        print(f"数据包 #{item['index'] + 1}:")
        print(f"  起始符: 0x{item['start']:02X}")
        print(f"  设备地址: {item['addr']}")
        print(f"  命令: {item.get('cmd_name', f'0x{item['cmd']:02X}')}")
        print(f"  数据: {item['data']}")
        print(f"  校验和: 0x{item['checksum']:02X}")
        print()


def example_3_network_packet():
    """示例3: 网络数据包解析"""
    print("=" * 60)
    print("示例3: 网络数据包解析")
    print("=" * 60)
    print("包格式: [Magic(2B)] [Version(1B)] [Type(1B)] [Length(2B)] [Payload(var)]")
    print()

    config = {
        "enable": True,
        "source": {"type": "direct", "format": "spaced"},
        "fields": [
            {"name": "magic", "offset": 0, "length": 2, "type": "uint16", "endian": "big"},
            {"name": "version", "offset": 2, "length": 1, "type": "uint8"},
            {"name": "packet_type", "offset": 3, "length": 1, "type": "uint8"},
            {"name": "payload_len", "offset": 4, "length": 2, "type": "uint16", "endian": "big"},
            {"name": "payload", "offset": 6, "length": 8, "type": "hex"},
        ],
        "value_mapping": {
            "packet_type": {0x01: "HANDSHAKE", 0x02: "DATA", 0x03: "ACK", 0xFF: "ERROR"}
        },
        "validation": {"verify_checksum": False, "verify_header": False},
        "output": {"format": "json", "include_raw": True, "json_path": "output/example3.json"},
    }

    plugin = DataParserPlugin.__new__(DataParserPlugin)
    plugin.config = config
    plugin.enabled = True

    context = {
        "hex_data": [
            "CA FE 01 01 00 08 48 45 4C 4C 4F 21 21 21",  # HANDSHAKE
            "CA FE 01 02 00 10 01 02 03 04 05 06 07 08",  # DATA
            "CA FE 01 03 00 00 00 00 00 00 00 00 00 00",  # ACK
        ]
    }

    result = plugin.execute(context)

    print(f"解析结果: {len(result['parsed_data'])} 个数据包\n")
    for item in result["parsed_data"]:
        print(f"数据包 #{item['index'] + 1}:")
        print(f"  Magic: 0x{item['magic']:04X}")
        print(f"  Version: {item['version']}")
        print(f"  Type: {item.get('packet_type_name', f'0x{item['packet_type']:02X}')}")
        print(f"  Payload Length: {item['payload_len']}")
        print(f"  Payload: {item['payload']}")
        print()


def example_4_compact_format():
    """示例4: 紧凑格式（无空格）"""
    print("=" * 60)
    print("示例4: 紧凑格式16进制（无空格）")
    print("=" * 60)

    config = {
        "enable": True,
        "source": {"type": "direct", "format": "compact"},
        "fields": [
            {"name": "id", "offset": 0, "length": 2, "type": "uint16", "endian": "big"},
            {"name": "status", "offset": 2, "length": 1, "type": "uint8"},
            {"name": "value", "offset": 3, "length": 4, "type": "uint32", "endian": "big"},
        ],
        "value_mapping": {"status": {0x00: "OK", 0x01: "WARNING", 0xFF: "ERROR"}},
        "validation": {"verify_checksum": False, "verify_header": False},
        "output": {"format": "json", "include_raw": True, "json_path": "output/example4.json"},
    }

    plugin = DataParserPlugin.__new__(DataParserPlugin)
    plugin.config = config
    plugin.enabled = True

    context = {
        "hex_data": [
            "000100000000AB",  # ID=1, OK, value=171
            "0002FF12345678",  # ID=2, ERROR, value=305419896
        ]
    }

    result = plugin.execute(context)

    print(f"解析结果: {len(result['parsed_data'])} 条记录\n")
    for item in result["parsed_data"]:
        print(f"记录 #{item['index'] + 1}:")
        print(f"  ID: {item['id']}")
        print(f"  Status: {item.get('status_name', f'0x{item['status']:02X}')}")
        print(f"  Value: {item['value']}")
        print()


if __name__ == "__main__":
    # 运行所有示例
    example_1_basic_parsing()
    print("\n" * 2)

    example_2_protocol_parsing()
    print("\n" * 2)

    example_3_network_packet()
    print("\n" * 2)

    example_4_compact_format()
