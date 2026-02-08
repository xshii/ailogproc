"""
自动文件名插件 - 根据顶格表格字段值自动生成文件名后缀
"""

import os

from src.plugins.base import Plugin, get_target_column


from src.utils import info, warning


class AutoFilenamePlugin(Plugin):
    """自动文件名小插件 - Level 4"""

    level = 4  # 小插件
    dependencies = ["excel_writer"]  # 依赖 excel_writer

    def execute(self, context: dict) -> dict:
        """根据顶格表格的字段值自动生成文件名后缀"""
        info("\n  生成自动文件名...")
        validation = self._validate_prerequisites(context)
        if not validation:
            return {}

        output_file, processor, excel_writer_config, top_start, top_end = validation

        field_values = self._extract_field_values(
            processor, excel_writer_config, top_start, top_end
        )

        if not field_values:
            warning("  ⚠️  未提取到任何字段值，使用原文件名")
            return {}

        new_filename = self._generate_new_filename(output_file, field_values)
        info(f"  ✓ 新文件名: {os.path.basename(new_filename)}")
        # 实际重命名文件
        if os.path.exists(output_file):
            os.rename(output_file, new_filename)
            info("  ✓ 文件已重命名")
        else:
            warning("  ⚠️  原文件不存在，无法重命名")
        return {"output_file": new_filename}

    def _validate_prerequisites(self, context):
        """验证前置条件"""
        excel_writer_output = context.get("excel_writer", {})
        output_file = excel_writer_output.get("output_file")
        processor = excel_writer_output.get("processor")

        if not output_file or not processor:
            return None

        fields = self.config.get("fields", [])
        if not fields:
            warning("  ⚠️  未配置fields，使用原文件名")
            return None

        excel_writer_config = context.get("excel_writer_config", {})
        enable_top_table = excel_writer_config.get("top_table", {}).get("enable", True)

        if not enable_top_table:
            warning("  ⚠️  顶格表格未启用，使用原文件名")
            return None

        top_start, top_end = processor.find_top_table()
        if not top_start:
            warning("  ⚠️  未找到顶格表格，使用原文件名")
            return None

        return output_file, processor, excel_writer_config, top_start, top_end

    def _extract_field_values(self, processor, excel_writer_config, top_start, top_end):
        """从顶格表格提取字段值"""
        fields = self.config.get("fields", [])
        value_mapping = self.config.get("value_mapping", {})
        default_value = self.config.get("default_value", None)
        target_col = get_target_column(excel_writer_config)
        special_prefix_for_b_column = excel_writer_config.get("special_prefix", {}).get(
            "for_b_column", []
        )

        field_values = []

        for field_name in fields:
            field_value = self._find_field_value(
                processor,
                field_name,
                top_start,
                top_end,
                target_col,
                special_prefix_for_b_column,
            )

            if field_value is None:
                warning(f"  ⚠️  字段 '{field_name}' 未找到或无值，跳过")
                continue

            mapped_value = self._apply_value_mapping(
                field_name, field_value, value_mapping, default_value
            )
            field_values.append(mapped_value)

        return field_values

    def _find_field_value(
        self, processor, field_name, start_row, end_row, target_col, special_prefixes
    ):
        """在顶格表格中查找字段值"""
        field_name_lower = field_name.lower()

        for row in range(start_row, end_row + 1):
            a_col_value = processor.get_cell_value_smart(row, 1)
            if not a_col_value:
                continue

            a_col_str = str(a_col_value).strip()
            is_special = any(a_col_str.startswith(p) for p in special_prefixes)

            if is_special:
                b_col_value = processor.get_cell_value_smart(row, 2)
                if b_col_value and str(b_col_value).strip().lower() == field_name_lower:
                    return processor.get_cell_value_smart(row, target_col)
            else:
                if a_col_str.lower() == field_name_lower:
                    return processor.get_cell_value_smart(row, target_col)

        return None

    def _apply_value_mapping(
        self, field_name, field_value, value_mapping, default_value
    ):
        """应用字段值映射"""
        field_value_str = str(field_value).strip()

        if field_name in value_mapping:
            field_mapping = value_mapping[field_name]
            if field_value_str in field_mapping:
                mapped_value = field_mapping[field_value_str]
                info(f"  ✓ {field_name}: {field_value_str} → {mapped_value}")
                return mapped_value

            if default_value:
                print(
                    f"  ⚠️  {field_name}: {field_value_str} → {default_value} (未映射)"
                )
                return default_value

            warning(f"  ⚠️  {field_name}: {field_value_str} (未映射，使用原值)")
            return field_value_str

        info(f"  ℹ️  {field_name}: {field_value_str} (无映射配置)")
        return field_value_str

    def _generate_new_filename(self, output_file, field_values):
        """生成新文件名"""
        suffix = "_" + "_".join(field_values)

        dir_name = os.path.dirname(output_file)
        base_name = os.path.basename(output_file)
        name_without_ext, ext = os.path.splitext(base_name)

        new_base_name = name_without_ext + suffix + ext
        return os.path.join(dir_name, new_base_name) if dir_name else new_base_name
