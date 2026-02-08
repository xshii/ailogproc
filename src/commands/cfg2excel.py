"""
cfg2excel 命令 - 配置导出到Excel
"""

import argparse
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
        parser.add_argument(
            "--log-level",
            choices=["DEBUG", "INFO", "WARNING", "ERROR"],
            help="设置日志级别",
        )

    def execute(self, args: argparse.Namespace) -> int:
        """执行配置导出"""
        info("=" * 60)
        info("配置导出到Excel (cfg2excel)")
        info("=" * 60)

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
