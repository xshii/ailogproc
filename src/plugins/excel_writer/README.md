# Excel Writer Plugin

Excel填充插件 - 将配置数据填充到Excel模板

## 功能

根据解析后的配置数据，自动填充Excel模板：
- **顶格表格**：填充主配置信息
- **子表**：填充重复配置（如多个I2C、SPI配置）
- **智能匹配**：支持精确匹配和模糊匹配
- **特殊前缀**：处理 `***` 等特殊标记

## 配置

```yaml
excel_writer:
  enable: true

  top_table:
    log_keyword: "opSch"        # 顶表关键字
    target_column: 3            # 填充到第3列
    enable: true

  matching:
    enable_partial_match: true  # 启用模糊匹配

  special_prefix:
    for_b_column: ["***", "##"] # B列特殊前缀
    merge_rows: 2               # 合并行数

  keyword_mapping:
    i2c: "I2C"                  # 日志名 -> Excel名映射
    spi: "SPI"
```

## 依赖

- **Level**: 3 (处理层)
- **Dependencies**: `config_parser`
- **被依赖**: `auto_filename`, `constraint_checker`

## 命令行使用

```bash
# 基本用法
python main.py template.xlsx log.txt

# 指定输出文件
python main.py template.xlsx log.txt -o output.xlsx

# 禁用顶格表格填充
python main.py template.xlsx log.txt --no-top-table

# 仅填充顶表（不填充子表）
python main.py template.xlsx log.txt --top-table-only
```

## 数据模型

插件使用14个数据类来减少参数传递：

### 基础数据类
- `CellPosition`: 单元格位置
- `TableRange`: 表格范围
- `MatchResult`: 匹配结果
- `ProcessingStats`: 处理统计

### 专用数据类
- `BColumnMatchContext`: B列匹配上下文
- `CellFillContext`: 单元格填充上下文
- `ColumnMatchContext`: 列匹配上下文

详见 `data_models.py` 和 `docs/REFACTORING_GUIDE.md`。

## 与其他插件的配合

### 工作流位置

```
config_parser → [excel_writer] → auto_filename → constraint_checker
                      ↓
                 填充Excel模板
                 (顶表 + 子表)
```

### 插件依赖链

1. **config_parser**: 提供 `sections` 数据
2. **excel_writer**: 填充Excel模板
   - 读取sections
   - 匹配模板字段
   - 填充单元格
3. **auto_filename**: 从填充好的Excel提取字段值
4. **constraint_checker**: 检查填充后的数据

### 配合示例

```yaml
# 完整工作流配置
config_parser:
  enable: true

excel_writer:
  enable: true
  top_table:
    log_keyword: "opSch"
  keyword_mapping:
    i2c: "I2C"
    spi: "SPI"

auto_filename:
  enable: true
  fields: ["powerLevel", "mode"]

constraint_checker:
  enable: true
  active_version: "1.0.0_20240115"
```

## 匹配策略

### 1. 顶格表格匹配

```
A列          B列          C列(填充)
───────────────────────────────────
fieldName1   ────→      value1
***special   fieldName2  value2  (特殊前缀)
fieldName3   ────→      value3
```

### 2. 子表匹配

```
关键字行: I2C Configuration
───────────────────
fieldA  fieldB
───────────────────
value1  value2   ← 填充第一个I2C配置
value3  value4   ← 填充第二个I2C配置
```

### 3. 特殊前缀处理

```
A列        B列        C列
─────────────────────────
***mode    lowPower   5     ← 匹配B列，填充C列
                            并合并2行
```

## 示例输出

```
[Excel填充] 开始填充Excel...
  顶格表格:
    ✓ powerLevel: 5
    ✓ deviceMode: auto
    ✓ frequency: 2400
    匹配: 15/18 (83.3%)

  子表:
    ✓ I2C: 2个配置
    ✓ SPI: 1个配置
    ✓ UART: 1个配置

  ✓ Excel填充完成: output.xlsx
  ⚠️  3个字段未匹配: unknownField1, unknownField2, unknownField3
```

## 处理器类

### ExcelProcessor

核心处理类，包含32个方法：

**读取方法**:
- `get_cell_value_smart()`: 智能读取单元格
- `read_table_range()`: 读取表格范围

**匹配方法**:
- `match_field_in_top_table()`: 顶表字段匹配
- `_match_field_in_column()`: 列匹配
- `_try_match_b_column()`: B列匹配（特殊前缀）

**填充方法**:
- `fill_section()`: 填充配置块
- `_fill_cell_value()`: 填充单元格
- `merge_cells()`: 合并单元格

## 警告处理

插件会收集并报告以下警告：

1. **未匹配字段**: 日志中的字段在模板中找不到
2. **B列为空**: 特殊前缀行的B列为空
3. **子表未找到**: 配置的关键字在模板中不存在
4. **字段建议**: 自动建议可能的匹配字段

```
⚠️  顶格表格未匹配字段 (opSch): unknownField
  建议: 是否应为 'knownField'? (相似度: 0.85)
```

## 常见问题

**Q: 为什么有些字段没有填充？**
A: 检查以下情况：
1. 字段名是否完全匹配（不区分大小写）
2. 是否启用了模糊匹配 `enable_partial_match`
3. 查看警告信息中的建议

**Q: 如何处理重复的配置块？**
A: 使用子表功能，Excel模板中留足够的行数。

**Q: 特殊前缀 `***` 如何工作？**
A: A列是 `***`，匹配字段名在B列，值填充到C列，并可合并多行。

**Q: 如何自定义填充列？**
A: 修改 `top_table.target_column` 配置。
