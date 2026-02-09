"""
性能可视化插件 - 生成算子执行时间线（类似升腾Studio）
"""

import os
from typing import List, Dict, Optional
from src.plugins.base import Plugin
from src.utils import info, warning, error


class PerfVisualizerPlugin(Plugin):
    """性能可视化器 - Level 3 (Output)"""

    level = 3
    dependencies = ["perf_parser", "perf_analyzer"]

    def execute(self, context: dict) -> dict:
        """生成算子执行时间线

        Args:
            context: 上下文字典，需要包含：
                - perf_parser.pairs: 事件对
                - perf_analyzer.summary: 统计摘要

        Returns:
            {
                'charts': {生成的图表路径},
                'timeline_path': str  # 主时间线图路径
            }
        """
        # 获取数据
        perf_data = context.get("perf_parser", {})
        pairs = perf_data.get("pairs", [])

        if not pairs:
            warning("[性能可视化] 没有可视化的数据")
            return {"charts": {}, "timeline_path": None}

        info("[性能可视化] 开始生成算子执行时间线")

        charts = {}

        # 生成算子执行时间线（主图表）
        timeline_path = self._generate_operator_timeline(pairs, context)
        if timeline_path:
            charts["operator_timeline"] = timeline_path
            info(f"[性能可视化] 时间线图已生成: {timeline_path}")

        # 生成耗时分布直方图（可选）
        if self.config["visualizations"].get("histogram", False):
            hist_path = self._generate_histogram(pairs)
            if hist_path:
                charts["histogram"] = hist_path

        return {"charts": charts, "timeline_path": timeline_path}

    def _generate_operator_timeline(self, pairs: List[Dict], context: dict) -> str:
        """生成算子执行时间线（类似升腾Studio效果）"""
        try:
            # 检查依赖
            try:
                from pyecharts import options as opts  # noqa: F401  # pylint: disable=unused-import,import-outside-toplevel
                from pyecharts.charts import Bar  # noqa: F401  # pylint: disable=unused-import,import-outside-toplevel
            except ImportError:
                error("[性能可视化] 需要安装 pyecharts: pip install pyecharts")
                return None

            # 准备数据
            timeline_data = self._prepare_timeline_data(pairs)

            if not timeline_data:
                warning("[性能可视化] 没有有效的时间线数据")
                return None

            # 创建图表
            chart = self._create_timeline_figure(timeline_data, context)

            # 保存
            output_path = self.config["gantt"]["output_path"]
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            chart.render(output_path)

            info(f"[性能可视化] 算子执行时间线已保存: {output_path}")
            return output_path

        except Exception as e:
            error(f"[性能可视化] 生成时间线失败: {e}")
            import traceback

            traceback.print_exc()
            return None

    def _prepare_timeline_data(self, pairs: List[Dict]) -> List[Dict]:
        """准备时间线数据（使用cycle作为时间轴）"""
        timeline_data = []

        # 按开始行号排序
        sorted_pairs = sorted(pairs, key=lambda p: p["start_event"]["line_number"])

        for idx, pair in enumerate(sorted_pairs):
            start_event = pair["start_event"]
            end_event = pair["end_event"]

            # 提取算子信息
            operator_id = pair["correlation_id"]
            unit = pair.get("execution_unit", "Unknown")

            # 从字段中提取 cycle 信息
            start_fields = start_event.get("fields", {})
            end_fields = end_event.get("fields", {})

            # 尝试找到 cycle 字段（可能是 cycle_start, start_cycle, begin_cycle 等）
            start_cycle = self._extract_cycle_value(
                start_fields, ["cycle_start", "start_cycle", "begin_cycle"]
            )
            end_cycle = self._extract_cycle_value(
                end_fields, ["cycle_end", "end_cycle", "done_cycle"]
            )

            # 如果没有cycle信息，跳过
            if start_cycle is None or end_cycle is None:
                continue

            duration_cycles = end_cycle - start_cycle

            # 从 performance 提取额外信息
            performance = pair.get("performance", {})

            timeline_data.append(
                {
                    "index": idx,
                    "source": pair.get("source", "unknown"),
                    "operator_id": operator_id,
                    "unit": unit,
                    "start_cycle": start_cycle,
                    "end_cycle": end_cycle,
                    "duration_cycles": duration_cycles,
                    "start_line": start_event["line_number"],
                    "end_line": end_event["line_number"],
                    "performance": performance,
                    "rule_name": pair.get("rule_name"),
                }
            )

        return timeline_data

    def _extract_cycle_value(
        self, fields: dict, possible_names: List[str]
    ) -> Optional[int]:
        """从字段中提取cycle值（尝试多个可能的字段名）"""
        for name in possible_names:
            if name in fields:
                return fields[name]
        return None

    def _create_timeline_figure(self, timeline_data: List[Dict], context: dict):
        """创建时间线图表（PyEcharts版本，使用堆叠Bar模拟甘特图）"""

        config = self.config["gantt"]
        units, unit_colors = self._prepare_unit_data(timeline_data)

        bar = self._initialize_chart(config, units)
        self._add_timeline_series(bar, timeline_data, units, unit_colors)
        self._apply_chart_options(bar, config)

        bar.reversal_axis()
        return bar

    def _prepare_unit_data(self, timeline_data: List[Dict]) -> tuple:
        """准备执行单元数据和颜色映射"""
        units = sorted(set(item["unit"] for item in timeline_data))
        colors = self._get_color_scheme(len(units))
        unit_colors = {
            unit: colors[idx % len(colors)] for idx, unit in enumerate(units)
        }
        return units, unit_colors

    def _initialize_chart(self, config: Dict, units: List):
        """初始化图表对象"""
        from pyecharts import options as opts
        from pyecharts.charts import Bar

        bar = Bar(
            init_opts=opts.InitOpts(
                width=f"{config.get('width', 1400)}px",
                height=f"{config.get('height', 600)}px",
                theme="light",
            )
        )
        bar.add_xaxis(xaxis_data=units)
        return bar

    def _add_timeline_series(
        self, bar, timeline_data: List[Dict], units: List, unit_colors: Dict
    ) -> None:
        """添加时间线数据系列"""
        from pyecharts import options as opts

        for idx, item in enumerate(timeline_data):
            unit_idx = units.index(item["unit"])
            color = unit_colors[item["unit"]]

            # 添加占位系列（模拟起始位置）
            self._add_placeholder_series(bar, idx, unit_idx, item, len(units), opts)

            # 添加实际数据系列
            self._add_duration_series(bar, idx, unit_idx, item, color, len(units), opts)

    def _add_placeholder_series(
        self, bar, idx: int, unit_idx: int, item: Dict, num_units: int, opts
    ) -> None:
        """添加占位系列"""
        placeholder_data = [0] * num_units
        placeholder_data[unit_idx] = item["start_cycle"]

        bar.add_yaxis(
            series_name=f"_placeholder_{idx}",
            y_axis=placeholder_data,
            stack=f"stack_{unit_idx}",
            itemstyle_opts=opts.ItemStyleOpts(opacity=0),
            label_opts=opts.LabelOpts(is_show=False),
        )

    def _add_duration_series(
        self, bar, idx: int, unit_idx: int, item: Dict, color: str, num_units: int, opts
    ) -> None:
        """添加耗时数据系列"""
        duration_data = [None] * num_units
        duration_data[unit_idx] = item["duration_cycles"]

        tooltip_content = self._build_tooltip_content(item)

        bar.add_yaxis(
            series_name=f"{item['operator_id']}",
            y_axis=duration_data,
            stack=f"stack_{unit_idx}",
            itemstyle_opts=opts.ItemStyleOpts(color=color),
            label_opts=opts.LabelOpts(is_show=False),
            tooltip_opts=opts.TooltipOpts(formatter=tooltip_content),
        )

    def _build_tooltip_content(self, item: Dict) -> str:
        """构建tooltip内容"""
        return (
            f"算子ID: {item['operator_id']}<br/>"
            f"来源: {item['source']}<br/>"
            f"开始Cycle: {item['start_cycle']}<br/>"
            f"结束Cycle: {item['end_cycle']}<br/>"
            f"耗时: {item['duration_cycles']} cycles<br/>"
            f"日志行: {item['start_line']}-{item['end_line']}"
        )

    def _apply_chart_options(self, bar, config: Dict) -> None:
        """应用图表全局选项"""
        from pyecharts import options as opts

        bar.set_global_opts(
            title_opts=self._build_title_opts(config, opts),
            xaxis_opts=self._build_xaxis_opts(opts),
            yaxis_opts=self._build_yaxis_opts(opts),
            tooltip_opts=opts.TooltipOpts(trigger="item", axis_pointer_type="shadow"),
            legend_opts=opts.LegendOpts(is_show=False),
            datazoom_opts=self._build_datazoom_opts(opts),
        )

    def _build_title_opts(self, config: Dict, opts):
        """构建标题选项"""
        return opts.TitleOpts(
            title=config["title"],
            pos_left="center",
            title_textstyle_opts=opts.TextStyleOpts(color="#2c3e50", font_size=20),
        )

    def _build_xaxis_opts(self, opts):
        """构建X轴选项"""
        return opts.AxisOpts(
            name="执行单元",
            axislabel_opts=opts.LabelOpts(font_size=12, rotate=0),
        )

    def _build_yaxis_opts(self, opts):
        """构建Y轴选项"""
        return opts.AxisOpts(
            name="Cycle",
            name_location="middle",
            name_gap=50,
            name_textstyle_opts=opts.TextStyleOpts(color="#34495e", font_size=14),
            axislabel_opts=opts.LabelOpts(font_size=12),
            splitline_opts=opts.SplitLineOpts(is_show=True),
        )

    def _build_datazoom_opts(self, opts) -> List:
        """构建缩放选项"""
        return [
            opts.DataZoomOpts(type_="slider", orient="vertical"),
            opts.DataZoomOpts(type_="slider", orient="horizontal"),
            opts.DataZoomOpts(type_="inside", orient="vertical"),
            opts.DataZoomOpts(type_="inside", orient="horizontal"),
        ]

    def _get_color_scheme(self, num_colors: int) -> List[str]:
        """获取配色方案"""
        scheme = self.config["gantt"].get("color_scheme", "default")

        if scheme == "rainbow":
            # 彩虹配色
            return [
                "#e74c3c",  # 红
                "#e67e22",  # 橙
                "#f39c12",  # 黄
                "#2ecc71",  # 绿
                "#3498db",  # 蓝
                "#9b59b6",  # 紫
            ]
        elif scheme == "monochrome":
            # 单色深浅
            return [
                "#3498db",
                "#5dade2",
                "#85c1e9",
                "#aed6f1",
                "#d6eaf8",
            ]
        else:
            # 默认配色（升腾Studio风格）
            return [
                "#3498db",  # 蓝色
                "#2ecc71",  # 绿色
                "#f39c12",  # 橙色
                "#e74c3c",  # 红色
                "#9b59b6",  # 紫色
                "#1abc9c",  # 青色
                "#34495e",  # 深灰
                "#e67e22",  # 深橙
                "#16a085",  # 深青
                "#c0392b",  # 深红
            ]

    def _generate_histogram(self, pairs: List[Dict]) -> str:
        """生成耗时分布直方图（基于cycle）"""
        try:
            from pyecharts import options as opts
            from pyecharts.charts import Bar

            # 提取耗时数据（cycles）
            durations = []
            for p in pairs:
                perf = p.get("performance", {})
                # 尝试从performance中获取任何duration字段
                for key, value in perf.items():
                    if "duration" in key.lower() or "cycle" in key.lower():
                        if isinstance(value, (int, float)):
                            durations.append(value)
                            break

            if not durations:
                warning("[性能可视化] 没有耗时数据")
                return None

            config = self.config.get("histogram", {})
            bins = config.get("bins", 30)

            # 计算直方图分组
            min_val = min(durations)
            max_val = max(durations)
            bin_width = (max_val - min_val) / bins

            # 创建分组区间
            bin_ranges = []
            bin_counts = [0] * bins
            for i in range(bins):
                bin_start = min_val + i * bin_width
                bin_end = bin_start + bin_width
                bin_ranges.append(f"{int(bin_start)}-{int(bin_end)}")

                # 统计每个区间的数量
                for duration in durations:
                    if bin_start <= duration < bin_end or (
                        i == bins - 1 and duration == bin_end
                    ):
                        bin_counts[i] += 1

            # 创建柱状图
            bar = Bar(
                init_opts=opts.InitOpts(
                    width=f"{config.get('width', 900)}px",
                    height=f"{config.get('height', 500)}px",
                    theme="light",
                )
            )

            bar.add_xaxis(xaxis_data=bin_ranges)
            bar.add_yaxis(
                series_name="数量",
                y_axis=bin_counts,
                itemstyle_opts=opts.ItemStyleOpts(color="#3498db"),
                label_opts=opts.LabelOpts(is_show=False),
            )

            bar.set_global_opts(
                title_opts=opts.TitleOpts(
                    title=config.get("title", "算子耗时分布"),
                    pos_left="center",
                    title_textstyle_opts=opts.TextStyleOpts(
                        color="#2c3e50", font_size=18
                    ),
                ),
                xaxis_opts=opts.AxisOpts(
                    name="耗时 (cycles)",
                    name_location="middle",
                    name_gap=30,
                    axislabel_opts=opts.LabelOpts(rotate=45, font_size=10),
                    splitline_opts=opts.SplitLineOpts(is_show=True),
                ),
                yaxis_opts=opts.AxisOpts(
                    name="数量",
                    name_location="middle",
                    name_gap=40,
                    splitline_opts=opts.SplitLineOpts(is_show=True),
                ),
                tooltip_opts=opts.TooltipOpts(
                    trigger="axis", axis_pointer_type="shadow"
                ),
                legend_opts=opts.LegendOpts(is_show=False),
            )

            # 保存
            output_path = config.get("output_path", "output/perf_histogram.html")
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            bar.render(output_path)

            info(f"[性能可视化] 耗时分布图已保存: {output_path}")
            return output_path

        except Exception as e:
            error(f"[性能可视化] 生成分布图失败: {e}")
            return None
