"""
cfglimit 命令 - 配置约束检查
"""

import argparse
from src.commands import Command
from src.utils import info, error, warning


class CfgLimitCommand(Command):
    """配置约束检查命令"""

    @property
    def name(self) -> str:
        return "cfglimit"

    @property
    def help(self) -> str:
        return "检查配置是否符合约束规则"

    def register_arguments(self, parser: argparse.ArgumentParser) -> None:
        """注册参数"""
        parser.add_argument(
            "log",
            help="日志文件路径",
        )
        parser.add_argument(
            "-r",
            "--report",
            help="约束检查报告输出路径（默认：output/constraint_report.json）",
        )
        parser.add_argument(
            "--log-level",
            choices=["DEBUG", "INFO", "WARNING", "ERROR"],
            help="设置日志级别",
        )

    def execute(self, args: argparse.Namespace) -> int:
        """执行约束检查"""
        info("=" * 60)
        info("配置约束检查 (cfglimit)")
        info("=" * 60)

        try:
            # 延迟导入
            from src.plugins.config_parser.plugin import ConfigParserPlugin
            from src.plugins.constraint_checker.plugin import ConstraintCheckerPlugin

            # 1. 解析日志文件
            info("[1/2] 解析日志文件...")
            parser = ConfigParserPlugin()
            context = {"trace_file": args.log}
            parser_result = parser.execute(context)

            if not parser_result or not parser_result.get("sections"):
                error("日志文件解析失败或未找到配置数据")
                return 1

            sections = parser_result.get("sections", [])
            info(f"  ✓ 找到 {len(sections)} 个配置块")

            # 将解析结果放入上下文
            context["config_parser"] = parser_result

            # 2. 执行约束检查
            info("[2/2] 检查配置约束...")
            checker = ConstraintCheckerPlugin()

            # 应用命令行参数覆盖
            if args.report:
                checker.config["report_path"] = args.report

            if not checker.enabled:
                warning("约束检查插件未启用")
                return 0

            # 执行约束检查
            result = checker.execute(context)

            # 显示结果
            if result.get("validation_passed"):
                info(f"✓ 配置通过所有约束检查 (版本: {result.get('version', 'unknown')})")
                return 0
            else:
                violations = result.get("violations", [])
                error(f"✗ 发现 {len(violations)} 个约束违规")
                for v in violations:
                    error(f"  - {v.get('type')}: {v.get('message')}")
                return 1

        except Exception as e:
            error(f"约束检查失败: {e}")
            import traceback
            traceback.print_exc()
            return 1
