"""
性能数据分析器插件 - 统计和分析性能数据
"""

import os
import json
import csv
from typing import List, Dict
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
                'outliers': [异常值列表],
                'report_paths': {报告文件路径}
            }
        """
        # 获取解析结果
        perf_data = context.get("perf_parser", {})
        pairs = perf_data.get("pairs", [])

        if not pairs:
            warning("[性能分析] 没有可分析的数据")
            return {"summary": {}, "by_unit": {}, "outliers": []}

        info(f"[性能分析] 开始分析 {len(pairs)} 对事件")

        # 1. 计算汇总统计
        summary = self._compute_summary(pairs)

        # 2. 按执行单元分组统计
        by_unit = {}
        if self.config["grouping"]["by_execution_unit"]:
            by_unit = self._analyze_by_unit(pairs)

        # 3. 检测异常值
        outliers = []
        if self.config["analysis"]["detect_outliers"]:
            outliers = self._detect_outliers(pairs)
            if outliers:
                warning(f"[性能分析] 检测到 {len(outliers)} 个异常值")

        result = {"summary": summary, "by_unit": by_unit, "outliers": outliers}

        # 4. 生成报告
        report_paths = self._generate_reports(result, pairs)
        result["report_paths"] = report_paths

        info("[性能分析] 分析完成")
        return result

    def _compute_summary(self, pairs: List[Dict]) -> Dict:
        """计算汇总统计"""
        durations = [p["duration_seconds"] for p in pairs if p["duration_seconds"]]

        if not durations:
            return {}

        durations_sorted = sorted(durations)
        n = len(durations)

        summary = {
            "count": n,
            "min": min(durations),
            "max": max(durations),
            "mean": sum(durations) / n,
            "median": durations_sorted[n // 2],
            "p50": durations_sorted[int(n * 0.50)],
            "p90": durations_sorted[int(n * 0.90)],
            "p95": durations_sorted[int(n * 0.95)],
            "p99": durations_sorted[int(n * 0.99)] if n >= 100 else durations_sorted[-1],
        }

        return summary

    def _analyze_by_unit(self, pairs: List[Dict]) -> Dict:
        """按执行单元分组统计"""
        by_unit = {}

        for pair in pairs:
            unit = pair.get("execution_unit", "unknown")
            duration = pair.get("duration_seconds")

            if duration is None:
                continue

            if unit not in by_unit:
                by_unit[unit] = []

            by_unit[unit].append(duration)

        # 计算每个单元的统计
        stats = {}
        for unit, durations in by_unit.items():
            if not durations:
                continue

            durations_sorted = sorted(durations)
            n = len(durations)

            stats[unit] = {
                "count": n,
                "min": min(durations),
                "max": max(durations),
                "mean": sum(durations) / n,
                "median": durations_sorted[n // 2],
            }

        return stats

    def _detect_outliers(self, pairs: List[Dict]) -> List[Dict]:
        """检测异常值"""
        method = self.config["analysis"]["outlier_method"]

        durations = [
            (i, p["duration_seconds"])
            for i, p in enumerate(pairs)
            if p["duration_seconds"]
        ]

        if not durations:
            return []

        outliers = []

        if method == "iqr":
            outliers = self._detect_outliers_iqr(durations, pairs)
        elif method == "zscore":
            outliers = self._detect_outliers_zscore(durations, pairs)
        elif method == "percentile":
            outliers = self._detect_outliers_percentile(durations, pairs)

        return outliers

    def _detect_outliers_iqr(
        self, durations: List[tuple], pairs: List[Dict]
    ) -> List[Dict]:
        """使用IQR方法检测异常值"""
        values = [d[1] for d in durations]
        values_sorted = sorted(values)
        n = len(values_sorted)

        q1 = values_sorted[n // 4]
        q3 = values_sorted[3 * n // 4]
        iqr = q3 - q1

        multiplier = self.config["analysis"]["iqr_multiplier"]
        lower_bound = q1 - multiplier * iqr
        upper_bound = q3 + multiplier * iqr

        outliers = []
        for idx, duration in durations:
            if duration < lower_bound or duration > upper_bound:
                outliers.append(
                    {
                        "pair": pairs[idx],
                        "duration": duration,
                        "reason": "IQR outlier",
                        "bounds": [lower_bound, upper_bound],
                    }
                )

        return outliers

    def _detect_outliers_zscore(
        self, durations: List[tuple], pairs: List[Dict]
    ) -> List[Dict]:
        """使用Z-score方法检测异常值"""
        values = [d[1] for d in durations]
        mean = sum(values) / len(values)

        # 计算标准差
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        std_dev = variance**0.5

        if std_dev == 0:
            return []

        threshold = self.config["analysis"]["zscore_threshold"]

        outliers = []
        for idx, duration in durations:
            z_score = abs((duration - mean) / std_dev)
            if z_score > threshold:
                outliers.append(
                    {
                        "pair": pairs[idx],
                        "duration": duration,
                        "reason": "Z-score outlier",
                        "z_score": z_score,
                    }
                )

        return outliers

    def _detect_outliers_percentile(
        self, durations: List[tuple], pairs: List[Dict]
    ) -> List[Dict]:
        """使用百分位方法检测异常值"""
        values = [d[1] for d in durations]
        values_sorted = sorted(values)
        n = len(values_sorted)

        lower_pct = self.config["analysis"]["percentile_lower"]
        upper_pct = self.config["analysis"]["percentile_upper"]

        lower_bound = values_sorted[int(n * lower_pct / 100)]
        upper_bound = values_sorted[int(n * upper_pct / 100)]

        outliers = []
        for idx, duration in durations:
            if duration < lower_bound or duration > upper_bound:
                outliers.append(
                    {
                        "pair": pairs[idx],
                        "duration": duration,
                        "reason": "Percentile outlier",
                        "bounds": [lower_bound, upper_bound],
                    }
                )

        return outliers

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
                "outliers_count": len(result["outliers"]),
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
                        "Correlation ID",
                        "Execution Unit",
                        "Duration (s)",
                        "Start Time",
                        "End Time",
                    ]
                )

                # 写入数据
                for pair in pairs:
                    start_ts = (
                        pair["start_event"]["timestamp"].isoformat()
                        if pair["start_event"]["timestamp"]
                        else ""
                    )
                    end_ts = (
                        pair["end_event"]["timestamp"].isoformat()
                        if pair["end_event"]["timestamp"]
                        else ""
                    )

                    writer.writerow(
                        [
                            pair["correlation_id"],
                            pair.get("execution_unit", ""),
                            pair.get("duration_seconds", ""),
                            start_ts,
                            end_ts,
                        ]
                    )

            info(f"[性能分析] CSV报告已保存: {csv_path}")
            return csv_path

        except Exception as e:
            error(f"[性能分析] 生成CSV报告失败: {e}")
            return None
