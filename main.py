#!/usr/bin/env python3
"""
AI日志处理工具 - 主入口
"""

import os
import sys
import argparse
import yaml

from src.utils import setup_logger, get_logger, info
from src.commands import setup_subparsers
from src.commands.registry import register_all_commands


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


def main():
    """主函数"""
    # 先加载日志配置
    _load_logger_config()

    # 注册所有命令
    register_all_commands()

    # 创建主解析器
    parser = argparse.ArgumentParser(
        prog="ailogproc",
        description="AI日志处理工具 - 配置提取、约束检查、性能分析",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 配置导出到Excel
  %(prog)s cfg2excel template.xlsx log.txt -o output.xlsx

  # 配置约束检查
  %(prog)s cfglimit filled_config.xlsx -r report.json

  # 性能日志分析
  %(prog)s perflog device0.log device1.log --freq 1.0

  # 查看子命令帮助
  %(prog)s cfg2excel --help
""",
    )

    # 设置子命令
    setup_subparsers(parser)

    # 解析参数
    args = parser.parse_args()

    # 如果没有指定命令，显示帮助
    if not hasattr(args, "func"):
        parser.print_help()
        return 1

    # 如果命令行指定了日志级别，覆盖配置文件
    if hasattr(args, "log_level") and args.log_level:
        get_logger().set_console_level(args.log_level)

    # 执行命令
    try:
        return args.func(args)
    except KeyboardInterrupt:
        info("\n操作已取消")
        return 130
    except Exception as e:
        info(f"错误: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
