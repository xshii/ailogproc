#!/usr/bin/env python3
"""
日志到Excel匹配工具 - 主入口
"""
import sys
from src.workflow import process_log_to_excel


def main():
    if len(sys.argv) < 3:
        print("=" * 60)
        print("日志到Excel匹配工具")
        print("=" * 60)
        print()
        print("用法:")
        print("  python main.py <Excel文件> <日志文件> [选项]")
        print()
        print("参数:")
        print("  Excel文件  - Excel模板文件路径")
        print("  日志文件   - 日志文件路径")
        print()
        print("可选参数:")
        print("  --output <文件>  - 指定输出文件路径")
        print("  --sheet <名称>   - 指定工作表名称")
        print()
        print("示例:")
        print("  python main.py template.xlsx log.txt")
        print("  python main.py template.xlsx log.txt --output result.xlsx")
        print("  python main.py template.xlsx log.txt --sheet 配置表")
        print("=" * 60)
        sys.exit(1)
    
    excel_file = sys.argv[1]
    log_file = sys.argv[2]
    
    # 解析可选参数
    output_file = None
    sheet_name = None
    
    i = 3
    while i < len(sys.argv):
        if sys.argv[i] == '--output' and i + 1 < len(sys.argv):
            output_file = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == '--sheet' and i + 1 < len(sys.argv):
            sheet_name = sys.argv[i + 1]
            i += 2
        else:
            i += 1
    
    # 执行处理
    process_log_to_excel(excel_file, log_file, output_file, sheet_name)


if __name__ == "__main__":
    main()
