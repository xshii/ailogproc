#!/usr/bin/env python3
"""
日志到Excel匹配工具 - 主入口
"""

import os
import sys

import yaml

from src.utils import setup_logger, get_logger, info
from src.workflow import process_log_to_excel


def _load_logger_config():
    """加载日志配置"""
    config_file = "src/utils/logger_config.yaml"

    if os.path.exists(config_file):
        with open(config_file, encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}
    else:
        # 使用默认配置
        config = {}

    # 初始化日志器
    setup_logger(
        console_level=config.get("console_level", "INFO"),
        enable_file=config.get("enable_file_logging", False),
        log_file=config.get("log_file"),
        file_level=config.get("file_level", "DEBUG"),
    )

    # 如果配置禁用控制台
    if config.get("console_disabled", False):
        get_logger().disable_console()


def _print_usage():
    """打印使用说明"""
    info("=" * 60)
    info("日志到Excel匹配工具")
    info("=" * 60)
    info("")
    info("用法:")
    info("  python main.py [Excel文件] [选项]")
    info("")
    info("参数:")
    info("  Excel文件  - Excel模板文件路径（可选，默认自动查找）")
    info("")
    info("自动查找规则:")
    info("  Excel模板: templates/*.xlsx → examples/templates/*.xlsx")
    info("  Trace文件: logs/trace_*.txt → logs/*.txt → examples/logs/*.txt")
    info("")
    info("可选参数:")
    info("  --output <文件>  - 指定输出文件路径")
    info("  --sheet <名称>   - 指定工作表名称")
    info("  --log-level <级别> - 设置日志级别 (DEBUG, INFO, WARNING, ERROR)")
    info("")
    info("示例:")
    info("  python main.py                               # 使用默认模板和trace")
    info("  python main.py template.xlsx                 # 指定模板")
    info("  python main.py template.xlsx --output result.xlsx")
    info("  python main.py --log-level DEBUG             # 无模板参数时使用默认")
    info("=" * 60)


def _parse_optional_args():
    """解析可选参数"""
    output_file = None
    sheet_name = None
    log_level = None

    # 确定从哪个位置开始解析选项
    # 如果第一个参数不以 -- 开头，说明它是 Excel 文件，从第二个参数开始
    # 否则从第一个参数开始
    start_index = 2 if len(sys.argv) >= 2 and not sys.argv[1].startswith("--") else 1

    i = start_index
    while i < len(sys.argv):
        if sys.argv[i] == "--output" and i + 1 < len(sys.argv):
            output_file = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == "--sheet" and i + 1 < len(sys.argv):
            sheet_name = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == "--log-level" and i + 1 < len(sys.argv):
            log_level = sys.argv[i + 1]
            i += 2
        else:
            i += 1

    return output_file, sheet_name, log_level


def main():
    """主函数"""
    # 先加载日志配置
    _load_logger_config()

    # 解析参数：判断第一个参数是 Excel 文件还是选项
    excel_file = None
    if len(sys.argv) >= 2 and not sys.argv[1].startswith("--"):
        # 第一个参数不以 -- 开头，视为 Excel 文件
        excel_file = sys.argv[1]

    # 解析可选参数
    output_file, sheet_name, log_level = _parse_optional_args()

    # 如果命令行指定了日志级别，覆盖配置文件
    if log_level:
        get_logger().set_console_level(log_level)

    # 执行主流程（传递用户指定的文件路径，None 表示由插件自动查找）
    process_log_to_excel(
        excel_file=excel_file,  # None 表示由 dld_configtmp 插件查找默认模板
        trace_file=None,  # None 表示由 config_parser 插件查找默认 trace
        output_file=output_file,
        sheet_name=sheet_name,
    )


if __name__ == "__main__":
    main()
