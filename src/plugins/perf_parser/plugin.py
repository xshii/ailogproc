"""
性能日志解析器插件 - 解析性能日志并找到关联的开始/结束行
"""

import re
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from src.plugins.base import Plugin
from src.utils import info, warning, error, debug


class PerfParserPlugin(Plugin):
    """性能日志解析器 - Level 1 (Extractor)"""

    level = 1
    dependencies = []  # 不依赖其他插件

    def execute(self, context: dict) -> dict:
        """解析性能日志

        Args:
            context: 上下文字典，包含：
                - perf_log_file: 性能日志文件路径（可选）

        Returns:
            {
                'events': [事件列表],
                'pairs': [关联的事件对],
                'unpaired': [未匹配的事件],
                'statistics': {统计信息}
            }
        """
        # 获取日志文件路径
        log_file = context.get("perf_log_file") or self.config.get("log_file")

        if not log_file:
            error("[性能日志解析] 未指定日志文件")
            return {"events": [], "pairs": [], "unpaired": []}

        info(f"[性能日志解析] 开始解析: {log_file}")

        # 读取并解析日志
        events = self._parse_log_file(log_file)
        info(f"[性能日志解析] 解析到 {len(events)} 个事件")

        # 关联开始/结束事件
        pairs, unpaired = self._correlate_events(events)
        info(f"[性能日志解析] 找到 {len(pairs)} 对关联事件")

        if unpaired:
            warning(f"[性能日志解析] {len(unpaired)} 个事件未找到配对")

        # 统计信息
        statistics = self._compute_statistics(events, pairs, unpaired)

        result = {
            "events": events,
            "pairs": pairs,
            "unpaired": unpaired,
            "statistics": statistics,
        }

        return result

    def _parse_log_file(self, log_file: str) -> List[Dict]:
        """解析日志文件

        Returns:
            事件列表，每个事件包含：
            {
                'line_number': int,
                'timestamp': datetime,
                'raw_line': str,
                'event_type': 'start'|'end'|'unknown',
                'correlation_id': str,
                'execution_unit': str,
                'metrics': {...}
            }
        """
        events = []
        ignore_patterns = [
            re.compile(p) for p in self.config["cleaning"]["ignore_patterns"]
        ]

        try:
            with open(log_file, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()

                    # 跳过需要忽略的行
                    if any(pattern.search(line) for pattern in ignore_patterns):
                        continue

                    # 解析事件
                    event = self._parse_line(line, line_num)
                    if event:
                        events.append(event)

        except Exception as e:
            error(f"[性能日志解析] 读取文件失败: {e}")

        return events

    def _parse_line(self, line: str, line_num: int) -> Optional[Dict]:
        """解析单行日志

        Returns:
            事件字典或None（无法解析时）
        """
        # 提取时间戳
        timestamp = self._extract_timestamp(line)

        # 判断事件类型（开始/结束）
        event_type = self._identify_event_type(line)

        # 提取关联ID
        correlation_id = self._extract_correlation_id(line)

        # 如果没有关联ID或事件类型，跳过
        if not correlation_id or event_type == "unknown":
            return None

        # 提取执行单元
        execution_unit = self._extract_execution_unit(line)

        # 提取性能指标
        metrics = self._extract_metrics(line)

        return {
            "line_number": line_num,
            "timestamp": timestamp,
            "raw_line": line,
            "event_type": event_type,
            "correlation_id": correlation_id,
            "execution_unit": execution_unit,
            "metrics": metrics,
        }

    def _extract_timestamp(self, line: str) -> Optional[datetime]:
        """从日志行中提取时间戳"""
        timestamp_regex = self.config["correlation"]["timestamp_regex"]
        match = re.search(timestamp_regex, line)

        if match:
            timestamp_str = match.group(1)
            timestamp_format = self.config["correlation"]["timestamp_format"]
            try:
                return datetime.strptime(timestamp_str, timestamp_format)
            except ValueError:
                return None

        return None

    def _identify_event_type(self, line: str) -> str:
        """识别事件类型（开始/结束/未知）"""
        markers = self.config["correlation"]["markers"]

        # 检查是否包含开始标记
        if any(marker in line for marker in markers["start"]):
            return "start"

        # 检查是否包含结束标记
        if any(marker in line for marker in markers["end"]):
            return "end"

        return "unknown"

    def _extract_correlation_id(self, line: str) -> Optional[str]:
        """提取关联ID"""
        id_fields = self.config["correlation"]["id_fields"]

        # 尝试每个ID字段
        for field in id_fields:
            # 匹配 "字段: 值" 或 "字段:值"
            pattern = rf"{field}\s*:\s*(\S+)"
            match = re.search(pattern, line)
            if match:
                return match.group(1)

        return None

    def _extract_execution_unit(self, line: str) -> Optional[str]:
        """提取执行单元"""
        unit_fields = self.config["metrics"]["execution_unit"]

        for field in unit_fields:
            pattern = rf"{field}\s*:\s*(\S+)"
            match = re.search(pattern, line)
            if match:
                return match.group(1)

        return None

    def _extract_metrics(self, line: str) -> Dict:
        """提取性能指标"""
        metrics = {}

        # 提取耗时
        duration_fields = self.config["metrics"]["duration"]
        for field in duration_fields:
            # 匹配 "字段: 数字单位" 如 "耗时: 25ms"
            pattern = rf"{field}\s*:\s*([\d.]+)\s*(\w+)?"
            match = re.search(pattern, line)
            if match:
                value = float(match.group(1))
                unit = match.group(2) if match.group(2) else ""
                metrics["duration"] = {"value": value, "unit": unit}
                break

        # 提取自定义指标
        custom_metrics = self.config["metrics"].get("custom", {})
        for metric_name, field_list in custom_metrics.items():
            for field in field_list:
                pattern = rf"{field}\s*:\s*([\d.]+)\s*(\w+)?"
                match = re.search(pattern, line)
                if match:
                    value = float(match.group(1))
                    unit = match.group(2) if match.group(2) else ""
                    metrics[metric_name] = {"value": value, "unit": unit}
                    break

        return metrics

    def _correlate_events(
        self, events: List[Dict]
    ) -> Tuple[List[Dict], List[Dict]]:
        """关联开始和结束事件

        Returns:
            (配对的事件列表, 未配对的事件列表)
        """
        pairs = []
        unpaired = []

        # 按关联ID分组
        start_events = {}  # {correlation_id: event}
        end_events = {}  # {correlation_id: event}

        for event in events:
            corr_id = event["correlation_id"]
            event_type = event["event_type"]

            if event_type == "start":
                if corr_id in start_events:
                    warning(
                        f"[性能日志解析] 重复的开始事件: {corr_id} (行 {event['line_number']})"
                    )
                start_events[corr_id] = event
            elif event_type == "end":
                if corr_id in end_events:
                    warning(
                        f"[性能日志解析] 重复的结束事件: {corr_id} (行 {event['line_number']})"
                    )
                end_events[corr_id] = event

        # 配对
        all_ids = set(start_events.keys()) | set(end_events.keys())

        for corr_id in all_ids:
            start = start_events.get(corr_id)
            end = end_events.get(corr_id)

            if start and end:
                # 计算耗时（如果结束事件有时间戳）
                duration = None
                if start["timestamp"] and end["timestamp"]:
                    duration = (end["timestamp"] - start["timestamp"]).total_seconds()

                pairs.append(
                    {
                        "correlation_id": corr_id,
                        "start_event": start,
                        "end_event": end,
                        "duration_seconds": duration,
                        "execution_unit": start["execution_unit"]
                        or end["execution_unit"],
                    }
                )
            else:
                # 未配对的事件
                unpaired_event = start or end
                unpaired.append(unpaired_event)

        return pairs, unpaired

    def _compute_statistics(
        self, events: List[Dict], pairs: List[Dict], unpaired: List[Dict]
    ) -> Dict:
        """计算统计信息"""
        stats = {
            "total_events": len(events),
            "start_events": sum(1 for e in events if e["event_type"] == "start"),
            "end_events": sum(1 for e in events if e["event_type"] == "end"),
            "paired_events": len(pairs),
            "unpaired_events": len(unpaired),
        }

        # 按执行单元统计
        units = {}
        for pair in pairs:
            unit = pair.get("execution_unit", "unknown")
            units[unit] = units.get(unit, 0) + 1

        stats["execution_units"] = units

        return stats
