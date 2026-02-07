"""
日志解析器模块
"""
import re
from config.default_config import LOG_SECTION_PATTERN, LOG_FIELD_PATTERN
from src.utils import extract_value, map_field_name


class LogParser:
    """解析日志文件，提取配置块和键值对"""
    
    def __init__(self, log_file):
        self.log_file = log_file
        self.sections = []  # 存储所有配置块
        
    def parse(self):
        """解析日志文件"""
        current_section = None
        
        with open(self.log_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.rstrip('\n')
                
                # 检查是否是配置块开始
                section_match = re.search(LOG_SECTION_PATTERN, line)
                if section_match:
                    # 保存上一个配置块
                    if current_section:
                        self.sections.append(current_section)
                    
                    # 开始新配置块
                    section_name = section_match.group(1).strip()
                    current_section = {
                        'name': section_name,
                        'fields': {}
                    }
                    continue
                
                # 检查是否是字段行
                if current_section:
                    field_match = re.search(LOG_FIELD_PATTERN, line)
                    if field_match:
                        log_field_name = field_match.group(1).strip()
                        raw_value = field_match.group(2).strip()
                        
                        # 应用字段名映射
                        mapped_field_name = map_field_name(log_field_name)
                        
                        # 提取值
                        field_value = extract_value(raw_value)
                        
                        # 保存映射后的字段名和值
                        current_section['fields'][mapped_field_name] = field_value
                        
                        # 如果字段名被映射了，记录原始名称（用于调试）
                        if log_field_name != mapped_field_name:
                            if 'field_mappings' not in current_section:
                                current_section['field_mappings'] = {}
                            current_section['field_mappings'][mapped_field_name] = log_field_name
        
        # 保存最后一个配置块
        if current_section:
            self.sections.append(current_section)
        
        return self.sections
    
    def get_top_section(self, keyword):
        """获取顶格表格的配置块"""
        for section in self.sections:
            if section['name'] == keyword:
                return section
        return None
    
    def get_sub_sections(self, pattern):
        """获取匹配指定模式的所有子配置块"""
        matched = []
        for section in self.sections:
            if re.match(pattern, section['name']):
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
            if section['name'] == top_keyword:
                # 遇到新的TopConfig，保存上一组
                if current_group:
                    groups.append(current_group)
                
                # 开始新组
                current_group = {
                    'top': section,
                    'subs': []
                }
            elif current_group:
                # 将子配置块加入当前组
                current_group['subs'].append(section)
        
        # 保存最后一组
        if current_group:
            groups.append(current_group)
        
        return groups
