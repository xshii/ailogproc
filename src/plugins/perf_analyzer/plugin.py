"""
性能数据分析器插件 - 统计和分析性能数据（基于cycle）
"""

import os
import json
import csv
from typing import List, Dict, Optional
from src.plugins.base import Plugin
from src.utils import info, warning, error


class PerfAnalyzerPlugin(Plugin):
    """性能数据分析器 - Level 2 (Processor)"""

    level = 2
    dependencies = ["perf_parser"]

    def execute(self, context: dict) -> dict:
        """分析性能数据

        Args:
            context: 上下文字典，需要包含：
                - perf_parser.pairs: 关联的事件对

        Returns:
            {
                'summary': {汇总统计},
                'by_unit': {按执行单元的统计},
                'mfu': {MFU计算结果} (可选),
                'report_paths': {报告文件路径}
            }
        """
        # 获取解析结果
        perf_data = context.get("perf_parser", {})
        pairs = perf_data.get("pairs", [])

        if not pairs:
            warning("[性能分析] 没有可分析的数据")
            return {"summary": {}, "by_unit": {}, "mfu": {}}

        info(f"[性能分析] 开始分析 {len(pairs)} 对事件")

        # 1. 计算汇总统计
        summary = self._compute_summary(pairs)

        # 2. 按执行单元分组统计
        by_unit = {}
        if self.config["grouping"]["by_execution_unit"]:
            by_unit = self._analyze_by_unit(pairs)

        # 3. 按来源分组统计（用于多文件对比）
        by_source = self._analyze_by_source(pairs)

        # 4. 计算 MFU（如果启用）
        mfu_result = {}
        if self.config["analysis"].get("compute_mfu", False):
            mfu_result = self._compute_mfu(pairs)
            if mfu_result:
                info(f"[性能分析] 平均 MFU: {mfu_result.get('mean_mfu', 0):.2%}")

        result = {
            "summary": summary,
            "by_unit": by_unit,
            "by_source": by_source,
            "mfu": mfu_result,
        }

        # 5. 生成报告
        report_paths = self._generate_reports(result, pairs)
        result["report_paths"] = report_paths

        info("[性能分析] 分析完成")
        return result

    def _extract_duration(self, pair: Dict) -> Optional[float]:
        """从pair中提取duration值（cycles）"""
        performance = pair.get("performance", {})

        # 尝试找到任何包含duration或cycle的字段
        for value in performance.values():
            if isinstance(value, (int, float)):
                return float(value)

        return None

    def _compute_summary(self, pairs: List[Dict]) -> Dict:
        """计算汇总统计（以cycles为单位）"""
        durations = []
        for p in pairs:
            duration = self._extract_duration(p)
            if duration is not None:
                durations.append(duration)

        if not durations:
            return {}

        durations_sorted = sorted(durations)
        n = len(durations)

        summary = {
            "count": n,
            "min_cycles": min(durations),
            "max_cycles": max(durations),
            "mean_cycles": sum(durations) / n,
            "median_cycles": durations_sorted[n // 2],
            "p50_cycles": durations_sorted[int(n * 0.50)],
            "p90_cycles": durations_sorted[int(n * 0.90)],
            "p95_cycles": durations_sorted[int(n * 0.95)],
            "p99_cycles": durations_sorted[int(n * 0.99)]
            if n >= 100
            else durations_sorted[-1],
        }

        # 如果配置了频率，也计算以时间为单位的统计
        freq_ghz = self.config["hardware"].get("frequency_ghz")
        if freq_ghz:
            summary["frequency_ghz"] = freq_ghz
            summary["min_ms"] = summary["min_cycles"] / (freq_ghz * 1e6)
            summary["max_ms"] = summary["max_cycles"] / (freq_ghz * 1e6)
            summary["mean_ms"] = summary["mean_cycles"] / (freq_ghz * 1e6)
            summary["median_ms"] = summary["median_cycles"] / (freq_ghz * 1e6)

        return summary

    def _analyze_by_unit(self, pairs: List[Dict]) -> Dict:
        """按执行单元分组统计"""
        by_unit = {}

        for pair in pairs:
            unit = pair.get("execution_unit", "unknown")
            duration = self._extract_duration(pair)

            if duration is None:
                continue

            if unit not in by_unit:
                by_unit[unit] = []

            by_unit[unit].append(duration)

        # 计算每个单元的统计
        stats = {}
        freq_ghz = self.config["hardware"].get("frequency_ghz")

        for unit, durations in by_unit.items():
            if not durations:
                continue

            durations_sorted = sorted(durations)
            n = len(durations)

            unit_stats = {
                "count": n,
                "min_cycles": min(durations),
                "max_cycles": max(durations),
                "mean_cycles": sum(durations) / n,
                "median_cycles": durations_sorted[n // 2],
            }

            # 如果配置了频率，也计算以时间为单位
            if freq_ghz:
                unit_stats["mean_ms"] = unit_stats["mean_cycles"] / (freq_ghz * 1e6)

            stats[unit] = unit_stats

        return stats

    def _analyze_by_source(self, pairs: List[Dict]) -> Dict:
        """按来源分组统计（用于多文件对比）"""
        by_source = {}

        for pair in pairs:
            source = pair.get("source", "unknown")
            duration = self._extract_duration(pair)

            if duration is None:
                continue

            if source not in by_source:
                by_source[source] = []

            by_source[source].append(duration)

        # 计算每个来源的统计
        stats = {}
        freq_ghz = self.config["hardware"].get("frequency_ghz")

        for source, durations in by_source.items():
            if not durations:
                continue

            durations_sorted = sorted(durations)
            n = len(durations)

            source_stats = {
                "count": n,
                "min_cycles": min(durations),
                "max_cycles": max(durations),
                "mean_cycles": sum(durations) / n,
                "median_cycles": durations_sorted[n // 2],
                "p90_cycles": durations_sorted[int(n * 0.90)],
                "p95_cycles": durations_sorted[int(n * 0.95)],
            }

            # 如果配置了频率，也计算以时间为单位
            if freq_ghz:
                source_stats["mean_ms"] = source_stats["mean_cycles"] / (freq_ghz * 1e6)
                source_stats["p90_ms"] = source_stats["p90_cycles"] / (freq_ghz * 1e6)
                source_stats["p95_ms"] = source_stats["p95_cycles"] / (freq_ghz * 1e6)

            stats[source] = source_stats

        return stats

    def _compute_mfu(self, pairs: List[Dict]) -> Dict:
        """计算 MFU (Model FLOPs Utilization)

        MFU = 实际FLOPs / 理论峰值FLOPs
        实际FLOPs = FLOPs数量 / (cycles / frequency)
        """
        freq_ghz = self.config["hardware"].get("frequency_ghz")
        peak_tflops = self.config["hardware"].get("peak_tflops")

        if not freq_ghz or not peak_tflops:
            warning("[性能分析] MFU计算需要配置 frequency_ghz 和 peak_tflops")
            return {}

        info(f"[性能分析] 计算 MFU (频率: {freq_ghz} GHz, 峰值: {peak_tflops} TFLOPS)")

        # 注：这里需要从日志中提取FLOPs信息
        # 当前实现是示例，实际需要根据具体日志格式调整

        mfu_values = []
        for pair in pairs:
            # 从start_event或end_event中提取FLOPs（需要根据实际日志格式）
            # 示例：假设fields中有flops字段
            start_fields = pair.get("start_event", {}).get("fields", {})
            end_fields = pair.get("end_event", {}).get("fields", {})

            flops = start_fields.get("flops") or end_fields.get("flops")
            if not flops:
                continue

            duration_cycles = self._extract_duration(pair)
            if not duration_cycles:
                continue

            # 计算实际时间（秒）
            duration_seconds = duration_cycles / (freq_ghz * 1e9)

            # 计算实际TFLOPS
            actual_tflops = (flops / duration_seconds) / 1e12

            # 计算MFU
            mfu = actual_tflops / peak_tflops
            mfu_values.append(mfu)

        if not mfu_values:
            warning("[性能分析] 未找到FLOPs数据，无法计算MFU")
            return {}

        return {
            "count": len(mfu_values),
            "mean_mfu": sum(mfu_values) / len(mfu_values),
            "min_mfu": min(mfu_values),
            "max_mfu": max(mfu_values),
            "median_mfu": sorted(mfu_values)[len(mfu_values) // 2],
            "frequency_ghz": freq_ghz,
            "peak_tflops": peak_tflops,
        }

    def _generate_reports(self, result: Dict, pairs: List[Dict]) -> Dict:
        """生成报告文件"""
        report_paths = {}

        # 生成JSON报告
        if self.config["reporting"]["generate_json"]:
            json_path = self._generate_json_report(result, pairs)
            if json_path:
                report_paths["json"] = json_path

        # 生成CSV报告
        if self.config["reporting"]["generate_csv"]:
            csv_path = self._generate_csv_report(pairs)
            if csv_path:
                report_paths["csv"] = csv_path

        return report_paths

    def _generate_json_report(self, result: Dict, pairs: List[Dict]) -> str:
        """生成JSON报告"""
        try:
            json_path = self.config["reporting"]["json_path"]
            os.makedirs(os.path.dirname(json_path), exist_ok=True)

            report = {
                "summary": result["summary"],
                "by_unit": result["by_unit"],
                "by_source": result.get("by_source", {}),
                "mfu": result.get("mfu", {}),
                "total_pairs": len(pairs),
            }

            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(report, f, ensure_ascii=False, indent=2)

            info(f"[性能分析] JSON报告已保存: {json_path}")
            return json_path

        except Exception as e:
            error(f"[性能分析] 生成JSON报告失败: {e}")
            return None

    def _generate_csv_report(self, pairs: List[Dict]) -> str:
        """生成CSV报告"""
        try:
            csv_path = self.config["reporting"]["csv_path"]
            os.makedirs(os.path.dirname(csv_path), exist_ok=True)

            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)

                # 写入表头
                writer.writerow(
                    [
                        "Source",
                        "Correlation ID",
                        "Rule Name",
                        "Execution Unit",
                        "Duration (cycles)",
                        "Start Line",
                        "End Line",
                    ]
                )

                # 写入数据
                for pair in pairs:
                    duration = self._extract_duration(pair)

                    writer.writerow(
                        [
                            pair.get("source", ""),
                            pair.get("correlation_id", ""),
                            pair.get("rule_name", ""),
                            pair.get("execution_unit", ""),
                            duration if duration is not None else "",
                            pair.get("start_event", {}).get("line_number", ""),
                            pair.get("end_event", {}).get("line_number", ""),
                        ]
                    )

            info(f"[性能分析] CSV报告已保存: {csv_path}")
            return csv_path

        except Exception as e:
            error(f"[性能分析] 生成CSV报告失败: {e}")
            return None
