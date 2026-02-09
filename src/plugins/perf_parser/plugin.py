"""
性能日志解析器插件 - 基于多规则提取的性能日志解析
"""

import json
import os
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from src.plugins.base import Plugin
from src.utils import error, info, warning


class PerfParserPlugin(Plugin):
    """性能日志解析器 - Level 1 (Extractor)"""

    level = 1
    dependencies = []  # 不依赖其他插件

    def execute(self, context: dict) -> dict:
        """解析性能日志（支持多文件）

        Args:
            context: 上下文字典，包含：
                - perf_log_file: 性能日志文件路径（可选，单文件模式）
                - perf_log_files: 性能日志文件列表（可选，多文件模式）

        Returns:
            {
                'pairs': [关联的事件对，每个包含 source 字段],
                'statistics': {
                    'total': 总体统计,
                    'by_source': {按来源分组的统计}
                }
            }
        """
        # 获取日志文件配置
        log_sources = self._get_log_sources(context)

        if not log_sources:
            error("[性能日志解析] 未指定日志文件")
            return {"pairs": [], "statistics": {}}

        info(f"[性能日志解析] 开始解析 {len(log_sources)} 个日志文件")

        # 解析所有日志文件
        all_pairs = []
        all_stats_by_source = {}
        total_events = 0
        total_unpaired = 0

        for source_label, log_path in log_sources:
            info(f"[性能日志解析] 解析 [{source_label}]: {log_path}")

            # 读取并解析日志
            events = self._parse_log_file(log_path)
            info(f"[性能日志解析] [{source_label}] 解析到 {len(events)} 个事件")

            # 关联开始/结束事件
            pairs, unpaired = self._correlate_events(events, source_label)
            info(f"[性能日志解析] [{source_label}] 找到 {len(pairs)} 对关联事件")

            # 对未匹配的事件打印告警并记录日志
            if unpaired:
                warning(
                    f"[性能日志解析] [{source_label}] {len(unpaired)} 个事件未找到配对"
                )
                for event in unpaired:
                    warning(
                        f"  - 未配对: {event['event_type']} 事件，"
                        f"规则={event['rule_name']}, "
                        f"行号={event['line_number']}, "
                        f"字段={event['fields']}"
                    )

                # 记录到文件
                self._log_unpaired_events(unpaired, log_path, source_label)

            # 统计信息
            source_stats = self._compute_source_statistics(
                len(events), pairs, len(unpaired)
            )
            all_stats_by_source[source_label] = source_stats

            # 累加
            all_pairs.extend(pairs)
            total_events += len(events)
            total_unpaired += len(unpaired)

        # 总体统计
        statistics = {
            "total": {
                "total_events": total_events,
                "paired_count": len(all_pairs),
                "unpaired_count": total_unpaired,
                "source_count": len(log_sources),
            },
            "by_source": all_stats_by_source,
        }

        info(f"[性能日志解析] 完成，共 {len(all_pairs)} 对关联事件")

        result = {
            "pairs": all_pairs,
            "statistics": statistics,
        }

        return result

    def _get_log_sources(self, context: dict) -> List[Tuple[str, str]]:
        """获取日志文件来源列表

        Returns:
            [(source_label, log_path), ...]
        """
        sources = []

        # 优先从 context 获取（命令行传入）
        ctx_file = context.get("perf_log_file")
        ctx_files = context.get("perf_log_files")

        if ctx_files:
            # 多文件模式
            for item in ctx_files:
                if isinstance(item, dict):
                    sources.append((item.get("label", "unknown"), item.get("path")))
                else:
                    # 简化模式，使用文件名作为 label
                    label = os.path.basename(item).split(".")[0]
                    sources.append((label, item))
        elif ctx_file:
            # 单文件模式（向后兼容）
            label = os.path.basename(ctx_file).split(".")[0]
            sources.append((label, ctx_file))
        else:
            # 从配置读取
            cfg_files = self.config.get("log_files")
            if cfg_files:
                for item in cfg_files:
                    if isinstance(item, dict):
                        path = item.get("path")
                        if path:
                            sources.append((item.get("label", "unknown"), path))
                    elif isinstance(item, str):
                        label = os.path.basename(item).split(".")[0]
                        sources.append((label, item))

        return sources

    def _parse_log_file(self, log_file: str) -> List[Dict]:
        """解析日志文件，使用多规则提取

        Returns:
            事件列表，每个事件包含：
            {
                'line_number': int,
                'event_type': 'start'|'end',
                'rule_name': str,
                'fields': {...}  # 提取的字段
            }
        """
        events = []
        extraction_rules = self.config.get("extraction_rules", [])

        try:
            with open(log_file, encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue

                    # 尝试每个提取规则
                    for rule in extraction_rules:
                        # 尝试匹配开始模式
                        start_event = self._try_match_pattern(
                            line, line_num, rule, "start"
                        )
                        if start_event:
                            events.append(start_event)
                            break  # 一行只匹配一个规则

                        # 尝试匹配结束模式
                        end_event = self._try_match_pattern(line, line_num, rule, "end")
                        if end_event:
                            events.append(end_event)
                            break

        except Exception as e:
            error(f"[性能日志解析] 读取文件失败: {e}")

        return events

    def _try_match_pattern(
        self, line: str, line_num: int, rule: dict, pattern_type: str
    ) -> Optional[Dict]:
        """尝试用指定规则匹配一行日志

        Args:
            line: 日志行
            line_num: 行号
            rule: 提取规则
            pattern_type: 'start' 或 'end'

        Returns:
            匹配成功返回事件字典，否则返回 None
        """
        pattern_key = f"{pattern_type}_pattern"
        if pattern_key not in rule:
            return None

        pattern_config = rule[pattern_key]
        regex = pattern_config.get("regex")
        field_defs = pattern_config.get("fields", {})

        if not regex:
            return None

        # 尝试匹配
        match = re.search(regex, line)
        if not match:
            return None

        # 提取字段
        fields = {}
        try:
            for field_name, field_config in field_defs.items():
                # 从命名捕获组提取
                value = match.group(field_name)

                # 类型转换
                field_type = field_config.get("type", "string")
                if field_type == "int":
                    value = int(value)
                elif field_type == "float":
                    value = float(value)
                # string 类型不需要转换

                fields[field_name] = value

            # 检查必需字段
            for field_name, field_config in field_defs.items():
                if field_config.get("required", False) and field_name not in fields:
                    return None

        except (ValueError, IndexError, KeyError):
            # 提取或转换失败
            return None

        # 构建事件
        event = {
            "line_number": line_num,
            "event_type": pattern_type,
            "rule_name": rule.get("name", "unknown"),
            "fields": fields,
        }

        return event

    def _correlate_events(
        self, events: List[Dict], source_label: str
    ) -> Tuple[List[Dict], List[Dict]]:
        """关联开始和结束事件

        Args:
            events: 事件列表
            source_label: 来源标识

        Returns:
            (配对的事件列表, 未配对的事件列表)
        """
        pairs = []
        unpaired = []

        # 按规则名称分组
        events_by_rule = {}
        for event in events:
            rule_name = event["rule_name"]
            if rule_name not in events_by_rule:
                events_by_rule[rule_name] = {"starts": [], "ends": []}

            if event["event_type"] == "start":
                events_by_rule[rule_name]["starts"].append(event)
            elif event["event_type"] == "end":
                events_by_rule[rule_name]["ends"].append(event)

        # 对每个规则进行配对
        extraction_rules = self.config.get("extraction_rules", [])
        for rule in extraction_rules:
            rule_name = rule.get("name", "unknown")
            if rule_name not in events_by_rule:
                continue

            rule_events = events_by_rule[rule_name]
            match_fields = rule.get("match_fields", [])

            # 配对该规则的开始和结束事件
            rule_pairs, rule_unpaired = self._pair_events(
                rule_events["starts"],
                rule_events["ends"],
                match_fields,
                rule,
                source_label,
            )

            pairs.extend(rule_pairs)
            unpaired.extend(rule_unpaired)

        return pairs, unpaired

    def _pair_events(
        self,
        start_events: List[Dict],
        end_events: List[Dict],
        match_fields: List[str],
        rule: dict,
        source_label: str,
    ) -> Tuple[List[Dict], List[Dict]]:
        """配对开始和结束事件

        Args:
            start_events: 开始事件列表
            end_events: 结束事件列表
            match_fields: 需要匹配的字段名列表
            rule: 提取规则配置
            source_label: 来源标识

        Returns:
            (配对列表, 未配对列表)
        """
        pairs = []
        unpaired = []
        matched_ends = set()

        for start in start_events:
            # 查找匹配的结束事件
            matched_end = None
            for idx, end in enumerate(end_events):
                if idx in matched_ends:
                    continue

                # 检查所有匹配字段是否相同
                if self._fields_match(start["fields"], end["fields"], match_fields):
                    matched_end = end
                    matched_ends.add(idx)
                    break

            if matched_end:
                # 计算性能指标
                performance = self._calculate_performance(start, matched_end, rule)

                # 提取关联ID（使用第一个匹配字段的值）
                correlation_id = (
                    start["fields"].get(match_fields[0])
                    if match_fields
                    else f"line_{start['line_number']}"
                )

                # 提取执行单元（如果配置了 'unit' 字段）
                execution_unit = start["fields"].get("unit") or matched_end[
                    "fields"
                ].get("unit")

                pairs.append(
                    {
                        "source": source_label,
                        "correlation_id": str(correlation_id),
                        "execution_unit": execution_unit,
                        "start_event": start,
                        "end_event": matched_end,
                        "rule_name": rule.get("name"),
                        "performance": performance,
                    }
                )
            else:
                unpaired.append(start)

        # 未匹配的结束事件
        for idx, end in enumerate(end_events):
            if idx not in matched_ends:
                unpaired.append(end)

        return pairs, unpaired

    def _fields_match(
        self, fields1: dict, fields2: dict, match_fields: List[str]
    ) -> bool:
        """检查两个字段字典在指定字段上是否匹配"""
        return all(fields1.get(field) == fields2.get(field) for field in match_fields)

    def _calculate_performance(
        self, start_event: Dict, end_event: Dict, rule: dict
    ) -> Dict:
        """计算性能指标

        Args:
            start_event: 开始事件
            end_event: 结束事件
            rule: 提取规则（包含 performance 配置）

        Returns:
            性能指标字典
        """
        perf_config = rule.get("performance", {})
        duration_field = perf_config.get("duration_field", "duration")
        formula = perf_config.get("formula", "")

        performance = {}

        if formula:
            # 解析公式（如 "cycle_end - cycle_start"）
            try:
                # 简单的减法公式解析
                if " - " in formula:
                    parts = formula.split(" - ")
                    if len(parts) == 2:
                        end_field = parts[0].strip()
                        start_field = parts[1].strip()

                        end_value = end_event["fields"].get(end_field)
                        start_value = start_event["fields"].get(start_field)

                        if end_value is not None and start_value is not None:
                            duration = end_value - start_value
                            performance[duration_field] = duration
            except Exception as e:
                warning(f"[性能日志解析] 计算性能指标失败: {e}")

        return performance

    def _compute_source_statistics(
        self, total_events: int, pairs: List[Dict], unpaired_count: int
    ) -> Dict:
        """计算单个来源的统计信息"""
        stats = {
            "total_events": total_events,
            "paired_count": len(pairs),
            "unpaired_count": unpaired_count,
        }

        # 按规则统计
        rules = {}
        for pair in pairs:
            rule_name = pair.get("rule_name", "unknown")
            rules[rule_name] = rules.get(rule_name, 0) + 1

        stats["by_rule"] = rules

        # 按执行单元统计
        units = {}
        for pair in pairs:
            unit = pair.get("execution_unit", "unknown")
            units[unit] = units.get(unit, 0) + 1

        stats["by_execution_unit"] = units

        return stats

    def _log_unpaired_events(
        self, unpaired: List[Dict], source_log_file: str, source_label: str = "unknown"
    ) -> None:
        """记录未配对事件到日志文件

        Args:
            unpaired: 未配对的事件列表
            source_log_file: 源日志文件路径（用于生成日志文件名）
        """
        unpaired_config = self.config.get("unpaired_log", {})

        if not unpaired_config.get("enable", True):
            return

        log_path = unpaired_config.get("path", "output/perf_unpaired.log")

        try:
            # 确保输出目录存在
            os.makedirs(os.path.dirname(log_path), exist_ok=True)

            # 追加写入日志
            with open(log_path, "a", encoding="utf-8") as f:
                # 写入时间戳和分隔符
                f.write("\n" + "=" * 80 + "\n")
                f.write(f"时间: {datetime.now().isoformat()}\n")
                f.write(f"来源: {source_label}\n")
                f.write(f"源文件: {source_log_file}\n")
                f.write(f"未配对事件数: {len(unpaired)}\n")
                f.write("=" * 80 + "\n\n")

                # 写入每个未配对事件的详细信息
                for idx, event in enumerate(unpaired, 1):
                    f.write(f"[{idx}] {event['event_type'].upper()} 事件\n")
                    f.write(f"    规则: {event['rule_name']}\n")
                    f.write(f"    行号: {event['line_number']}\n")
                    f.write(
                        f"    字段: {json.dumps(event['fields'], ensure_ascii=False, indent=6)}\n"
                    )
                    f.write("\n")

            info(f"[性能日志解析] 未配对事件已记录到: {log_path}")

        except Exception as e:
            error(f"[性能日志解析] 记录未配对事件失败: {e}")
