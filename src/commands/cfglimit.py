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
            "excel",
            help="已填充的Excel配置文件路径",
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
            from config.default_config import RAW_CONFIG
            from src.plugins.constraint_checker.plugin import ConstraintCheckerPlugin

            # 创建约束检查插件实例
            config = RAW_CONFIG.get("constraint_checker", {})
            if args.report:
                config["report_path"] = args.report

            checker = ConstraintCheckerPlugin(config)

            if not checker.enabled:
                warning("约束检查插件未启用")
                return 0

            # 准备上下文
            context = {
                "excel_file": args.excel,
            }

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
