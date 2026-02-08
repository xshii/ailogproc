"""
性能可视化插件 - 生成算子执行时间线（类似升腾Studio）
"""

import os
from typing import List, Dict
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

        info(f"[性能可视化] 开始生成算子执行时间线")

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

    def _generate_operator_timeline(
        self, pairs: List[Dict], context: dict
    ) -> str:
        """生成算子执行时间线（类似升腾Studio效果）"""
        try:
            # 检查依赖
            try:
                import plotly.graph_objects as go
                from plotly.subplots import make_subplots
            except ImportError:
                error("[性能可视化] 需要安装 plotly: pip install plotly")
                return None

            # 准备数据
            timeline_data = self._prepare_timeline_data(pairs)

            if not timeline_data:
                warning("[性能可视化] 没有有效的时间线数据")
                return None

            # 创建图表
            fig = self._create_timeline_figure(timeline_data, context)

            # 保存
            output_path = self.config["gantt"]["output_path"]
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            fig.write_html(output_path)

            info(f"[性能可视化] 算子执行时间线已保存: {output_path}")
            return output_path

        except Exception as e:
            error(f"[性能可视化] 生成时间线失败: {e}")
            import traceback

            traceback.print_exc()
            return None

    def _prepare_timeline_data(self, pairs: List[Dict]) -> List[Dict]:
        """准备时间线数据"""
        timeline_data = []
        base_time = None

        # 按开始时间排序
        sorted_pairs = sorted(
            pairs,
            key=lambda p: p["start_event"]["timestamp"]
            if p["start_event"]["timestamp"]
            else float("inf"),
        )

        for idx, pair in enumerate(sorted_pairs):
            start_event = pair["start_event"]
            end_event = pair["end_event"]

            # 跳过没有时间戳的事件
            if not start_event["timestamp"] or not end_event["timestamp"]:
                continue

            # 记录基准时间（第一个事件的开始时间）
            if base_time is None:
                base_time = start_event["timestamp"]

            # 计算相对时间（毫秒）
            start_ms = (start_event["timestamp"] - base_time).total_seconds() * 1000
            end_ms = (end_event["timestamp"] - base_time).total_seconds() * 1000
            duration_ms = end_ms - start_ms

            # 提取算子信息
            operator_id = pair["correlation_id"]
            unit = pair.get("execution_unit", "Unknown")
            
            # 从 metrics 提取额外信息
            metrics = end_event.get("metrics", {})
            duration_info = metrics.get("duration", {})

            timeline_data.append(
                {
                    "index": idx,
                    "operator_id": operator_id,
                    "unit": unit,
                    "start_ms": start_ms,
                    "end_ms": end_ms,
                    "duration_ms": duration_ms,
                    "start_line": start_event["line_number"],
                    "end_line": end_event["line_number"],
                    "metrics": metrics,
                }
            )

        return timeline_data

    def _create_timeline_figure(
        self, timeline_data: List[Dict], context: dict
    ) -> "go.Figure":
        """创建时间线图表（升腾Studio风格）"""
        import plotly.graph_objects as go

        config = self.config["gantt"]

        # 按执行单元分组
        units = sorted(set(item["unit"] for item in timeline_data))
        unit_to_row = {unit: idx for idx, unit in enumerate(units)}

        # 准备颜色映射
        colors = self._get_color_scheme(len(units))
        unit_colors = {unit: colors[idx % len(colors)] for idx, unit in enumerate(units)}

        # 创建图表
        fig = go.Figure()

        # 添加每个算子的执行条
        for item in timeline_data:
            unit = item["unit"]
            y_pos = unit_to_row[unit]

            # 悬停信息
            hover_text = (
                f"<b>算子ID:</b> {item['operator_id']}<br>"
                f"<b>执行单元:</b> {unit}<br>"
                f"<b>开始时间:</b> {item['start_ms']:.3f} ms<br>"
                f"<b>结束时间:</b> {item['end_ms']:.3f} ms<br>"
                f"<b>耗时:</b> {item['duration_ms']:.3f} ms<br>"
                f"<b>日志行:</b> {item['start_line']}-{item['end_line']}"
            )

            # 添加metrics信息
            if item["metrics"]:
                hover_text += "<br><b>指标:</b>"
                for key, value in item["metrics"].items():
                    if isinstance(value, dict) and "value" in value:
                        hover_text += f"<br>  {key}: {value['value']} {value.get('unit', '')}"

            fig.add_trace(
                go.Bar(
                    name=unit,
                    x=[item["duration_ms"]],
                    y=[unit],
                    base=[item["start_ms"]],
                    orientation="h",
                    marker=dict(
                        color=unit_colors[unit],
                        line=dict(color="white", width=0.5),
                    ),
                    hovertemplate=hover_text + "<extra></extra>",
                    showlegend=False,
                )
            )

        # 更新布局（升腾Studio风格）
        fig.update_layout(
            title=dict(
                text=config["title"], font=dict(size=20, color="#2c3e50"), x=0.5
            ),
            xaxis=dict(
                title="时间 (ms)",
                titlefont=dict(size=14, color="#34495e"),
                showgrid=True,
                gridcolor="#ecf0f1",
                zeroline=True,
                zerolinecolor="#bdc3c7",
                tickfont=dict(size=12),
            ),
            yaxis=dict(
                title="执行单元",
                titlefont=dict(size=14, color="#34495e"),
                categoryorder="array",
                categoryarray=units,
                tickfont=dict(size=12),
            ),
            height=config.get("height", 600),
            width=config.get("width", 1400),
            barmode="overlay",
            bargap=0.2,
            plot_bgcolor="white",
            paper_bgcolor="white",
            hovermode="closest",
            # 添加工具栏按钮
            modebar=dict(
                bgcolor="rgba(255,255,255,0.7)",
                color="#7f8c8d",
                activecolor="#2980b9",
            ),
        )

        # 添加图例（显示执行单元）
        for unit in units:
            fig.add_trace(
                go.Scatter(
                    x=[None],
                    y=[None],
                    mode="markers",
                    name=unit,
                    marker=dict(size=10, color=unit_colors[unit]),
                    showlegend=True,
                )
            )

        fig.update_layout(
            legend=dict(
                title="执行单元",
                orientation="v",
                yanchor="top",
                y=1,
                xanchor="left",
                x=1.02,
                bgcolor="rgba(255,255,255,0.8)",
                bordercolor="#bdc3c7",
                borderwidth=1,
            )
        )

        return fig

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
        """生成耗时分布直方图"""
        try:
            import plotly.graph_objects as go

            # 提取耗时数据（毫秒）
            durations = [
                p["duration_seconds"] * 1000 for p in pairs if p["duration_seconds"]
            ]

            if not durations:
                warning("[性能可视化] 没有耗时数据")
                return None

            config = self.config.get("histogram", {})

            # 创建直方图
            fig = go.Figure(
                data=[
                    go.Histogram(
                        x=durations,
                        nbinsx=config.get("bins", 30),
                        marker=dict(color="#3498db", line=dict(color="white", width=1)),
                    )
                ]
            )

            fig.update_layout(
                title=dict(
                    text=config.get("title", "算子耗时分布"),
                    font=dict(size=18, color="#2c3e50"),
                    x=0.5,
                ),
                xaxis=dict(
                    title="耗时 (ms)",
                    titlefont=dict(size=14),
                    showgrid=True,
                    gridcolor="#ecf0f1",
                ),
                yaxis=dict(
                    title="数量",
                    titlefont=dict(size=14),
                    showgrid=True,
                    gridcolor="#ecf0f1",
                ),
                height=config.get("height", 500),
                width=config.get("width", 900),
                plot_bgcolor="white",
                paper_bgcolor="white",
                showlegend=False,
            )

            # 保存
            output_path = config.get("output_path", "output/perf_histogram.html")
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            fig.write_html(output_path)

            info(f"[性能可视化] 耗时分布图已保存: {output_path}")
            return output_path

        except Exception as e:
            error(f"[性能可视化] 生成分布图失败: {e}")
            return None
