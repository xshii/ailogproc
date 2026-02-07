#!/usr/bin/env python3
"""
日志到Excel匹配工具 - 主入口
"""

import sys
from src.workflow import process_log_to_excel
from src.utils import find_latest_log, cleanup_old_logs, validate_log_file


def _print_usage():
    """打印使用说明"""
    print("=" * 60)
    print("日志到Excel匹配工具")
    print("=" * 60)
    print()
    print("用法:")
    print("  python main.py <Excel文件> [选项]")
    print()
    print("参数:")
    print("  Excel文件  - Excel模板文件路径")
    print()
    print("日志文件:")
    print("  自动查找 logs/ 目录下最新的 logs_*.txt 文件")
    print("  日志文件命名格式: logs_20260207_153045.txt")
    print()
    print("可选参数:")
    print("  --output <文件>  - 指定输出文件路径")
    print("  --sheet <名称>   - 指定工作表名称")
    print()
    print("示例:")
    print("  python main.py template.xlsx")
    print("  python main.py template.xlsx --output result.xlsx")
    print("=" * 60)


def _parse_optional_args():
    """解析可选参数"""
    output_file = None
    sheet_name = None

    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == "--output" and i + 1 < len(sys.argv):
            output_file = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == "--sheet" and i + 1 < len(sys.argv):
            sheet_name = sys.argv[i + 1]
            i += 2
        else:
            i += 1

    return output_file, sheet_name


def main():
    """主函数"""
    if len(sys.argv) < 2:
        _print_usage()
        sys.exit(1)

    excel_file = sys.argv[1]
    log_file = find_latest_log()

    if not validate_log_file(log_file):
        sys.exit(1)

    print(f"✓ 使用日志文件: {log_file}")
    cleanup_old_logs(max_keep=5)
    print()

    output_file, sheet_name = _parse_optional_args()
    process_log_to_excel(excel_file, log_file, output_file, sheet_name)


if __name__ == "__main__":
    main()
