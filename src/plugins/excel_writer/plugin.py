"""
Excel写入插件 - 将配置信息写入Excel模板
"""

import os
import re
import sys
from copy import copy

import yaml
from openpyxl import load_workbook
from openpyxl.cell.cell import MergedCell

from src.plugins.base import Plugin, get_target_column


class ExcelWriterPlugin(Plugin):
    """Excel写入插件 - Level 2 (Processor)"""

    level = 2  # 处理层
    dependencies = ["config_extractor"]  # 依赖配置提取插件

    def execute(self, context: dict) -> dict:
        """将配置信息写入Excel模板

        Args:
            context: 上下文字典，需要包含：
                - excel_file: Excel模板文件路径
                - output_file: 输出文件路径（可选）
                - sheet_name: 工作表名称（可选）
                - config_extractor.sections: 配置块列表
                - config_extractor.parser: LogParser实例

        Returns:
            {
                'output_file': 输出文件路径,
                'processor': ExcelProcessor实例（供小插件使用）,
                'workbook': openpyxl Workbook对象
            }
        """
        # 获取输入参数
        excel_file = context.get("excel_file")
        output_file = context.get("output_file")
        sheet_name = context.get("sheet_name")

        if not excel_file:
            raise ValueError("excel_writer: context 中缺少 'excel_file'")

        # 获取 config_extractor 的输出
        config_data = context.get("config_extractor", {})
        sections = config_data.get("sections", [])
        parser = config_data.get("parser")

        if not sections or not parser:
            raise ValueError("excel_writer: 需要 config_extractor 的输出数据")

        print(f"[Excel写入] 加载模板: {excel_file}")

        # 检查是否有多个TopConfig（多工作表模式）
        enable_top_table = self.config.get("top_table", {}).get("enable", True)
        if enable_top_table:
            top_keyword = self.config.get("top_table", {}).get("log_keyword", "opSch")
            groups = parser.group_by_top_config(top_keyword)
            num_top_configs = len(groups)

            if num_top_configs > 1:
                print(
                    f"[Excel写入] 检测到 {num_top_configs} 个 TopConfig，使用多工作表模式"
                )
                return self._process_multi_sheets(
                    excel_file, output_file, sheet_name, sections, groups
                )
            elif num_top_configs == 1:
                print("[Excel写入] 检测到 1 个 TopConfig，使用单工作表模式")
            else:
                print("[Excel写入] 未检测到 TopConfig")

        # 单工作表模式
        return self._process_single_sheet(
            excel_file, output_file, sheet_name, sections, parser
        )

    def _process_single_sheet(
        self, excel_file, output_file, sheet_name, sections, parser
    ):
        """单工作表处理模式"""
        # 加载Excel
        processor = ExcelProcessor(excel_file, sheet_name, self.config)
        print(f"[Excel写入] 使用工作表: {processor.sheet.title}")

        # 处理顶格表格
        enable_top_table = self.config.get("top_table", {}).get("enable", True)
        if enable_top_table:
            top_keyword = self.config.get("top_table", {}).get("log_keyword", "opSch")
            top_section = parser.get_top_section(top_keyword)
            if top_section:
                start_row, end_row = processor.find_top_table()
                if start_row:
                    matched = processor.match_and_fill_top_table(
                        top_section, start_row, end_row
                    )
                    print(f"[Excel写入] ✓ 顶格表格: 匹配 {len(matched)} 个字段")
                else:
                    print("[Excel写入] ✗ 未找到顶格表格")
            else:
                print(f"[Excel写入] ✗ 日志中未找到 {top_keyword}")

        # 处理子表
        self._process_sub_sections(processor, sections)

        # 生成输出文件名
        if not output_file:
            base_name = os.path.splitext(excel_file)[0]
            output_file = f"{base_name}_processed.xlsx"

        # 保存文件
        processor.save(output_file)
        print(f"[Excel写入] ✓ 保存完成: {output_file}")

        return {"output_file": output_file, "processor": processor}

    def _process_multi_sheets(
        self, excel_file, output_file, sheet_name, sections, groups
    ):
        """多工作表处理模式"""
        workbook, template_sheet, template_name = self._setup_multi_sheets_workbook(
            excel_file, sheet_name, len(groups)
        )

        created_sheets, first_processor = self._create_all_sheets(
            workbook, template_sheet, groups
        )

        output_file = self._finalize_multi_sheets(
            workbook,
            template_name,
            excel_file,
            output_file,
            created_sheets,
            first_processor,
        )

        return {
            "output_file": output_file,
            "processor": first_processor,
            "workbook": workbook,
            "created_sheets": created_sheets,
        }

    def _setup_multi_sheets_workbook(self, excel_file, sheet_name, num_groups):
        """设置多工作表工作簿"""
        workbook = load_workbook(excel_file)

        if sheet_name and sheet_name in workbook.sheetnames:
            template_sheet = workbook[sheet_name]
        else:
            template_sheet = workbook.active

        template_name = template_sheet.title
        print(f"[Excel写入] 模板工作表: {template_name}")
        print(f"[Excel写入] 创建 {num_groups} 个工作表...")

        return workbook, template_sheet, template_name

    def _create_all_sheets(self, workbook, template_sheet, groups):
        """为所有组创建工作表"""
        created_sheets = []
        first_processor = None

        for idx, group in enumerate(groups, 1):
            processor, sheet_title = self._process_group_to_sheet(
                workbook, template_sheet, group, idx, len(groups)
            )
            created_sheets.append((sheet_title, processor))

            if idx == 1:
                first_processor = processor

        return created_sheets, first_processor

    def _process_group_to_sheet(self, workbook, template_sheet, group, idx, total):
        """处理单个组到工作表"""
        top_section = group["top"]
        sub_sections = group["subs"]

        sheet_title = self._generate_sheet_name(top_section, idx)
        new_sheet = workbook.copy_worksheet(template_sheet)
        new_sheet.title = sheet_title

        processor = ExcelProcessor(workbook, new_sheet, self.config)

        enable_top_table = self.config.get("top_table", {}).get("enable", True)
        if enable_top_table:
            start_row, end_row = processor.find_top_table()
            if start_row:
                matched = processor.match_and_fill_top_table(
                    top_section, start_row, end_row
                )
                print(f"  [{idx}/{total}] {sheet_title}: 顶格表格 {len(matched)} 字段")

        self._process_sub_sections(processor, sub_sections)
        print(f"  [{idx}/{total}] {sheet_title}: 处理了 {len(sub_sections)} 个子表")

        return processor, sheet_title

    def _finalize_multi_sheets(
        self,
        workbook,
        template_name,
        excel_file,
        output_file,
        created_sheets,
        first_processor,
    ):
        """完成多工作表处理"""
        if template_name in workbook.sheetnames:
            del workbook[template_name]

        if not output_file:
            base_name = os.path.splitext(excel_file)[0]
            output_file = f"{base_name}_multi_sheets.xlsx"

        workbook.save(output_file)
        print(f"[Excel写入] ✓ 保存完成: {output_file}")
        print(f"[Excel写入] 工作表数量: {len(created_sheets)}")

        return output_file

    def _process_sub_sections(self, processor, sections):
        """处理子表部分"""
        keyword_mapping = self.config.get("keyword_mapping", {})
        top_keyword = self.config.get("top_table", {}).get("log_keyword", "opSch")
        merge_rows = self.config.get("special_prefix", {}).get("merge_rows", 2)

        keyword_info = self._scan_sub_table_positions(processor, keyword_mapping)
        self._fill_all_sections(
            processor, sections, keyword_info, keyword_mapping, top_keyword, merge_rows
        )
        self._cleanup_unused_sub_tables(processor, keyword_info)

    def _scan_sub_table_positions(self, processor, keyword_mapping):
        """扫描所有子表的原始位置"""
        keyword_info = {}
        for excel_keyword in keyword_mapping.keys():
            start_row, end_row = processor.find_sub_table(excel_keyword)
            if start_row:
                keyword_info[excel_keyword] = {
                    "orig_start": start_row,
                    "orig_end": end_row,
                    "count": 0,
                    "used": False,
                }
        return keyword_info

    def _fill_all_sections(
        self,
        processor,
        sections,
        keyword_info,
        keyword_mapping,
        top_keyword,
        merge_rows,
    ):
        """填充所有配置块到子表"""
        global_last_row = processor.sheet.max_row

        for section in sections:
            if section["name"] == top_keyword:
                continue

            matched_keyword = self._find_matching_keyword(
                section["name"], keyword_mapping
            )
            if not matched_keyword or matched_keyword not in keyword_info:
                continue

            global_last_row = self._fill_section_to_sub_table(
                processor,
                section,
                keyword_info[matched_keyword],
                global_last_row,
                merge_rows,
            )

        return global_last_row

    def _find_matching_keyword(self, section_name, keyword_mapping):
        """查找匹配的Excel关键词"""
        for excel_keyword, log_pattern in keyword_mapping.items():
            if re.match(log_pattern, section_name):
                return excel_keyword
        return None

    def _fill_section_to_sub_table(
        self, processor, section, info, global_last_row, merge_rows
    ):
        """填充配置块到子表"""
        if info["count"] == 0:
            processor.match_and_fill_sub_table(
                section, info["orig_start"], info["orig_end"]
            )
            info["count"] += 1
            info["used"] = True
            return global_last_row

        template_height = info["orig_end"] - info["orig_start"] + 1
        new_start = global_last_row + merge_rows
        new_end = new_start + template_height - 1

        processor.copy_sub_table(info["orig_start"], info["orig_end"], new_start)
        processor.match_and_fill_sub_table(section, new_start, new_end)
        info["count"] += 1

        return new_end

    def _cleanup_unused_sub_tables(self, processor, keyword_info):
        """清理未使用的子表"""
        rows_to_delete = [
            (info["orig_start"], info["orig_end"])
            for info in keyword_info.values()
            if not info["used"]
        ]

        if not rows_to_delete:
            return

        rows_to_delete.sort(reverse=True)
        for start_row, end_row in rows_to_delete:
            num_rows = end_row - start_row + 1
            processor.sheet.delete_rows(start_row, num_rows)

        processor.normalize_subtable_spacing()

    def _generate_sheet_name(self, top_section, index):
        """生成工作表名称"""
        # 尝试加载 auto_filename 插件配置
        try:
            auto_filename_config_path = os.path.join(
                os.path.dirname(__file__), "..", "auto_filename", "config.yaml"
            )
            if os.path.exists(auto_filename_config_path):
                with open(auto_filename_config_path, "r", encoding="utf-8") as f:
                    auto_filename_config = yaml.safe_load(f) or {}
            else:
                auto_filename_config = {}
        except Exception:
            auto_filename_config = {}

        if auto_filename_config.get("enable", False):
            filename_fields = auto_filename_config.get("fields", [])
            filename_value_mapping = auto_filename_config.get("value_mapping", {})

            if filename_fields:
                name_parts = []
                for field_name in filename_fields[:2]:  # 只用前2个字段
                    if field_name in top_section["fields"]:
                        value = top_section["fields"][field_name]
                        # 应用映射
                        if field_name in filename_value_mapping:
                            field_mapping = filename_value_mapping[field_name]
                            value_str = str(value).strip()
                            if value_str in field_mapping:
                                value = field_mapping[value_str]
                        name_parts.append(str(value))

                if name_parts:
                    sheet_name = f"Config_{index}_{'_'.join(name_parts)}"
                    # Excel工作表名称限制：31字符
                    if len(sheet_name) > 31:
                        sheet_name = sheet_name[:28] + "..."
                    return sheet_name

        # 默认使用序号
        return f"Config_{index}"


# ==================== 内部类和工具函数 ====================


class ExcelProcessor:
    """处理Excel表格的读取、匹配和填充"""

    def __init__(self, excel_file_or_workbook, sheet_name_or_sheet=None, config=None):
        """
        初始化ExcelProcessor

        Args:
            excel_file_or_workbook: Excel文件路径 或 openpyxl Workbook对象
            sheet_name_or_sheet: 工作表名称 或 openpyxl Worksheet对象
            config: 配置字典
        """
        self.warnings = []  # 存储告警信息
        self.config = config or {}

        # 判断是文件路径还是Workbook对象
        if isinstance(excel_file_or_workbook, str):
            # 文件路径模式
            self.excel_file = excel_file_or_workbook
            self.wb = load_workbook(excel_file_or_workbook)
            self.sheet = (
                self.wb[sheet_name_or_sheet] if sheet_name_or_sheet else self.wb.active
            )
        else:
            # Workbook对象模式
            self.excel_file = None
            self.wb = excel_file_or_workbook
            self.sheet = sheet_name_or_sheet if sheet_name_or_sheet else self.wb.active

    def get_cell_value_smart(self, row, col):
        """智能获取单元格值，处理合并单元格

        如果是MergedCell，找到合并区域的主单元格并返回其值

        Args:
            row: 行号（从1开始）
            col: 列号（从1开始）

        Returns:
            单元格的值，如果是MergedCell则返回主单元格的值
        """
        cell = self.sheet.cell(row, col)

        # 如果是普通单元格，直接返回值
        if not isinstance(cell, MergedCell):
            return cell.value

        # 如果是MergedCell，找到对应的合并区域
        for merged_range in self.sheet.merged_cells.ranges:
            if cell.coordinate in merged_range:
                # 获取合并区域的主单元格（左上角）
                min_row = merged_range.min_row
                min_col = merged_range.min_col
                master_cell = self.sheet.cell(min_row, min_col)
                return master_cell.value

        # 如果没有找到合并区域（不应该发生），返回None
        return None

    def copy_cell_style(self, source_cell, target_cell):
        """复制单元格样式"""
        if source_cell.has_style:
            target_cell.font = copy(source_cell.font)
            target_cell.border = copy(source_cell.border)
            target_cell.fill = copy(source_cell.fill)
            target_cell.number_format = copy(source_cell.number_format)
            target_cell.protection = copy(source_cell.protection)
            target_cell.alignment = copy(source_cell.alignment)

    def normalize_subtable_spacing(self):
        """规范化所有子表之间的空行"""
        keyword_mapping = self.config.get("keyword_mapping", {})
        subtable_positions = self._find_all_subtable_positions(keyword_mapping)

        if len(subtable_positions) <= 1:
            return

        self._adjust_all_subtable_gaps(subtable_positions)

    def _find_all_subtable_positions(self, keyword_mapping):
        """查找所有子表的位置"""
        subtable_positions = []
        row = 1

        while row <= self.sheet.max_row:
            cell_a = self.sheet.cell(row, 1).value
            if cell_a and any(
                keyword in str(cell_a) for keyword in keyword_mapping.keys()
            ):
                start_row, end_row = self._find_subtable_end(row, keyword_mapping)
                subtable_positions.append((start_row, end_row))
                row = end_row + 1
            else:
                row += 1

        return subtable_positions

    def _find_subtable_end(self, start_row, keyword_mapping):
        """查找子表的结束行"""
        end_row = start_row

        for check_row in range(
            start_row + 1, min(start_row + 20, self.sheet.max_row + 1)
        ):
            cell_check_a = self.sheet.cell(check_row, 1).value

            if cell_check_a and any(
                keyword in str(cell_check_a) for keyword in keyword_mapping.keys()
            ):
                break

            if self._row_has_data(check_row):
                end_row = check_row

        return start_row, end_row

    def _row_has_data(self, row):
        """检查行是否有数据"""
        cell_b = self.sheet.cell(row, 2).value
        cell_c = self.sheet.cell(row, 3).value
        cell_d = self.sheet.cell(row, 4).value
        return cell_b or cell_c or cell_d

    def _adjust_all_subtable_gaps(self, subtable_positions):
        """调整所有子表之间的间隙"""
        for i in range(len(subtable_positions) - 1, 0, -1):
            _, prev_end = subtable_positions[i - 1]
            current_start, _ = subtable_positions[i]
            gap = current_start - prev_end - 1

            if gap < 1:
                self._insert_gap(prev_end, subtable_positions, i)
            elif gap > 1:
                self._remove_excess_gap(prev_end, gap, subtable_positions, i)

    def _insert_gap(self, prev_end, subtable_positions, from_index):
        """插入空行"""
        self.sheet.insert_rows(prev_end + 1, 1)
        print(f"    ✓ 在第{prev_end}行后插入空行")

        for j in range(from_index, len(subtable_positions)):
            old_start, old_end = subtable_positions[j]
            subtable_positions[j] = (old_start + 1, old_end + 1)

    def _remove_excess_gap(self, prev_end, gap, subtable_positions, from_index):
        """删除多余空行"""
        rows_to_delete = gap - 1
        delete_start = prev_end + 2

        self.sheet.delete_rows(delete_start, rows_to_delete)
        print(f"    ✓ 删除多余空行（第{delete_start}行开始，共{rows_to_delete}行）")

        for j in range(from_index, len(subtable_positions)):
            old_start, old_end = subtable_positions[j]
            subtable_positions[j] = (
                old_start - rows_to_delete,
                old_end - rows_to_delete,
            )

    def find_top_table(self):
        """查找顶格表格的起始和结束行（顶格表格从第1行开始，无需关键字）"""
        keyword_mapping = self.config.get("keyword_mapping", {})
        start_row = self.config.get("top_table", {}).get("start_row", 1)

        # 查找结束行（遇到空行或子片段关键字）
        end_row = start_row
        for row in range(start_row, self.sheet.max_row + 1):
            # 检查前3列是否都为空（空行）
            if all(self.sheet.cell(row, col).value is None for col in range(1, 4)):
                end_row = row - 1
                break

            # 检查是否遇到子片段关键字（A列）
            first_cell = self.sheet.cell(row, 1).value
            if first_cell and str(first_cell).strip() in keyword_mapping:
                end_row = row - 1
                break

            end_row = row

        # 确保至少有一行
        if end_row < start_row:
            return None, None

        return start_row, end_row

    def find_sub_table(self, keyword):
        """查找子片段表格的起始和结束行"""
        keyword_mapping = self.config.get("keyword_mapping", {})
        start_row = None

        # 查找关键字所在行
        for row in range(1, self.sheet.max_row + 1):
            cell_value = self.sheet.cell(row, 1).value
            if cell_value and str(cell_value).strip() == keyword:
                start_row = row
                break

        if not start_row:
            return None, None

        # 子表的结束行（遇到空行或新的关键字）
        end_row = start_row
        for row in range(start_row + 1, self.sheet.max_row + 1):
            # 检查A列和B列是否都为空
            if (
                self.sheet.cell(row, 1).value is None
                and self.sheet.cell(row, 2).value is None
            ):
                break
            # 检查是否遇到新的子片段关键字
            first_cell = self.sheet.cell(row, 1).value
            if first_cell and str(first_cell).strip() in keyword_mapping:
                break
            end_row = row

        return start_row, end_row

    def match_and_fill_top_table(self, log_section, start_row, end_row):
        """在顶格表格中匹配并填充数据"""
        target_col = get_target_column(self.config)
        special_prefix_merge_rows = self.config.get("special_prefix", {}).get(
            "merge_rows", 2
        )
        show_unmatched_warnings = self.config.get("matching", {}).get(
            "show_unmatched_warnings", True
        )

        matched_count = {}
        unmatched_fields = []
        special_prefix_no_match = []

        for field_name, field_value in log_section["fields"].items():
            match_info = self._find_match_row_top_table(
                field_name, start_row, end_row, special_prefix_no_match
            )

            if not match_info:
                unmatched_fields.append(field_name)
                continue

            row, is_special = match_info
            self._fill_cell_value(
                row, target_col, field_value, is_special, special_prefix_merge_rows
            )
            matched_count[field_name] = matched_count.get(field_name, 0) + 1

        self._record_top_table_warnings(
            special_prefix_no_match,
            unmatched_fields,
            show_unmatched_warnings,
            log_section,
            start_row,
            end_row,
        )

        return matched_count

    def _find_match_row_top_table(
        self, field_name, start_row, end_row, special_prefix_no_match
    ):
        """查找字段在顶格表格中的匹配行"""
        enable_partial_match = self.config.get("matching", {}).get(
            "enable_partial_match", True
        )
        special_prefix_for_b_column = self.config.get("special_prefix", {}).get(
            "for_b_column", []
        )
        field_name_lower = field_name.lower()

        for row in range(start_row, end_row + 1):
            a_col_value = self.get_cell_value_smart(row, 1)
            if not a_col_value:
                continue

            a_col_str = str(a_col_value).strip()
            is_special_prefix = any(
                a_col_str.startswith(prefix) for prefix in special_prefix_for_b_column
            )

            if is_special_prefix:
                match = self._try_match_b_column(
                    row,
                    field_name_lower,
                    enable_partial_match,
                    a_col_str,
                    field_name,
                    special_prefix_no_match,
                )
                if match:
                    return match
            else:
                match = self._try_match_a_column(
                    row, a_col_str, field_name_lower, enable_partial_match
                )
                if match:
                    return match

        return None

    def _try_match_b_column(
        self,
        row,
        field_name_lower,
        enable_partial_match,
        a_col_str,
        field_name,
        special_prefix_no_match,
    ):
        """尝试匹配B列（特殊前缀情况）"""
        b_col_value = self.get_cell_value_smart(row, 2)

        if b_col_value:
            b_col_str_lower = str(b_col_value).strip().lower()
            if b_col_str_lower == field_name_lower:
                return (row, True)
            if enable_partial_match and (
                field_name_lower in b_col_str_lower
                or b_col_str_lower in field_name_lower
            ):
                return (row, True)
        else:
            if row not in [info[0] for info in special_prefix_no_match]:
                special_prefix_no_match.append((row, a_col_str, field_name))

        return None

    def _try_match_a_column(
        self, row, a_col_str, field_name_lower, enable_partial_match
    ):
        """尝试匹配A列（普通情况）"""
        a_col_str_lower = a_col_str.lower()

        if a_col_str_lower == field_name_lower:
            return (row, False)
        if enable_partial_match and (
            field_name_lower in a_col_str_lower or a_col_str_lower in field_name_lower
        ):
            return (row, False)

        return None

    def _fill_cell_value(self, row, target_col, field_value, is_special, merge_rows):
        """填充单元格值"""
        if is_special and merge_rows > 1:
            merge_end_row = row + merge_rows - 1
            try:
                self.sheet.merge_cells(
                    start_row=row,
                    start_column=target_col,
                    end_row=merge_end_row,
                    end_column=target_col,
                )
            except ValueError:
                pass

        self.sheet.cell(row, target_col, value=field_value)

    def _record_top_table_warnings(
        self,
        special_prefix_no_match,
        unmatched_fields,
        show_warnings,
        log_section,
        start_row,
        end_row,
    ):
        """记录顶格表格的警告信息"""
        if special_prefix_no_match:
            unique_warnings = {}
            for row, a_col_val, field in special_prefix_no_match:
                key = (row, a_col_val)
                if key not in unique_warnings:
                    unique_warnings[key] = []
                unique_warnings[key].append(field)

            for (row, a_col_val), fields in unique_warnings.items():
                self.warnings.append(
                    f"⚠️  顶格表格特殊前缀B列匹配失败: 第{row}行 A列='{a_col_val}'，"
                    f"B列为空或不匹配字段 {fields}"
                )

        if unmatched_fields and show_warnings:
            section_name = log_section.get("name", "未知配置块")
            self.warnings.append(
                f"⚠️  顶格表格未匹配字段 ({section_name}): {unmatched_fields}"
            )
            self._suggest_field_mapping(
                unmatched_fields, start_row, end_row, is_sub_table=False
            )

    def _suggest_field_mapping(
        self, unmatched_fields, start_row, end_row, is_sub_table=False
    ):
        """
        为未匹配的字段提供映射建议
        检查Excel中的字段名，找出可能的匹配（部分匹配）
        """
        suggestions = []

        # 获取Excel中的所有字段名
        excel_fields = []
        # 顶格表和子表都只在B列搜索
        search_col = 2
        end_col = 2

        for row in range(start_row, end_row + 1):
            for col in range(search_col, end_col + 1):
                cell_value = self.sheet.cell(row, col).value
                if cell_value:
                    excel_fields.append(str(cell_value).strip())

        # 对每个未匹配的字段，查找可能的匹配
        for log_field in unmatched_fields:
            possible_matches = []
            for excel_field in excel_fields:
                # 检查是否有包含关系（子字符串）
                if (
                    log_field.lower() in excel_field.lower()
                    or excel_field.lower() in log_field.lower()
                ):
                    possible_matches.append(excel_field)

            if possible_matches:
                suggestions.append(f"    '{log_field}' 可能对应: {possible_matches}")

        if suggestions:
            table_type = "子表" if is_sub_table else "顶格表格"
            self.warnings.append(
                f"💡 {table_type}字段映射建议（可在FIELD_NAME_MAPPING中配置）:"
            )
            self.warnings.extend(suggestions)

    def match_and_fill_sub_table(self, log_section, start_row, end_row):
        """在子片段表格中匹配并填充数据（列1匹配）"""
        target_col = get_target_column(self.config)
        enable_partial_match = self.config.get("matching", {}).get(
            "enable_partial_match", True
        )
        show_unmatched_warnings = self.config.get("matching", {}).get(
            "show_unmatched_warnings", True
        )

        matched_count = {}
        unmatched_fields = []

        for field_name, field_value in log_section["fields"].items():
            match_rows = []
            field_name_lower = field_name.lower()  # 转小写用于比较

            # 在B列（列1，因为A列是关键字）搜索字段名
            for row in range(start_row, end_row + 1):
                cell_value = self.sheet.cell(row, 2).value  # B列
                if cell_value:
                    cell_str = str(cell_value).strip()
                    cell_str_lower = cell_str.lower()  # 转小写比较

                    # 精确匹配（不区分大小写）
                    if cell_str_lower == field_name_lower:
                        match_rows.append(row)
                    # 部分匹配（不区分大小写）
                    elif enable_partial_match and (
                        field_name_lower in cell_str_lower
                        or cell_str_lower in field_name_lower
                    ):
                        match_rows.append(row)

            # 检查是否匹配
            if not match_rows:
                unmatched_fields.append(field_name)
                continue

            # 检查重复匹配
            if len(match_rows) > 1:
                self.warnings.append(
                    f"⚠️  子表重复匹配: 字段'{field_name}' 在第 {match_rows} 行都出现了"
                )

            # 填充数据
            for row in match_rows:
                self.sheet.cell(row, target_col, value=field_value)
                matched_count[field_name] = matched_count.get(field_name, 0) + 1

        # 记录未匹配字段
        if unmatched_fields and show_unmatched_warnings:
            section_name = log_section.get("name", "未知配置块")
            self.warnings.append(
                f"⚠️  子表未匹配字段 ({section_name}): {unmatched_fields}"
            )
            # 检查是否有字段名映射建议
            self._suggest_field_mapping(
                unmatched_fields, start_row, end_row, is_sub_table=True
            )

        return matched_count

    def copy_sub_table(self, start_row, end_row, insert_after_row):
        """复制子片段表格到指定位置"""
        # 插入空行
        self.sheet.insert_rows(insert_after_row + 1, 1)
        insert_after_row += 1

        # 复制表格行
        table_rows = end_row - start_row + 1
        self.sheet.insert_rows(insert_after_row + 1, table_rows)

        # 复制数据和样式
        for offset in range(table_rows):
            source_row = start_row + offset
            target_row = insert_after_row + 1 + offset

            for col in range(1, self.sheet.max_column + 1):
                source_cell = self.sheet.cell(source_row, col)
                target_cell = self.sheet.cell(target_row, col)

                # 跳过MergedCell（合并单元格的非主单元格）
                if isinstance(target_cell, MergedCell):
                    continue

                # 复制值
                if not isinstance(source_cell, MergedCell):
                    target_cell.value = source_cell.value

                # 复制样式
                self.copy_cell_style(source_cell, target_cell)

        # 复制合并单元格区域
        for merged_range in list(self.sheet.merged_cells.ranges):
            # 检查是否在源表格范围内
            if merged_range.min_row >= start_row and merged_range.max_row <= end_row:
                # 计算目标位置的合并范围
                offset = insert_after_row + 1 - start_row
                new_min_row = merged_range.min_row + offset
                new_max_row = merged_range.max_row + offset
                new_min_col = merged_range.min_col
                new_max_col = merged_range.max_col

                # 添加新的合并单元格
                self.sheet.merge_cells(
                    start_row=new_min_row,
                    start_column=new_min_col,
                    end_row=new_max_row,
                    end_column=new_max_col,
                )

        return insert_after_row + table_rows

    def save(self, output_file):
        """保存Excel文件（增强版，带完整验证）"""
        print(f"\n{'=' * 60}")
        print("[保存文件]")
        print(f"{'=' * 60}")

        abs_path = self._prepare_output_path(output_file)
        if not self._ensure_output_directory(abs_path):
            return

        abs_path = self._handle_file_conflict(abs_path)
        self._perform_save(abs_path)

    def _prepare_output_path(self, output_file):
        """规范化并准备输出路径"""
        output_file = os.path.normpath(output_file)
        abs_path = os.path.abspath(output_file)

        print(f"目标文件: {output_file}")
        print(f"完整路径: {abs_path}")
        print(f"当前目录: {os.getcwd()}")

        return abs_path

    def _ensure_output_directory(self, abs_path):
        """确保输出目录存在"""
        output_dir = os.path.dirname(abs_path)
        if not output_dir:
            return True

        if os.path.exists(output_dir):
            print(f"✓ 目录已存在: {output_dir}")
            return True

        try:
            os.makedirs(output_dir)
            print(f"✓ 创建目录: {output_dir}")
            return True
        except Exception as e:
            print(f"✗ 创建目录失败: {e}")
            return False

    def _handle_file_conflict(self, abs_path):
        """处理文件占用冲突"""
        if not os.path.exists(abs_path):
            return abs_path

        try:
            temp_name = abs_path + ".tmp_test"
            os.rename(abs_path, temp_name)
            os.rename(temp_name, abs_path)
            print("✓ 文件可以覆盖")
            return abs_path
        except OSError:
            print("⚠️  文件可能被占用，使用新文件名")
            import time

            timestamp = time.strftime("%Y%m%d_%H%M%S")
            base, ext = os.path.splitext(abs_path)
            new_path = f"{base}_{timestamp}{ext}"
            print(f"新文件名: {new_path}")
            return new_path

    def _perform_save(self, abs_path):
        """执行保存并处理错误"""
        try:
            print("正在保存...")
            self.wb.save(abs_path)
            self._verify_and_report_success(abs_path)
        except PermissionError as e:
            self._print_permission_error(e)
        except Exception as e:
            self._print_general_error(e)

    def _verify_and_report_success(self, abs_path):
        """验证保存成功并报告"""
        if not os.path.exists(abs_path):
            self._print_file_not_found_error()
            return

        file_size = os.path.getsize(abs_path)
        print(f"\n{'=' * 60}")
        print("✅ 保存成功!")
        print(f"{'=' * 60}")
        print(f"文件位置: {abs_path}")
        print(f"文件大小: {file_size:,} 字节")

        self._try_open_in_explorer(abs_path)
        print(f"{'=' * 60}\n")

    def _try_open_in_explorer(self, abs_path):
        """尝试在资源管理器中打开（仅Windows）"""
        if sys.platform == "win32":
            try:
                import subprocess

                subprocess.Popen(f'explorer /select,"{abs_path}"')
                print("✓ 已在资源管理器中打开文件位置")
            except Exception:
                pass

    def _print_file_not_found_error(self):
        """打印文件未找到错误"""
        print(f"\n{'=' * 60}")
        print("✗ 保存失败!")
        print(f"{'=' * 60}")
        print("错误: 文件不存在于预期位置")
        print("请检查:")
        print("  1. 是否有目录写入权限")
        print("  2. 磁盘空间是否充足")
        print("  3. 路径是否正确")
        print(f"{'=' * 60}\n")

    def _print_permission_error(self, error):
        """打印权限错误"""
        print(f"\n{'=' * 60}")
        print("✗ 权限错误!")
        print(f"{'=' * 60}")
        print(f"错误: {error}")
        print("解决方案:")
        print("  1. 以管理员权限运行脚本")
        print("  2. 选择其他有权限的目录")
        print("  3. 关闭占用该文件的程序（如Excel）")
        print(f"{'=' * 60}\n")

    def _print_general_error(self, error):
        """打印一般错误"""
        print(f"\n{'=' * 60}")
        print("✗ 保存失败!")
        print(f"{'=' * 60}")
        print(f"错误: {error}")
        import traceback

        traceback.print_exc()
        print(f"{'=' * 60}\n")
