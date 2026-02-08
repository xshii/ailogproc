"""
perflog 命令 - 性能日志分析
"""

import argparse
from src.commands import Command
from src.utils import info, error


class PerfLogCommand(Command):
    """性能日志分析命令"""

    @property
    def name(self) -> str:
        return "perflog"

    @property
    def help(self) -> str:
        return "分析性能日志并生成统计报告和可视化"

    def register_arguments(self, parser: argparse.ArgumentParser) -> None:
        """注册参数"""
        parser.add_argument(
            "logs",
            nargs="+",
            help="性能日志文件路径（支持多个文件用于对比）",
        )
        parser.add_argument(
            "-o",
            "--output",
            default="output",
            help="输出目录（默认：output/）",
        )
        parser.add_argument(
            "--json",
            help="JSON报告路径（默认：output/perf_analysis.json）",
        )
        parser.add_argument(
            "--csv",
            help="CSV报告路径（默认：output/perf_analysis.csv）",
        )
        parser.add_argument(
            "--timeline",
            help="时间线图路径（默认：output/perf_timeline.html）",
        )
        parser.add_argument(
            "--freq",
            type=float,
            help="时钟频率（GHz），用于转换cycle到时间",
        )
        parser.add_argument(
            "--no-viz",
            action="store_true",
            help="不生成可视化图表",
        )
        parser.add_argument(
            "--log-level",
            choices=["DEBUG", "INFO", "WARNING", "ERROR"],
            help="设置日志级别",
        )

    def execute(self, args: argparse.Namespace) -> int:
        """执行性能分析"""
        info("=" * 60)
        info("性能日志分析 (perflog)")
        info("=" * 60)

        try:
            # 延迟导入
            from src.plugins.perf_parser.plugin import PerfParserPlugin
            from src.plugins.perf_analyzer.plugin import PerfAnalyzerPlugin
            from src.plugins.perf_visualizer.plugin import PerfVisualizerPlugin

            # 准备日志文件列表
            log_files = []
            for log_path in args.logs:
                label = log_path.split("/")[-1].split(".")[0]  # 使用文件名作为标签
                log_files.append({"label": label, "path": log_path})

            # 1. 解析日志
            info(f"[1/3] 解析 {len(log_files)} 个日志文件...")
            parser = PerfParserPlugin()

            context = {"perf_log_files": log_files}
            parser_result = parser.execute(context)

            if not parser_result.get("pairs"):
                error("未找到配对的事件，分析终止")
                return 1

            context["perf_parser"] = parser_result

            # 2. 统计分析
            info("[2/3] 统计分析...")
            analyzer = PerfAnalyzerPlugin()

            # 应用命令行参数覆盖
            if args.freq:
                analyzer.config.setdefault("hardware", {})["frequency_ghz"] = args.freq
            if args.json:
                analyzer.config.setdefault("reporting", {})["json_path"] = args.json
            if args.csv:
                analyzer.config.setdefault("reporting", {})["csv_path"] = args.csv
            analyzer_result = analyzer.execute(context)
            context["perf_analyzer"] = analyzer_result

            # 显示统计摘要
            summary = analyzer_result.get("summary", {})
            info(f"  总事件对数: {summary.get('count', 0)}")
            info(f"  平均耗时: {summary.get('mean_cycles', 0):.0f} cycles")
            if "mean_ms" in summary:
                info(f"            ({summary['mean_ms']:.3f} ms)")

            # 按来源对比
            by_source = analyzer_result.get("by_source", {})
            if len(by_source) > 1:
                info("  来源对比:")
                for source, stats in by_source.items():
                    info(f"    {source}: {stats['mean_cycles']:.0f} cycles (count={stats['count']})")

            # 3. 可视化
            if not args.no_viz:
                info("[3/3] 生成可视化...")
                visualizer = PerfVisualizerPlugin()

                if args.timeline:
                    visualizer.config.setdefault("gantt", {})["output_path"] = args.timeline
                viz_result = visualizer.execute(context)

                timeline_path = viz_result.get("timeline_path")
                if timeline_path:
                    info(f"  时间线图: {timeline_path}")
            else:
                info("[3/3] 跳过可视化")

            info("=" * 60)
            info("性能分析完成")
            info("=" * 60)

            # 显示报告路径
            report_paths = analyzer_result.get("report_paths", {})
            if report_paths:
                info("报告文件:")
                for report_type, path in report_paths.items():
                    info(f"  {report_type.upper()}: {path}")

            return 0

        except Exception as e:
            error(f"性能分析失败: {e}")
            import traceback
            traceback.print_exc()
            return 1
