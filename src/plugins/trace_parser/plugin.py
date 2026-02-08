"""
Trace解析插件 - 从trace文件中提取配置信息
"""

import os
import re
from pathlib import Path
from src.plugins.base import Plugin


from src.utils import info
class TraceParserPlugin(Plugin):
    """Trace解析插件 - Level 1 (Extractor)"""

    level = 1  # 提取层
    dependencies = ["dld_tmp"]  # 依赖模板下载插件（确保模板准备好）

    def execute(self, context: dict) -> dict:
        """从trace文件中提取配置信息

        Args:
            context: 上下文字典，可能包含：
                - trace_file: trace文件路径（优先使用）

        Returns:
            {
                'sections': 解析出的配置块列表,
                'parser': TraceParser实例（供其他插件使用）,
                'trace_file': 实际使用的trace文件路径
            }
        """
        # 优先使用 context 中的 trace_file，否则从配置获取默认路径
        trace_file = context.get("trace_file")

        if not trace_file:
            trace_file = self._get_default_trace_file()

        if not trace_file:
            raise ValueError("trace_parser: 未指定trace文件，且配置中未设置默认路径")

        info(f"[Trace解析] 解析trace文件: {trace_file}")
        # 创建解析器并解析（传递配置）
        parser = TraceParser(trace_file, self.config)
        sections = parser.parse()

        info(f"[Trace解析] ✓ 找到 {len(sections)} 个配置块")
        return {
            "sections": sections,
            "parser": parser,  # 返回 parser 实例供其他插件使用
            "trace_file": trace_file,  # 返回实际使用的trace路径
        }

    def _get_default_trace_file(self) -> str | None:
        """从配置获取默认trace文件路径（支持多目录和多模式查找）"""
        default_config = self.config.get("default_trace", {})
        path = default_config.get("path")

        # 如果配置了具体路径
        if path:
            # 检查是文件还是目录
            if os.path.isfile(path):
                return path

            if os.path.isdir(path):
                # 是目录，查找最新trace
                if default_config.get("auto_find_latest", True):
                    patterns = default_config.get("file_patterns", ["*.txt"])
                    if isinstance(patterns, str):
                        patterns = [patterns]
                    return self._find_latest_trace_multi_pattern(path, patterns)

        # 没有配置 path，使用 search_dirs（支持多个目录）
        search_dirs = default_config.get("search_dirs", [default_config.get("search_dir")])
        if isinstance(search_dirs, str):
            search_dirs = [search_dirs]

        patterns = default_config.get("file_patterns", ["*.txt"])
        if isinstance(patterns, str):
            patterns = [patterns]

        # 按优先级遍历搜索目录和模式
        for search_dir in search_dirs:
            if not search_dir or not os.path.isdir(search_dir):
                continue

            if default_config.get("auto_find_latest", True):
                trace_file = self._find_latest_trace_multi_pattern(search_dir, patterns)
                if trace_file:
                    return trace_file

        return None

    def _find_latest_trace_multi_pattern(self, directory: str, patterns: list) -> str | None:
        """在目录中使用多个模式查找最新的trace文件"""
        for pattern in patterns:
            trace_file = self._find_latest_trace(directory, pattern)
            if trace_file:
                return trace_file
        return None

    def _find_latest_trace(self, directory: str, pattern: str) -> str | None:
        """在目录中查找最新的trace文件"""
        trace_files = list(Path(directory).glob(pattern))

        if not trace_files:
            return None

        # 按修改时间排序，返回最新的
        latest = max(trace_files, key=lambda p: p.stat().st_mtime)
        return str(latest)


# ==================== 内部类和工具函数 ====================


class TraceParser:
    """解析trace文件，提取配置块和键值对"""

    def __init__(self, trace_file, config: dict):
        self.trace_file = trace_file
        self.config = config
        self.sections = []  # 存储所有配置块

        # 从配置读取正则表达式
        self.section_pattern = config["log_patterns"]["section"]
        self.field_pattern = config["log_patterns"]["field"]

    def parse(self):
        """解析trace文件"""
        current_section = None

        with open(self.trace_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.rstrip("\n")

                # 检查是否是配置块开始
                section_match = re.search(self.section_pattern, line)
                if section_match:
                    # 保存上一个配置块
                    if current_section:
                        self.sections.append(current_section)

                    # 开始新配置块
                    section_name = section_match.group(1).strip()
                    current_section = {"name": section_name, "fields": {}}
                    continue

                # 检查是否是字段行
                if current_section:
                    field_match = re.search(self.field_pattern, line)
                    if field_match:
                        log_field_name = field_match.group(1).strip()
                        raw_value = field_match.group(2).strip()

                        # 应用字段名映射
                        mapped_field_name = _map_field_name(log_field_name, self.config)

                        # 提取值
                        field_value = _extract_value(raw_value, self.config)

                        # 保存映射后的字段名和值
                        current_section["fields"][mapped_field_name] = field_value

                        # 如果字段名被映射了，记录原始名称（用于调试）
                        if log_field_name != mapped_field_name:
                            if "field_mappings" not in current_section:
                                current_section["field_mappings"] = {}
                            current_section["field_mappings"][mapped_field_name] = (
                                log_field_name
                            )

        # 保存最后一个配置块
        if current_section:
            self.sections.append(current_section)

        return self.sections

    def get_top_section(self, keyword):
        """获取顶格表格的配置块"""
        for section in self.sections:
            if section["name"] == keyword:
                return section
        return None

    def get_sub_sections(self, pattern):
        """获取匹配指定模式的所有子配置块"""
        matched = []
        for section in self.sections:
            if re.match(pattern, section["name"]):
                matched.append(section)
        return matched

    def group_by_top_config(self, top_keyword):
        """将配置块按TopConfig分组

        返回格式: [
            {'top': top_section, 'subs': [sub_sections]},
            {'top': top_section, 'subs': [sub_sections]},
            ...
        ]
        """
        groups = []
        current_group = None

        for section in self.sections:
            if section["name"] == top_keyword:
                # 遇到新的TopConfig，保存上一组
                if current_group:
                    groups.append(current_group)

                # 开始新组
                current_group = {"top": section, "subs": []}
            elif current_group:
                # 将子配置块加入当前组
                current_group["subs"].append(section)

        # 保存最后一组
        if current_group:
            groups.append(current_group)

        return groups


def _extract_value(raw_value, config: dict):
    """
    提取字段值
    如果配置了 extract_parentheses=True，则提取括号中的内容
    例如: "4096  (0x1000)" -> "0x1000"
          "12345" -> "12345"
    """
    extract_parentheses = config.get("value_extraction", {}).get(
        "extract_parentheses", False
    )

    if not extract_parentheses:
        return raw_value.strip()

    # 查找括号中的内容
    match = re.search(r"\((.*?)\)", raw_value)
    if match:
        return match.group(1).strip()

    # 没有括号，返回原始值
    return raw_value.strip()


def _map_field_name(log_field_name, config: dict):
    """
    将日志中的字段名映射为Excel中的字段名
    如果在 field_name_mapping 中有配置，则使用映射后的名称
    否则返回原字段名
    """
    field_name_mapping = config.get("field_name_mapping", {})

    if log_field_name in field_name_mapping:
        return field_name_mapping[log_field_name]
    return log_field_name
