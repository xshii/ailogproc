# 插件依赖关系配置说明

## 概述

本项目采用**层级插件架构**，插件间通过 `level`（层级）和 `dependencies`（依赖）进行调度和协同。

## 依赖配置机制

### 1. 插件基类定义

所有插件继承自 `Plugin` 基类，定义了两个关键属性：

```python
class Plugin(ABC):
    # 插件层级（子类需要设置）
    level = 0  # 0=预处理, 1=提取层, 2=处理层, 3=小插件

    # 依赖的插件名列表（子类可选设置）
    dependencies = []
```

### 2. 插件声明依赖

每个插件在类定义中声明自己的 `level` 和 `dependencies`：

```python
class ConfigParserPlugin(Plugin):
    """Trace解析插件"""

    level = 1  # 提取层
    dependencies = ["dld_configtmp"]  # 依赖模板下载插件

    def execute(self, context: dict) -> dict:
        # 可以从 context 中获取 dld_configtmp 的输出
        template_path = context.get("dld_configtmp", {}).get("template_path")
        # ...
```

### 3. 插件注册表

所有插件在 `src/plugins/__init__.py` 中注册：

```python
PLUGIN_REGISTRY = {
    "dld_configtmp": DownloadTemplatePlugin,       # Level 0
    "config_parser": ConfigParserPlugin,           # Level 1
    "constraint_checker": ConstraintCheckerPlugin, # Level 2
    "excel_writer": ExcelWriterPlugin,             # Level 3
    "auto_filename": AutoFilenamePlugin,           # Level 4
}
```

**注意：** 注册键名（如 `"dld_configtmp"`）必须与 `dependencies` 中引用的名称一致。

## 当前插件依赖关系

### 依赖图

```
dld_configtmp (Level 0)
    ├──> config_parser (Level 1)
    │       └──> constraint_checker (Level 2)
    │               └──> excel_writer (Level 3)
    │                       └──> auto_filename (Level 4)
    └──> excel_writer (Level 3)
            └──> auto_filename (Level 4)
```

### 详细配置

| 插件 | Level | Dependencies | 说明 |
|------|-------|--------------|------|
| `dld_configtmp` | 0 | `[]` | 无依赖，最先执行 |
| `config_parser` | 1 | `["dld_configtmp"]` | 依赖模板下载 |
| `constraint_checker` | 2 | `["config_parser"]` | 依赖配置解析结果 |
| `excel_writer` | 3 | `["dld_configtmp", "config_parser", "constraint_checker"]` | 依赖模板、解析结果和约束检查 |
| `auto_filename` | 4 | `["excel_writer"]` | 依赖 Excel 写入结果 |

### 执行顺序

插件按以下顺序执行：

1. **Level 0**: `dld_configtmp` - 下载/准备模板
2. **Level 1**: `config_parser` - 解析 trace 文件
3. **Level 2**: `constraint_checker` - 检查配置约束
4. **Level 3**: `excel_writer` - 写入 Excel
5. **Level 4**: `auto_filename` - 自动重命名

## 依赖检查机制

### 运行时检查

在执行每个插件前，系统会检查其依赖是否满足：

```python
def _check_dependencies(plugin, context: dict) -> bool:
    """检查插件的依赖是否满足"""
    for dep in plugin.dependencies:
        if dep not in context:
            return False
    return True
```

### 检查逻辑

1. 遍历插件的 `dependencies` 列表
2. 检查每个依赖插件的输出是否在 `context` 中
3. 如果所有依赖都满足，返回 `True`；否则返回 `False`
4. 依赖未满足的插件会被跳过

### 示例

```python
# excel_writer 的依赖检查
plugin.dependencies = ["dld_configtmp", "config_parser"]

# context 中必须包含：
context = {
    "dld_configtmp": {
        "template_path": "/path/to/template.xlsx",
        ...
    },
    "config_parser": {
        "sections": [...],
        ...
    }
}

# 检查通过 ✅ 执行 excel_writer
```

## Context 传递机制

### Context 结构

`context` 是一个字典，包含：
- 初始输入（用户参数）
- 各插件的输出结果

```python
context = {
    # 初始输入
    "trace_file": "/path/to/trace.txt",
    "excel_file": "/path/to/template.xlsx",
    "output_file": "/path/to/output.xlsx",

    # 插件输出（插件名作为键）
    "dld_configtmp": {
        "template_path": "...",
        "version": "...",
    },
    "config_parser": {
        "sections": [...],
        "parser": <ConfigParser>,
    },
    "excel_writer": {
        "output_file": "...",
        "processor": <ExcelProcessor>,
    },
    "auto_filename": {
        "output_file": "...",  # 重命名后的文件
    }
}
```

### 插件访问依赖输出

插件通过 `context` 获取依赖插件的输出：

```python
def execute(self, context: dict) -> dict:
    # 获取 config_parser 的输出
    sections = context.get("config_parser", {}).get("sections", [])

    # 获取 dld_configtmp 的输出
    template_path = context.get("dld_configtmp", {}).get("template_path")

    # 使用依赖插件的输出
    # ...
```

## 添加新插件

### 步骤 1: 创建插件类

```python
# src/plugins/my_plugin/plugin.py
from src.plugins.base import Plugin

class MyPlugin(Plugin):
    level = 2  # 设置层级
    dependencies = ["config_parser"]  # 声明依赖

    def execute(self, context: dict) -> dict:
        # 获取依赖插件的输出
        sections = context.get("config_parser", {}).get("sections", [])

        # 执行插件逻辑
        result = self.do_something(sections)

        # 返回输出（会被合并到 context 中）
        return {
            "my_result": result
        }
```

### 步骤 2: 注册插件

```python
# src/plugins/__init__.py
from src.plugins.my_plugin import MyPlugin

PLUGIN_REGISTRY = {
    "dld_configtmp": DownloadTemplatePlugin,
    "config_parser": ConfigParserPlugin,
    "my_plugin": MyPlugin,  # 添加注册
    "excel_writer": ExcelWriterPlugin,
    "auto_filename": AutoFilenamePlugin,
}
```

### 步骤 3: 创建配置文件

```yaml
# src/plugins/my_plugin/config.yaml
enable: true

# 插件特定配置
option1: value1
option2: value2
```

### 步骤 4: 其他插件引用

如果其他插件需要依赖新插件：

```python
class AnotherPlugin(Plugin):
    level = 3
    dependencies = ["my_plugin"]  # 引用注册键名

    def execute(self, context: dict) -> dict:
        # 获取 my_plugin 的输出
        my_result = context.get("my_plugin", {}).get("my_result")
```

## 层级设计原则

### Level 定义

| Level | 名称 | 用途 | 示例 |
|-------|------|------|------|
| **0** | 预处理层 | 准备资源、下载文件 | `dld_configtmp` |
| **1** | 提取层 | 从输入提取信息 | `config_parser` |
| **2** | 处理层 | 处理和转换数据 | `excel_writer` |
| **3** | 小插件 | 轻量级收尾工作 | `auto_filename` |

### 设计建议

1. **Level 0**: 准备阶段，无需其他插件输出
2. **Level 1**: 数据提取，依赖 Level 0
3. **Level 2**: 核心处理，依赖 Level 0-1
4. **Level 3**: 收尾工作，依赖 Level 0-2

### 同级插件

- 同级插件之间**不应相互依赖**
- 同级插件执行顺序**不保证**
- 如果需要依赖关系，应使用不同 Level

## 调试依赖问题

### 启用调试日志

```bash
python main.py --log-level DEBUG
```

### 查看执行顺序

插件执行时会输出日志：

```
开始执行插件
[Level 0] 执行插件: dld_configtmp
  ✓ 完成
[Level 1] 执行插件: config_parser
  ✓ 完成
[Level 2] 执行插件: excel_writer
  ✓ 完成
[Level 3] 执行插件: auto_filename
  ✓ 完成
插件执行完成
```

### 依赖未满足警告

如果依赖未满足，会跳过插件：

```
[Level 2] 执行插件: excel_writer
  ⚠️  跳过: 依赖未满足
```

**排查步骤：**
1. 检查依赖插件是否启用（config.yaml 中 `enable: true`）
2. 检查依赖插件是否执行成功
3. 检查依赖插件是否返回了预期输出
4. 检查 `dependencies` 列表中的名称是否与注册键名一致

## 最佳实践

### 1. 明确插件职责

每个插件应该有**单一、明确的职责**，避免做太多事情。

### 2. 最小化依赖

只声明**必需的依赖**，避免不必要的耦合。

### 3. 健壮的输出

插件应该返回**清晰、完整的输出**，供下游插件使用：

```python
def execute(self, context: dict) -> dict:
    return {
        "sections": sections,      # 主要数据
        "parser": parser,          # 有用的对象
        "trace_file": trace_file,  # 元信息
        "stats": {                 # 统计信息
            "count": len(sections),
            "duration": elapsed_time,
        }
    }
```

### 4. 容错处理

插件应该**优雅处理依赖缺失**的情况：

```python
def execute(self, context: dict) -> dict:
    # 尝试获取依赖输出，提供默认值
    sections = context.get("config_parser", {}).get("sections", [])

    if not sections:
        # 处理空情况
        warning("未找到 config_parser 输出，使用默认值")
        sections = []
```

### 5. 配置驱动

通过配置文件控制插件行为，而不是硬编码：

```yaml
# config.yaml
enable: true

dependencies:
  required: ["config_parser"]  # 必需依赖
  optional: ["validator"]     # 可选依赖
```

## 相关文件

- `src/plugins/base.py` - 插件基类定义
- `src/plugins/__init__.py` - 插件注册表和调度器
- `src/workflow.py` - 插件工作流调用
- 各插件目录的 `plugin.py` - 具体插件实现

## 示例：完整的插件依赖链

```
用户输入
   ↓
dld_configtmp (Level 0)
   ├─ 查找/下载模板
   ├─ 返回: template_path
   ↓
config_parser (Level 1)
   ├─ 依赖: dld_configtmp ✅
   ├─ 解析 trace 文件
   ├─ 返回: sections, parser
   ↓
excel_writer (Level 2)
   ├─ 依赖: dld_configtmp ✅, config_parser ✅
   ├─ 使用 template_path 加载模板
   ├─ 使用 sections 填充数据
   ├─ 返回: output_file, processor
   ↓
auto_filename (Level 3)
   ├─ 依赖: excel_writer ✅
   ├─ 使用 processor 读取单元格
   ├─ 生成新文件名
   ├─ 返回: output_file (重命名后)
   ↓
最终输出
```

---

**更新时间**: 2026-02-08
