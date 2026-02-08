"""
Excel Writer 数据模型 - 使用数据类减少参数传递
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any


@dataclass
class CellPosition:
    """单元格位置"""
    row: int
    col: int

    def __str__(self):
        return f"({self.row}, {self.col})"


@dataclass
class TableRange:
    """表格范围"""
    start_row: int
    end_row: int
    start_col: Optional[int] = None
    end_col: Optional[int] = None

    @property
    def row_count(self) -> int:
        """行数"""
        return self.end_row - self.start_row + 1

    def contains_row(self, row: int) -> bool:
        """检查是否包含指定行"""
        return self.start_row <= row <= self.end_row


@dataclass
class MatchContext:
    """匹配上下文 - 用于减少函数参数"""
    worksheet: Any  # openpyxl Worksheet
    position: CellPosition
    field_name: str
    field_value: Any
    sections: List[Dict]
    options: Optional[Dict] = None

    @property
    def row(self) -> int:
        return self.position.row

    @property
    def col(self) -> int:
        return self.position.col


@dataclass
class BColumnMatchContext:
    """B列匹配上下文 - 用于 _try_match_b_column 函数"""
    row: int
    field_name: str
    field_name_lower: str
    a_col_str: str
    enable_partial_match: bool
    special_prefix_no_match: List


@dataclass
class TopTableWarningContext:
    """顶表警告上下文 - 用于 _record_top_table_warnings 函数"""
    special_prefix_no_match: List
    unmatched_fields: List
    show_warnings: bool
    log_section: Dict
    start_row: int
    end_row: int


@dataclass
class CellFillContext:
    """单元格填充上下文 - 用于 _fill_cell_value 函数"""
    row: int
    col: int
    value: Any
    is_special: bool = False
    merge_rows: int = 1


@dataclass
class ColumnMatchContext:
    """列匹配上下文 - 用于 _match_field_in_column 函数"""
    field_name: str
    start_row: int
    end_row: int
    column: int
    enable_partial_match: bool = True


@dataclass
class SectionFillContext:
    """配置块填充上下文 - 用于 _fill_all_sections 函数"""
    processor: Any  # ExcelProcessor instance
    sections: List[Dict]
    keyword_info: Dict
    keyword_mapping: Dict
    top_keyword: str
    merge_rows: int = 2


@dataclass
class MatchResult:
    """匹配结果"""
    matched: bool
    row: Optional[int] = None
    col: Optional[int] = None
    method: Optional[str] = None  # 'b_column', 'a_column', etc.
    confidence: float = 0.0

    @staticmethod
    def success(row: int, col: int, method: str, confidence: float = 1.0) -> 'MatchResult':
        """创建成功结果"""
        return MatchResult(
            matched=True,
            row=row,
            col=col,
            method=method,
            confidence=confidence
        )

    @staticmethod
    def failure() -> 'MatchResult':
        """创建失败结果"""
        return MatchResult(matched=False)


@dataclass
class FillOptions:
    """填充选项"""
    is_special: bool = False
    merge_rows: int = 1
    target_col: Optional[int] = None
    overwrite: bool = True


@dataclass
class TopTableWarning:
    """顶表告警"""
    row: int
    field_name: str
    message: str
    severity: str = "warning"  # warning, error, info

    def __str__(self):
        return f"[{self.severity.upper()}] Row {self.row} - {self.field_name}: {self.message}"


@dataclass
class SubTablePosition:
    """子表位置信息"""
    keyword: str
    start_row: int
    end_row: int
    gap_before: int = 0
    gap_after: int = 0

    @property
    def total_rows(self) -> int:
        """包含间隔的总行数"""
        return self.end_row - self.start_row + 1 + self.gap_before + self.gap_after


@dataclass
class MatchConfig:
    """匹配配置"""
    enable_top_table: bool = True
    enable_b_column: bool = True
    enable_a_column: bool = True
    special_prefix: Optional[str] = None
    fuzzy_match: bool = False
    case_sensitive: bool = False

    @classmethod
    def from_dict(cls, config: Dict) -> 'MatchConfig':
        """从配置字典创建"""
        return cls(
            enable_top_table=config.get('enable_top_table', True),
            enable_b_column=config.get('enable_b_column', True),
            enable_a_column=config.get('enable_a_column', True),
            special_prefix=config.get('special_prefix'),
            fuzzy_match=config.get('fuzzy_match', False),
            case_sensitive=config.get('case_sensitive', False),
        )


@dataclass
class ProcessingStats:
    """处理统计"""
    total_fields: int = 0
    matched_fields: int = 0
    failed_fields: int = 0
    warnings_count: int = 0
    errors_count: int = 0

    @property
    def match_rate(self) -> float:
        """匹配率"""
        if self.total_fields == 0:
            return 0.0
        return self.matched_fields / self.total_fields

    @property
    def success_rate(self) -> float:
        """成功率（无错误）"""
        if self.total_fields == 0:
            return 0.0
        return (self.total_fields - self.errors_count) / self.total_fields

    def add_match(self, success: bool = True):
        """添加匹配记录"""
        self.total_fields += 1
        if success:
            self.matched_fields += 1
        else:
            self.failed_fields += 1

    def add_warning(self):
        """添加警告"""
        self.warnings_count += 1

    def add_error(self):
        """添加错误"""
        self.errors_count += 1

    def __str__(self):
        return (
            f"Stats: {self.matched_fields}/{self.total_fields} matched "
            f"({self.match_rate:.1%}), "
            f"{self.warnings_count} warnings, {self.errors_count} errors"
        )
