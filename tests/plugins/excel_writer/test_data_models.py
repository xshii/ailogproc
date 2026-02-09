"""
测试 Excel Writer 数据模型
"""

from src.plugins.excel_writer.data_models import (
    BColumnMatchContext,
    CellFillContext,
    CellPosition,
    ColumnMatchContext,
    FillOptions,
    MatchConfig,
    MatchContext,
    MatchResult,
    ProcessingStats,
    SectionFillContext,
    SubTablePosition,
    TableRange,
    TopTableWarning,
    TopTableWarningContext,
)


class TestCellPosition:
    """测试 CellPosition"""

    def test_create(self):
        pos = CellPosition(row=5, col=3)
        assert pos.row == 5
        assert pos.col == 3

    def test_str(self):
        pos = CellPosition(row=10, col=20)
        assert str(pos) == "(10, 20)"


class TestTableRange:
    """测试 TableRange"""

    def test_create(self):
        range_ = TableRange(start_row=1, end_row=10)
        assert range_.start_row == 1
        assert range_.end_row == 10

    def test_row_count(self):
        range_ = TableRange(start_row=5, end_row=10)
        assert range_.row_count == 6

    def test_contains_row(self):
        range_ = TableRange(start_row=5, end_row=10)
        assert range_.contains_row(5) is True
        assert range_.contains_row(7) is True
        assert range_.contains_row(10) is True
        assert range_.contains_row(4) is False
        assert range_.contains_row(11) is False


class TestMatchContext:
    """测试 MatchContext"""

    def test_create(self):
        pos = CellPosition(row=5, col=3)
        ctx = MatchContext(
            worksheet=None,
            position=pos,
            field_name="test_field",
            field_value="test_value",
            sections=[],
        )
        assert ctx.row == 5
        assert ctx.col == 3
        assert ctx.field_name == "test_field"

    def test_with_options(self):
        pos = CellPosition(row=1, col=1)
        ctx = MatchContext(
            worksheet=None,
            position=pos,
            field_name="field",
            field_value="value",
            sections=[],
            options={"fuzzy": True},
        )
        assert ctx.options["fuzzy"] is True


class TestBColumnMatchContext:
    """测试 BColumnMatchContext"""

    def test_create(self):
        ctx = BColumnMatchContext(
            row=5,
            field_name="powerLevel",
            field_name_lower="powerlevel",
            a_col_str="***",
            enable_partial_match=True,
            special_prefix_no_match=[],
        )
        assert ctx.row == 5
        assert ctx.field_name == "powerLevel"
        assert ctx.field_name_lower == "powerlevel"
        assert ctx.a_col_str == "***"
        assert ctx.enable_partial_match is True

    def test_with_warning_list(self):
        warnings = [(3, "**", "field1")]
        ctx = BColumnMatchContext(
            row=10,
            field_name="test",
            field_name_lower="test",
            a_col_str="***test",
            enable_partial_match=False,
            special_prefix_no_match=warnings,
        )
        assert len(ctx.special_prefix_no_match) == 1
        assert ctx.special_prefix_no_match[0] == (3, "**", "field1")


class TestTopTableWarningContext:
    """测试 TopTableWarningContext"""

    def test_create(self):
        ctx = TopTableWarningContext(
            special_prefix_no_match=[],
            unmatched_fields=["field1", "field2"],
            show_warnings=True,
            log_section={"name": "opSch"},
            start_row=5,
            end_row=20,
        )
        assert ctx.show_warnings is True
        assert len(ctx.unmatched_fields) == 2
        assert ctx.log_section["name"] == "opSch"
        assert ctx.start_row == 5
        assert ctx.end_row == 20

    def test_with_special_prefix_warnings(self):
        warnings = [(10, "***", "test_field")]
        ctx = TopTableWarningContext(
            special_prefix_no_match=warnings,
            unmatched_fields=[],
            show_warnings=False,
            log_section={"name": "test"},
            start_row=1,
            end_row=30,
        )
        assert len(ctx.special_prefix_no_match) == 1
        assert ctx.special_prefix_no_match[0][0] == 10


class TestCellFillContext:
    """测试 CellFillContext"""

    def test_create_normal_cell(self):
        ctx = CellFillContext(row=5, col=3, value="test_value")
        assert ctx.row == 5
        assert ctx.col == 3
        assert ctx.value == "test_value"
        assert ctx.is_special is False
        assert ctx.merge_rows == 1

    def test_create_special_cell_with_merge(self):
        ctx = CellFillContext(
            row=10, col=2, value="merged_value", is_special=True, merge_rows=3
        )
        assert ctx.row == 10
        assert ctx.col == 2
        assert ctx.value == "merged_value"
        assert ctx.is_special is True
        assert ctx.merge_rows == 3


class TestColumnMatchContext:
    """测试 ColumnMatchContext"""

    def test_create_with_defaults(self):
        ctx = ColumnMatchContext(
            field_name="powerLevel", start_row=5, end_row=20, column=2
        )
        assert ctx.field_name == "powerLevel"
        assert ctx.start_row == 5
        assert ctx.end_row == 20
        assert ctx.column == 2
        assert ctx.enable_partial_match is True

    def test_create_without_partial_match(self):
        ctx = ColumnMatchContext(
            field_name="test",
            start_row=1,
            end_row=10,
            column=1,
            enable_partial_match=False,
        )
        assert ctx.enable_partial_match is False


class TestSectionFillContext:
    """测试 SectionFillContext"""

    def test_create_with_defaults(self):
        sections = [{"name": "I2C", "fields": {}}]
        keyword_info = {"I2C": {"start_row": 10, "end_row": 20}}
        ctx = SectionFillContext(
            processor=None,
            sections=sections,
            keyword_info=keyword_info,
            keyword_mapping={},
            top_keyword="opSch",
        )
        assert len(ctx.sections) == 1
        assert ctx.top_keyword == "opSch"
        assert ctx.merge_rows == 2

    def test_create_with_custom_merge_rows(self):
        ctx = SectionFillContext(
            processor=None,
            sections=[],
            keyword_info={},
            keyword_mapping={"i2c": "I2C"},
            top_keyword="test",
            merge_rows=5,
        )
        assert ctx.merge_rows == 5
        assert ctx.keyword_mapping["i2c"] == "I2C"


class TestMatchResult:
    """测试 MatchResult"""

    def test_success(self):
        result = MatchResult.success(row=5, col=3, method="b_column")
        assert result.matched is True
        assert result.row == 5
        assert result.col == 3
        assert result.method == "b_column"
        assert result.confidence == 1.0

    def test_success_with_confidence(self):
        result = MatchResult.success(row=5, col=3, method="fuzzy", confidence=0.8)
        assert result.confidence == 0.8

    def test_failure(self):
        result = MatchResult.failure()
        assert result.matched is False
        assert result.row is None
        assert result.col is None


class TestFillOptions:
    """测试 FillOptions"""

    def test_defaults(self):
        opts = FillOptions()
        assert opts.is_special is False
        assert opts.merge_rows == 1
        assert opts.overwrite is True

    def test_custom(self):
        opts = FillOptions(is_special=True, merge_rows=3, target_col=5)
        assert opts.is_special is True
        assert opts.merge_rows == 3
        assert opts.target_col == 5


class TestTopTableWarning:
    """测试 TopTableWarning"""

    def test_create(self):
        warning = TopTableWarning(
            row=5, field_name="test_field", message="Test warning"
        )
        assert warning.row == 5
        assert warning.severity == "warning"

    def test_str(self):
        warning = TopTableWarning(
            row=10, field_name="field", message="Missing value", severity="error"
        )
        assert "[ERROR]" in str(warning)
        assert "Row 10" in str(warning)


class TestSubTablePosition:
    """测试 SubTablePosition"""

    def test_create(self):
        pos = SubTablePosition(keyword="test", start_row=5, end_row=10)
        assert pos.keyword == "test"
        assert pos.start_row == 5
        assert pos.end_row == 10

    def test_total_rows(self):
        pos = SubTablePosition(
            keyword="test", start_row=5, end_row=10, gap_before=2, gap_after=1
        )
        assert pos.total_rows == 6 + 2 + 1


class TestMatchConfig:
    """测试 MatchConfig"""

    def test_defaults(self):
        config = MatchConfig()
        assert config.enable_top_table is True
        assert config.enable_b_column is True
        assert config.fuzzy_match is False

    def test_from_dict(self):
        config = MatchConfig.from_dict(
            {
                "enable_top_table": False,
                "fuzzy_match": True,
                "special_prefix": "***",
            }
        )
        assert config.enable_top_table is False
        assert config.fuzzy_match is True
        assert config.special_prefix == "***"

    def test_from_dict_with_defaults(self):
        config = MatchConfig.from_dict({})
        assert config.enable_top_table is True


class TestProcessingStats:
    """测试 ProcessingStats"""

    def test_initial(self):
        stats = ProcessingStats()
        assert stats.total_fields == 0
        assert stats.match_rate == 0.0

    def test_add_match_success(self):
        stats = ProcessingStats()
        stats.add_match(success=True)
        stats.add_match(success=True)
        assert stats.total_fields == 2
        assert stats.matched_fields == 2
        assert stats.match_rate == 1.0

    def test_add_match_failure(self):
        stats = ProcessingStats()
        stats.add_match(success=True)
        stats.add_match(success=False)
        assert stats.total_fields == 2
        assert stats.matched_fields == 1
        assert stats.failed_fields == 1
        assert stats.match_rate == 0.5

    def test_add_warning(self):
        stats = ProcessingStats()
        stats.add_warning()
        stats.add_warning()
        assert stats.warnings_count == 2

    def test_add_error(self):
        stats = ProcessingStats()
        stats.add_error()
        assert stats.errors_count == 1

    def test_success_rate(self):
        stats = ProcessingStats()
        stats.total_fields = 10
        stats.errors_count = 2
        assert stats.success_rate == 0.8

    def test_str(self):
        stats = ProcessingStats()
        stats.add_match(True)
        stats.add_match(True)
        stats.add_match(False)
        stats.add_warning()
        output = str(stats)
        assert "2/3" in output
        assert "1 warnings" in output
