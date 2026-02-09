# 插件系统总览

完整的插件架构、依赖关系和使用指南。

---

## 📦 插件列表

### 配置日志处理 (5个插件)

| 插件 | Level | 功能 | 依赖 |
|------|-------|------|------|
| **dld_configtmp** | 0 | 下载最新模板 | - |
| **config_parser** | 1 | 解析配置日志 | - |
| **excel_writer** | 3 | 填充Excel模板 | config_parser |
| **auto_filename** | 4 | 生成文件名后缀 | excel_writer |
| **constraint_checker** | 2 | 检查配置约束 | config_parser |

### 性能日志处理 (4个插件)

| 插件 | Level | 功能 | 依赖 |
|------|-------|------|------|
| **perf_parser** | 1 | 解析性能日志 | - |
| **perf_analyzer** | 2 | 计算性能指标 | perf_parser |
| **perf_visualizer** | 3 | 生成可视化图表 | perf_parser, perf_analyzer |
| **data_parser** | 1 | 提取二进制数据 | - |

---

## 🔄 插件依赖关系

### 配置日志工作流

```
[dld_configtmp] (可选) → 下载模板
       ↓
[config_parser] → 解析日志 → sections
       ↓                          ↓
       ├─────────────────────────┤
       ↓                          ↓
[excel_writer] ← 填充模板   [constraint_checker] ← 检查约束
       ↓
[auto_filename] ← 重命名文件
```

### 性能日志工作流

```
[perf_parser] → 解析日志 → tasks
       ↓
[perf_analyzer] → 分析性能 → metrics
       ↓
[perf_visualizer] → 生成图表 → HTML

[data_parser] → 提取二进制 → binary files (独立流程)
```

---

## 💻 命令行使用

### 配置日志处理

```bash
# 基本使用
python main.py template.xlsx config.log

# 禁用自动文件名
python main.py template.xlsx config.log --no-auto-filename

# 仅检查约束（不填充Excel）
python main.py template.xlsx config.log --check-only

# 下载最新模板
python main.py --download-template config.log

# 完整流程
python main.py --download-template template.xlsx config.log -o output.xlsx
```

### 性能日志处理

```bash
# 基本使用
python main.py --mode perf performance.log

# 指定输出目录
python main.py --mode perf performance.log -o charts/

# 自定义图表
python main.py --mode perf performance.log --chart-title "系统性能"

# 仅分析（不生成图表）
python main.py --mode perf performance.log --no-visualize
```

### 数据解析（二进制提取）

```bash
# 基本使用
python main.py --mode data data.log

# Block模式（多个二进制）
python main.py --mode data data.log --block-mode

# 指定输出目录
python main.py --mode data data.log -o binaries/
```

---

## ⚙️ 配置示例

### 完整配置（config/default_config.yaml）

```yaml
# 模板下载（可选）
dld_configtmp:
  enable: false
  api_url: "https://api.example.com/templates/latest"

# 配置解析
config_parser:
  enable: true

# Excel填充
excel_writer:
  enable: true
  top_table:
    log_keyword: "opSch"
    target_column: 3
  keyword_mapping:
    i2c: "I2C"
    spi: "SPI"

# 自动文件名
auto_filename:
  enable: true
  fields:
    - powerLevel
    - deviceMode
  value_mapping:
    powerLevel:
      "5": "high"
      "3": "medium"

# 约束检查
constraint_checker:
  enable: true
  check_only: false
  generate_report: true
  active_version: "1.0.0_20240115"

# 性能解析
perf_parser:
  enable: true

# 性能分析
perf_analyzer:
  enable: true
  metrics:
    - duration
    - concurrency
    - bottleneck

# 性能可视化
perf_visualizer:
  enable: true
  output_format: "html"
  gantt:
    title: "性能时间线"
    color_by: "unit"

# 数据解析
data_parser:
  enable: true
  mode: "block"
  fields:
    - name: type
      type: uint8
      offset: 0
```

---

## 🎯 使用场景

### 场景1: 配置文件生成与验证

```bash
# 1. 解析配置日志
# 2. 填充Excel模板
# 3. 自动生成文件名
# 4. 检查配置约束
python main.py template.xlsx config.log

# 输出:
# output_5_auto.xlsx (自动命名)
# constraint_report.json (约束检查报告)
```

### 场景2: 性能分析与可视化

```bash
# 1. 解析性能日志
# 2. 计算性能指标
# 3. 生成时间线图表
python main.py --mode perf performance.log

# 输出:
# output/timeline.html (交互式图表)
```

### 场景3: CI/CD集成

```bash
#!/bin/bash
# CI/CD脚本

# 下载最新模板
python main.py --download-template config.log || exit 1

# 生成并验证配置
python main.py template.xlsx config.log --check-only || exit 1

# 如果验证通过，生成最终文件
python main.py template.xlsx config.log -o release/config.xlsx
```

### 场景4: 批量处理

```bash
# 处理多个配置文件
for log in logs/*.txt; do
    output="output/$(basename $log .txt).xlsx"
    python main.py template.xlsx "$log" -o "$output"
done
```

---

## 🔌 插件开发指南

### 创建新插件

1. **继承基类**

```python
from src.plugins.base import Plugin

class MyPlugin(Plugin):
    level = 3  # 执行层级
    dependencies = ["other_plugin"]  # 依赖的插件

    def execute(self, context: dict) -> dict:
        # 插件逻辑
        return {"my_result": "value"}
```

2. **注册插件**

```python
# src/plugins/__init__.py
from src.plugins.my_plugin.plugin import MyPlugin

PLUGINS = {
    "my_plugin": MyPlugin,
    # ...
}
```

3. **添加配置**

```yaml
# config/default_config.yaml
my_plugin:
  enable: true
  # 插件配置
```

4. **编写测试**

```python
# tests/plugins/my_plugin/test_plugin.py
def test_my_plugin():
    plugin = MyPlugin(config)
    result = plugin.execute(context)
    assert result["my_result"] == "expected"
```

5. **添加文档**

创建 `src/plugins/my_plugin/README.md`

---

## 📊 插件执行顺序

插件按 **Level** 排序执行：

```
Level 0: dld_configtmp (预处理)
         ↓
Level 1: config_parser, perf_parser, data_parser (解析层)
         ↓
Level 2: constraint_checker, perf_analyzer (验证/分析层)
         ↓
Level 3: excel_writer, perf_visualizer (处理层)
         ↓
Level 4: auto_filename (后处理)
```

**依赖解析**: 自动根据 `dependencies` 调整执行顺序。

---

## 🛠️ 常见任务

### 禁用某个插件

```yaml
plugin_name:
  enable: false
```

### 调试某个插件

```bash
# 启用调试日志
python main.py template.xlsx log.txt --log-level DEBUG
```

### 查看插件执行顺序

```bash
# 查看插件加载信息
python main.py template.xlsx log.txt --verbose
```

### 仅运行特定插件

```bash
# 只运行配置解析和Excel填充
python main.py template.xlsx log.txt --plugins config_parser,excel_writer
```

---

## 📚 详细文档

### 配置日志插件

- [Config Parser](../src/plugins/config_parser/README.md)
- [Excel Writer](../src/plugins/excel_writer/README.md)
- [Auto Filename](../src/plugins/auto_filename/README.md)
- [Constraint Checker](../src/plugins/constraint_checker/README.md)
- [DLD Config Tmp](../src/plugins/dld_configtmp/README.md)

### 性能日志插件

- [Perf Parser](../src/plugins/perf_parser/README.md)
- [Perf Analyzer](../src/plugins/perf_analyzer/README.md)
- [Perf Visualizer](../src/plugins/perf_visualizer/README.md)
- [Data Parser](../src/plugins/data_parser/README.md)

---

## ❓ 常见问题

**Q: 插件执行失败怎么办？**
A: 检查：
1. 依赖插件是否已启用
2. 配置是否正确
3. 查看错误日志

**Q: 如何跳过某个插件？**
A: 在配置中设置 `enable: false` 或使用 `--plugins` 指定要运行的插件。

**Q: 插件之间如何传递数据？**
A: 通过 `context` 字典，插件执行结果存储在 `context[plugin_name]` 中。

**Q: 可以自定义插件执行顺序吗？**
A: 通过设置 `level` 和 `dependencies` 来控制执行顺序。

---

**更新时间**: 2026-02-09
**插件总数**: 9个
**测试覆盖**: 316个测试 ✅
