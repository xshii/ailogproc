"""
配置提取插件 - 从日志中提取配置信息
"""

import re
from src.plugins.base import Plugin


class ConfigExtractorPlugin(Plugin):
    """配置提取插件 - Level 1 (Extractor)"""

    level = 1  # 提取层
    dependencies = []  # 无依赖，第一层插件

    def execute(self, context: dict) -> dict:
        """从日志文件中提取配置信息

        Args:
            context: 上下文字典，需要包含：
                - log_file: 日志文件路径

        Returns:
            {
                'sections': 解析出的配置块列表,
                'parser': LogParser实例（供其他插件使用）
            }
        """
        log_file = context.get("log_file")
        if not log_file:
            raise ValueError("config_extractor: context 中缺少 'log_file'")

        print(f"[配置提取] 解析日志文件: {log_file}")

        # 创建解析器并解析（传递配置）
        parser = LogParser(log_file, self.config)
        sections = parser.parse()

        print(f"[配置提取] ✓ 找到 {len(sections)} 个配置块")

        return {
            "sections": sections,
            "parser": parser,  # 返回 parser 实例供其他插件使用
        }


# ==================== 内部类和工具函数 ====================


class LogParser:
    """解析日志文件，提取配置块和键值对"""

    def __init__(self, log_file, config: dict):
        self.log_file = log_file
        self.config = config
        self.sections = []  # 存储所有配置块

        # 从配置读取正则表达式
        self.section_pattern = config["log_patterns"]["section"]
        self.field_pattern = config["log_patterns"]["field"]

    def parse(self):
        """解析日志文件"""
        current_section = None

        with open(self.log_file, "r", encoding="utf-8") as f:
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
