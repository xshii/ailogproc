#!/usr/bin/env python3
"""
data_parser 插件 - 多二进制导出示例

演示如何从日志中提取多个16进制数据块并导出为二进制文件
"""

import json
import os
import sys

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.plugins.data_parser.plugin import DataParserPlugin


def run_example():
    """运行示例"""
    print("=" * 70)
    print("16进制数据解析器 - 多二进制导出示例")
    print("=" * 70)

    # 配置
    config = {
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

    # 创建插件
    plugin = DataParserPlugin.__new__(DataParserPlugin)
    plugin.config = config
    plugin.enabled = True

    # 示例日志文件
    log_file = "examples/sample_binary_data.log"

    if not os.path.exists(log_file):
        print(f"\n错误: 找不到示例日志文件: {log_file}")
        print("请确保在项目根目录运行此脚本")
        return

    print(f"\n📁 读取日志文件: {log_file}")
    print("-" * 70)

    # 执行解析
    context = {"trace_file": log_file}
    result = plugin.execute(context)

    # 显示结果
    print("\n✅ 解析完成！")
    print(f"   - 数据块数量: {len(result['data_blocks'])}")
    print(f"   - 二进制文件: {len(result['binary_files'])}")
    print(f"   - Manifest: {result['manifest_path']}")

    # 显示每个数据块详情
    print("\n📦 数据块详情:")
    print("-" * 70)

    for idx, block in enumerate(result["data_blocks"], 1):
        print(f"\n[{idx}] {block['type'].upper()}")
        print(f"    类型: {block['type']}")
        print(f"    地址: 0x{block['address']:08X}" if block['address'] is not None else "    地址: 未指定")
        print(f"    名称: {block.get('name', '未命名')}")
        print(f"    大小: {block['byte_count']} 字节")
        print(f"    文件: {os.path.basename(block.get('binary_file', 'N/A'))}")
        print(f"    行号: {block['start_line']}-{block['end_line']}")

        # 显示前16字节的hex dump
        if block['bytes']:
            hex_preview = " ".join(f"{b:02X}" for b in block['bytes'][:16])
            if len(block['bytes']) > 16:
                hex_preview += " ..."
            print(f"    数据: {hex_preview}")

    # 读取并显示manifest
    if result['manifest_path'] and os.path.exists(result['manifest_path']):
        print("\n📋 Manifest 清单:")
        print("-" * 70)

        with open(result['manifest_path'], encoding="utf-8") as f:
            manifest = json.load(f)

        print(f"版本: {manifest['version']}")
        print(f"生成时间: {manifest['generated_at']}")
        print(f"总块数: {manifest['total_blocks']}")
        print(f"总字节数: {manifest['total_bytes']}")

        print("\n块列表:")
        for block_info in manifest['blocks']:
            print(f"  [{block_info['index']}] {block_info['type']:12} | "
                  f"地址: {block_info['address']:12} | "
                  f"大小: {block_info['size']:4} bytes | "
                  f"文件: {block_info['binary_file']}")

    # 显示生成的文件
    print("\n💾 生成的二进制文件:")
    print("-" * 70)

    for file_path in result['binary_files']:
        file_size = os.path.getsize(file_path)
        print(f"  {os.path.basename(file_path):30} ({file_size:5} bytes)")

    print("\n" + "=" * 70)
    print("✨ 完成！")
    print(f"   所有文件已保存到: {config['output']['binary_output_dir']}/")
    print("=" * 70)


def verify_binaries():
    """验证生成的二进制文件"""
    print("\n\n" + "=" * 70)
    print("🔍 验证二进制文件")
    print("=" * 70)

    binary_dir = "output/binaries"

    if not os.path.exists(binary_dir):
        print(f"错误: 目录不存在: {binary_dir}")
        return

    bin_files = [f for f in os.listdir(binary_dir) if f.endswith('.bin')]

    if not bin_files:
        print("错误: 未找到.bin文件")
        return

    for bin_file in bin_files:
        file_path = os.path.join(binary_dir, bin_file)
        print(f"\n📄 {bin_file}")

        with open(file_path, "rb") as f:
            content = f.read()

        print(f"   大小: {len(content)} 字节")

        # Hex dump (前32字节)
        print("   内容 (Hex):")
        for i in range(0, min(len(content), 32), 16):
            hex_line = " ".join(f"{b:02X}" for b in content[i:i+16])
            ascii_line = "".join(chr(b) if 32 <= b < 127 else '.' for b in content[i:i+16])
            print(f"     {i:04X}: {hex_line:48}  {ascii_line}")

        if len(content) > 32:
            print(f"     ... (还有 {len(content) - 32} 字节)")


if __name__ == "__main__":
    # 运行主示例
    run_example()

    # 验证生成的文件
    verify_binaries()
