#!/usr/bin/env python3
"""
迁移脚本 - 将 print 语句替换为 logger 调用
"""

import os
import re
from pathlib import Path


def find_print_statements(directory="src/plugins"):
    """查找所有 print 语句"""
    print_files = []

    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".py"):
                filepath = os.path.join(root, file)
                with open(filepath, encoding="utf-8") as f:
                    content = f.read()
                    lines = content.split("\n")

                    matches = []
                    for i, line in enumerate(lines, 1):
                        if re.search(r'\bprint\s*\(', line):
                            matches.append((i, line.strip()))

                    if matches:
                        print_files.append((filepath, matches))

    return print_files


def classify_print_level(line):
    """根据内容推断日志级别"""
    lower_line = line.lower()

    if any(x in lower_line for x in ["✗", "错误", "error", "失败", "fail"]):
        return "error"
    elif any(x in lower_line for x in ["⚠️", "warning", "warn", "警告"]):
        return "warning"
    elif any(x in lower_line for x in ["✓", "成功", "完成", "saved", "done"]):
        return "info"
    else:
        return "info"  # 默认为 info


def replace_print_in_file(filepath):
    """替换文件中的 print 语句"""
    with open(filepath, encoding="utf-8") as f:
        content = f.read()

    # 检查是否已导入 logger
    has_logger_import = "from src.utils.logger import" in content or "from src.utils import" in content

    # 如果没有导入，添加导入
    if not has_logger_import:
        # 找到第一个 import 语句的位置
        lines = content.split("\n")
        import_index = 0
        for i, line in enumerate(lines):
            if line.startswith("import ") or line.startswith("from "):
                import_index = i
                break

        # 在最后一个 import 后插入
        for i in range(import_index, len(lines)):
            if not (lines[i].startswith("import ") or lines[i].startswith("from ") or lines[i].strip() == ""):
                insert_line = i
                break
        else:
            insert_line = import_index + 1

        lines.insert(insert_line, "from src.utils import info, warning, error, debug")
        content = "\n".join(lines)

    # 替换 print 语句
    # 处理多行 print (带f-string或多参数的情况)
    def replace_print(match):
        full_match = match.group(0)
        indent = match.group(1)
        args = match.group(2)

        # 推断日志级别
        level = classify_print_level(full_match)

        return f'{indent}{level}({args})'

    # 匹配 print(...) 语句
    pattern = r'^(\s*)print\s*\((.*?)\)\s*$'
    content = re.sub(pattern, replace_print, content, flags=re.MULTILINE)

    return content


def main():
    """主函数"""
    print("=" * 60)
    print("查找所有 print 语句...")
    print("=" * 60)

    print_files = find_print_statements()

    if not print_files:
        print("✓ 没有找到 print 语句")
        return

    print(f"\n找到 {len(print_files)} 个文件包含 print 语句:\n")

    total_prints = 0
    for filepath, matches in print_files:
        print(f"\n{filepath}: ({len(matches)} 个)")
        for line_no, line in matches[:3]:  # 只显示前3个
            print(f"  {line_no}: {line}")
            total_prints += 1
        if len(matches) > 3:
            print(f"  ... 还有 {len(matches) - 3} 个")

    print(f"\n总计: {total_prints} 个 print 语句")

    # 询问是否替换
    print("\n" + "=" * 60)
    response = input("是否自动替换? (y/N): ")

    if response.lower() == 'y':
        for filepath, _ in print_files:
            try:
                new_content = replace_print_in_file(filepath)
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                print(f"✓ 已更新: {filepath}")
            except Exception as e:
                print(f"✗ 失败: {filepath} - {e}")

        print("\n" + "=" * 60)
        print("✓ 迁移完成!")
        print("=" * 60)
    else:
        print("\n已取消")


if __name__ == "__main__":
    main()
