# Config Parser Plugin

配置解析插件 - 从日志文件中解析配置块

## 功能

解析日志文件，提取结构化的配置信息，包括：
- 配置块名称和字段
- 顶格配置（Top Config）
- 子表配置（Sub Tables）

## 配置

```yaml
config_parser:
  enable: true
  # 无需额外配置，自动解析日志格式
```

## 依赖

- **Level**: 1 (解析层)
- **Dependencies**: 无
- **被依赖**: `excel_writer`, `constraint_checker`, `auto_filename`

作为第一层插件，为其他所有插件提供解析后的配置数据。

## 命令行使用

```bash
# 基本用法
python main.py template.xlsx log.txt

# 内部自动调用 config_parser 解析日志
# 无需手动指定
```

## 日志格式

支持的日志格式：

```
[Section1]
field1 = value1
field2 = value2

[Section2]
field3 = value3
```

## 输出格式

解析后的数据结构：

```python
{
    "sections": [
        {
            "name": "Section1",
            "fields": {
                "field1": "value1",
                "field2": "value2"
            }
        },
        {
            "name": "Section2",
            "fields": {
                "field3": "value3"
            }
        }
    ],
    "parser": ConfigParser实例
}
```

## 与其他插件的配合

### 工作流位置

```
[config_parser] → excel_writer → auto_filename → constraint_checker
      ↓
   解析日志
   提供sections
```

### 数据流

1. **config_parser**: 解析日志文件
   ```
   log.txt → sections列表
   ```

2. **excel_writer**: 使用sections填充Excel
   ```
   sections + template → filled Excel
   ```

3. **constraint_checker**: 使用sections进行约束检查
   ```
   sections → 检查规则 → 违规报告
   ```

### 配合示例

```python
# config_parser 输出
context = {
    "config_parser": {
        "sections": [...],
        "parser": parser_instance
    }
}

# excel_writer 使用
sections = context["config_parser"]["sections"]

# constraint_checker 使用
sections = context["config_parser"]["sections"]
parser = context["config_parser"]["parser"]
```

## 示例输出

```
[配置解析] 开始解析日志...
  ✓ 解析完成: 5个配置块
  - opSch (顶表)
  - I2C (子表)
  - SPI (子表)
  - UART (子表)
  - GPIO (子表)
```

## 方法

### group_by_top_config()

将配置块按顶格配置分组：

```python
parser = context["config_parser"]["parser"]
groups = parser.group_by_top_config("opSch")

# 返回结构
[
    {
        "top": {"name": "opSch", "fields": {...}},
        "subs": [
            {"name": "I2C", "fields": {...}},
            {"name": "SPI", "fields": {...}}
        ]
    }
]
```

### get_field_value()

获取指定字段的值：

```python
value = parser.get_field_value("opSch", "powerLevel")
# 返回: "5" 或 None
```

## 扩展

支持自定义日志解析器：

```python
class CustomConfigParser(ConfigParser):
    def parse_log(self, log_file):
        # 自定义解析逻辑
        pass
```

## 常见问题

**Q: 支持哪些日志格式？**
A: 支持标准的 `[Section]` 和 `key=value` 格式。

**Q: 如何处理多个相同名称的配置块？**
A: 所有同名配置块都会被保留，用于支持重复的子表配置。

**Q: 解析失败怎么办？**
A: 检查日志文件格式是否正确，确保使用正确的编码（UTF-8）。
