# Auto Filename Plugin

自动文件名插件 - 根据顶格表格字段值自动生成输出文件名后缀

## 功能

根据Excel模板顶格表格中的指定字段值，自动为输出文件生成有意义的后缀名。

**示例**:
- 原文件: `output.xlsx`
- 字段值: `powerLevel=5, mode=auto`
- 新文件: `output_5_auto.xlsx`

## 配置

```yaml
auto_filename:
  enable: true
  fields:
    - powerLevel    # 要提取的字段名
    - mode
  value_mapping:    # 值映射（可选）
    powerLevel:
      "5": "high"
      "3": "medium"
  default_value: "unknown"  # 字段为空时的默认值
```

## 依赖

- **Level**: 4 (小插件)
- **Dependencies**: `excel_writer`

必须在 `excel_writer` 完成后执行，因为需要从已填充的Excel中提取字段值。

## 使用场景

1. **批量生成文件**: 自动为每个配置生成唯一文件名
2. **文件分类**: 通过文件名快速识别配置类型
3. **版本管理**: 文件名包含关键配置信息

## 行为

1. 从顶格表格提取指定字段的值
2. 应用值映射（如果配置）
3. 组合字段值生成后缀
4. 重命名输出文件

**注意**: 如果文件不存在或重命名失败，保持原文件名不变。

## 命令行使用

```bash
# 基本用法
python main.py template.xlsx log.txt

# 自动生成文件名后缀
python main.py template.xlsx log.txt -o output.xlsx
# → 生成: output_5_auto.xlsx (根据配置字段自动命名)

# 禁用自动文件名
python main.py template.xlsx log.txt --no-auto-filename
```

## 与其他插件的配合

### 工作流位置

```
config_parser → excel_writer → [auto_filename] → constraint_checker
     ↓              ↓                  ↓                 ↓
   解析日志      填充Excel        重命名文件         检查约束
```

### 插件依赖链

1. **config_parser** (Level 1): 解析日志，提取配置块
2. **excel_writer** (Level 3): 填充Excel模板
3. **auto_filename** (Level 4): 从填充好的Excel提取字段值，重命名文件
4. **constraint_checker** (Level 2): 对最终文件进行约束检查

### 配合示例

```yaml
# config/default_config.yaml
excel_writer:
  top_table:
    log_keyword: "opSch"

auto_filename:
  enable: true
  fields:
    - powerLevel  # 从顶表提取
    - deviceMode

constraint_checker:
  check_only: false
  generate_report: true
```

## 示例输出

```
[excel_writer] ✓ Excel填充完成
生成自动文件名...
  ✓ 提取字段: powerLevel=5, deviceMode=auto
  ✓ 新文件名: output_5_auto.xlsx
  ✓ 文件已重命名
[constraint_checker] 开始检查配置约束...
```

## 常见问题

**Q: 为什么文件名没有改变？**
A: 检查以下情况：
1. `auto_filename.enable` 是否为 `true`
2. 配置的字段是否存在于顶格表格
3. 字段值是否为空

**Q: 如何自定义文件名格式？**
A: 使用 `value_mapping` 将原始值映射为更友好的名称。

**Q: 可以提取子表字段吗？**
A: 不可以，auto_filename 只能提取顶格表格的字段。

