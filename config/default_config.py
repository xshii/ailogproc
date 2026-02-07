"""
配置文件 - 所有可配置参数集中管理
"""

# ==================== 关键字映射配置 ====================
KEYWORD_MAPPING = {
    'ExCfg-ER': r'ERCfg\s*\(grp\s*=\s*\d+\)',
    'ExCfg-TX': r'TXCfg\s*\(grp\s*=\s*\d+\)',
    'INxCfg': r'InxCfg\d+',
}

# ==================== 顶格表格配置 ====================
ENABLE_TOP_TABLE = True
TOP_TABLE_START_ROW = 1
TOP_TABLE_LOG_KEYWORD = 'opSch'

# ==================== A列特殊前缀配置 ====================
SPECIAL_PREFIX_FOR_B_COLUMN = ['Spec', 'Special']
SPECIAL_PREFIX_MERGE_ROWS = 2

# ==================== 字段名映射配置 ====================
FIELD_NAME_MAPPING = {
    'cfg_group': 'cfgGroup',
    'pwr_level': 'powerLevel',
}

# ==================== 匹配模式配置 ====================
ENABLE_PARTIAL_MATCH = True
SHOW_UNMATCHED_WARNINGS = True

# ==================== 填充目标列配置 ====================
TARGET_COLUMN = 5

# ==================== 值提取配置 ====================
EXTRACT_PARENTHESES = True

# ==================== 日志解析正则 ====================
LOG_FIELD_PATTERN = r'\|-\s+(\S+)\s*=\s*(.+)$'
LOG_SECTION_PATTERN = r'^thread\d+\s+cyc=0x[0-9a-fA-F]+\s+([^|].+)$'

# ==================== 自动文件名配置 ====================
ENABLE_AUTO_FILENAME = True
FILENAME_FIELDS = ['systemMode', 'debugLevel']
FILENAME_VALUE_MAPPING = {
    'systemMode': {
        '1': 'auto', '0x01': 'auto',
        '2': 'manual', '0x02': 'manual',
    },
    'debugLevel': {
        '1': 'low', '0x01': 'low',
        '2': 'high', '0x02': 'high',
        '3': 'full', '0x03': 'full',
    },
}
FILENAME_DEFAULT_VALUE = None
