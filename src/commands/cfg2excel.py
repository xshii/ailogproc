"""
cfg2excel 命令 - 配置导出到Excel
"""

import argparse
import os

from src.commands import Command
from src.utils import info, error


class Cfg2ExcelCommand(Command):
    """配置导出到Excel命令"""

    @property
    def name(self) -> str:
        return "cfg2excel"

    @property
    def help(self) -> str:
        return "从日志文件提取配置并填充到Excel模板"

    def register_arguments(self, parser: argparse.ArgumentParser) -> None:
        """注册参数"""
        parser.add_argument(
            "template",
            nargs="?",
            help="Excel模板文件路径（可选，默认自动查找）",
        )
        parser.add_argument(
            "log",
            nargs="?",
            help="日志文件路径（可选，默认自动查找）",
        )
        parser.add_argument(
            "-o",
            "--output",
            help="输出Excel文件路径",
        )
        parser.add_argument(
            "-s",
            "--sheet",
            help="指定工作表名称",
        )
        self.add_log_level_argument(parser)

    def execute(self, args: argparse.Namespace) -> int:
        """执行配置导出"""
        info("=" * 60)
        info("配置导出到Excel (cfg2excel)")
        info("=" * 60)

        # 验证输入文件
        if not self._validate_inputs(args):
            return 1

        try:
            # 延迟导入避免循环依赖
            from src.workflow import process_log_to_excel

            # 调用工作流
            process_log_to_excel(
                excel_file=args.template,
                trace_file=args.log,
                output_file=args.output,
                sheet_name=args.sheet,
            )
            info("配置导出完成")
            return 0
        except Exception as e:
            error(f"配置导出失败: {e}")
            import traceback

            traceback.print_exc()
            return 1

    def _validate_inputs(self, args: argparse.Namespace) -> bool:
        """验证输入文件和路径"""
        from src.utils import validate_file_extension, validate_directory_writable

        has_errors = False

        # 验证模板文件（如果指定）
        if args.template:
            if not os.path.isfile(args.template):
                error(f"模板文件不存在: {args.template}")
                has_errors = True
            elif not validate_file_extension(args.template, [".xlsx", ".xlsm"]):
                error(f"模板文件格式不支持（仅支持 .xlsx 或 .xlsm）: {args.template}")
                has_errors = True

        # 验证日志文件（如果指定）
        if args.log:
            if not os.path.isfile(args.log):
                error(f"日志文件不存在: {args.log}")
                has_errors = True

        # 验证输出路径（如果指定）
        if args.output:
            output_dir = os.path.dirname(args.output) or "."
            if not os.path.isdir(output_dir):
                error(f"输出目录不存在: {output_dir}")
                has_errors = True
            elif not validate_directory_writable(output_dir):
                error(f"输出目录不可写: {output_dir}")
                has_errors = True

        return not has_errors
