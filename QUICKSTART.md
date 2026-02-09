# ⚡ 快速开始指南

> **版本**: v1.0.1
> **更新**: 2026-02-09

---

## 📦 1. 安装

### 开发模式（推荐）

```bash
# 克隆或进入项目目录
cd ailogproc

# 使用 pyproject.toml 安装（推荐）
pip install -e .[dev]

# 或者只安装依赖
pip install -r requirements.txt
```

### 生产模式

```bash
# 直接安装包
pip install .

# 或从 PyPI（未来）
# pip install ailogproc
```

---

## 🚀 2. 运行示例

### 2.1 配置日志处理 (Config Log Processing)

```bash
# 最简单：使用默认模板和自动查找的 trace 文件
python main.py

# 指定模板文件（trace 文件仍自动查找）
python main.py examples/templates/template_a_column.xlsx

# 完整指定
python main.py examples/templates/template_a_column.xlsx examples/logs/sample_log_opsch.txt

# 指定输出文件
python main.py template.xlsx log.txt --output my_result.xlsx

# 指定工作表
python main.py template.xlsx log.txt --sheet 配置表

# 设置日志级别
python main.py --log-level DEBUG
```

**自动查找规则：**
- **Excel 模板**：`templates/*.xlsx` → `examples/templates/*.xlsx`（取第一个）
- **Trace 文件**：`logs/trace_*.txt` → `logs/*.txt` → `examples/logs/*.txt`（取最新）

### 2.2 性能日志分析 (Performance Analysis)

```bash
# 分析性能日志
python main.py --perf examples/logs/perf_sample.log

# 指定输出路径
python main.py --perf perf.log --output output/perf_timeline.html

# 查看生成的可视化报告
open output/perf_timeline.html
```

**输出内容：**
- 📊 算子执行时间线（PyEcharts 交互式图表）
- 📈 性能指标统计（P50/P95/P99）
- 📉 耗时分布直方图（可选）

### 2.3 二进制数据提取 (Data Extraction)

```bash
# 提取二进制数据
python main.py --data examples/logs/binary_data.txt

# 指定输出报告
python main.py --data data.txt --output output/data_report.json

# 查看提取结果
cat output/data_report.json | jq
```

**输出格式：**
- JSON 格式报告
- 包含解析后的结构化数据
- 支持自定义字段映射

---

## ⚙️ 3. 配置

编辑 `config/default_config.yaml` 修改配置：

### 3.1 配置日志插件

```yaml
# 日志文件路径（可选，null 表示通过命令行传入）
log_file: null

# 自动文件名插件
auto_filename:
  enable: true
  fields: ['systemMode', 'debugLevel', 'carrierType']
  value_mapping:
    systemMode:
      FDD: FDD
      TDD: TDD
    debugLevel:
      0: L0
      1: L1

# 配置解析插件
config_parser:
  enable: true
  log_keyword: 'opSch'

# Excel 写入插件
excel_writer:
  enable: true
  top_table:
    enable: true
    log_keyword: 'opSch'
    target_column: 3
  keyword_mapping:
    ExCfg-ER: 'ERCfg\s*\(grp\s*=\s*\d+\)'
    INxCfg: 'InxCfg\d+'

# 约束检查插件
constraint_checker:
  enable: true
  check_only: false
```

### 3.2 性能分析插件

```yaml
# 性能解析插件
perf_parser:
  enable: true
  rules:
    - name: "task_execution"
      start_pattern: "Task\\s+(\\d+)\\s+start.*cycle=(\\d+)"
      end_pattern: "Task\\s+(\\d+)\\s+done.*cycle=(\\d+)"

# 性能分析插件
perf_analyzer:
  enable: true
  metrics:
    - duration
    - concurrency
    - idle_time

# 性能可视化插件
perf_visualizer:
  enable: true
  gantt:
    title: "算子执行时间线"
    output_path: "output/perf_timeline.html"
    color_scheme: "default"  # default, rainbow, monochrome
```

### 3.3 数据提取插件

```yaml
# 数据解析插件
data_parser:
  enable: true
  source:
    type: "direct"
    format: "spaced"  # spaced, continuous
  fields:
    - name: "timestamp"
      offset: 0
      length: 4
      type: "uint32"
    - name: "device_id"
      offset: 4
      length: 2
      type: "uint16"
```

**详细配置说明**: [config/README.md](config/README.md)

---

## 📂 4. 目录说明

```
ailogproc/
├── config/                   # 配置目录
│   ├── default_config.yaml   # 应用配置（插件、字段映射等）
│   ├── .pylintrc            # Pylint 代码质量配置
│   ├── .coveragerc          # Coverage 覆盖率配置
│   └── pytest.ini           # Pytest 测试配置
│
├── src/plugins/             # 插件目录（层级架构 0-4）
│   ├── base.py              # 插件基类
│   │
│   ├── dld_configtmp/       # Level 0: 模板下载
│   │
│   ├── config_parser/       # Level 1: 配置日志解析
│   ├── perf_parser/         # Level 1: 性能日志解析
│   ├── data_parser/         # Level 1: 二进制数据解析
│   │
│   ├── constraint_checker/  # Level 2: 约束检查
│   ├── perf_analyzer/       # Level 2: 性能指标分析
│   │
│   ├── excel_writer/        # Level 3: Excel 写入
│   │   ├── data_models.py   # 14个数据类（Phase 2）
│   │   ├── processor.py     # Excel 处理器
│   │   └── plugin.py        # 插件入口
│   ├── perf_visualizer/     # Level 3: 性能可视化
│   │
│   └── auto_filename/       # Level 4: 自动文件命名
│
├── src/utils/               # 工具模块
│   ├── logger.py            # 统一日志系统
│   └── security.py          # 安全工具（路径验证等）
│
├── src/commands/            # 命令行模块
│   ├── cfg2excel.py         # 配置日志命令
│   ├── perflog.py           # 性能日志命令
│   └── cfglimit.py          # 约束检查命令
│
├── examples/                # 示例文件
│   ├── templates/           # Excel 模板
│   ├── logs/                # 日志文件
│   └── outputs/             # 输出结果
│
├── docs/                    # 文档
│   ├── PLUGINS_OVERVIEW.md  # 插件系统总览 ⭐
│   ├── REFACTORING_GUIDE.md # 重构指南（Phase 2）
│   ├── CODE_QUALITY_REVIEW.md # 代码质量分析
│   ├── QUALITY_GATE.md      # 质量门限说明
│   └── COVERAGE.md          # 测试覆盖率说明
│
├── tests/                   # 测试文件（316个测试）
│   ├── unit/                # 单元测试
│   ├── integration/         # 集成测试
│   ├── plugins/             # 插件测试
│   └── utils/               # 工具测试
│
├── pyproject.toml           # 项目配置（现代化）⭐
├── setup.py                 # 安装脚本（兼容）
├── requirements.txt         # 依赖列表
├── Jenkinsfile              # Jenkins CI/CD 配置 ⭐
├── Makefile                 # 开发命令快捷方式
└── main.py                  # 主程序入口
```

---

## ✨ 5. 核心功能

### 5.1 配置日志处理
- ✅ **层级插件架构**（9个插件协同工作）
- ✅ **智能字段匹配**（顶表/子表，A列/B列）
- ✅ **特殊前缀处理**（`*` 标记特殊字段）
- ✅ **多子表支持**（关键字映射 + 正则）
- ✅ **自动文件命名**（基于配置字段）
- ✅ **约束检查**（配置合法性验证）

### 5.2 性能日志分析
- ✅ **事件配对**（start/end 自动匹配）
- ✅ **性能指标**（duration, concurrency, idle_time, bottleneck）
- ✅ **统计分析**（P50/P95/P99, 平均值，标准差）
- ✅ **可视化时间线**（PyEcharts 交互式图表）
- ✅ **耗时分布图**（直方图分析）

### 5.3 数据提取
- ✅ **16进制解析**（多种格式支持）
- ✅ **字段提取**（offset/length/type 配置）
- ✅ **类型转换**（uint8/16/32, int8/16/32, hex, string）
- ✅ **值映射**（枚举值 → 可读字符串）
- ✅ **JSON 导出**（结构化报告）

### 5.4 代码质量（Phase 2 重构）
- ✅ **参数减少 85%**（使用数据类）
- ✅ **14个数据类模型**（简化参数传递）
- ✅ **测试覆盖 +13%**（280 → 316 测试）
- ✅ **零回归**（所有功能保持正常）

### 5.5 工程化
- ✅ **统一日志系统**（控制台 + 文件轮转）
- ✅ **YAML 配置驱动**（灵活配置）
- ✅ **pyproject.toml**（现代化项目配置）
- ✅ **完整 CI/CD**（GitHub Actions + Jenkins）
- ✅ **安全防护**（路径验证，防止遍历攻击）

---

## 🛠️ 6. 开发命令

```bash
# 运行测试
make test
# 或 pytest tests/ -v

# 代码质量检查（Pylint ≥ 9.0/10）
make quality
# 或 pylint src/ main.py --rcfile=config/.pylintrc

# 代码格式检查（Ruff）
make format-check
# 或 ruff format --check src/ main.py

# 代码 Linter（Ruff）
make lint
# 或 ruff check src/ main.py

# 自动修复格式
make format
# 或 ruff format src/ main.py

# 测试覆盖率检查（≥ 70%）
make coverage
# 或 pytest tests/ --cov=src --cov-report=html

# 运行所有检查
make all

# 清理临时文件
make clean
```

---

## ❓ 7. 常见问题

### Q1: 如何启用/禁用某个插件？

编辑 `config/default_config.yaml`：

```yaml
auto_filename:
  enable: false  # 禁用自动文件名插件
```

### Q2: 如何添加新的子表类型？

编辑 `config/default_config.yaml`：

```yaml
excel_writer:
  keyword_mapping:
    NewTable: 'NewPattern\d+'  # 支持正则表达式
    AnotherTable: 'ExactMatch'  # 精确匹配
```

### Q3: 如何查看日志？

```bash
# 日志文件位置（自动轮转，最大 1000MB）
ls -lh logs/app_*.log

# 查看最新日志
tail -f logs/app_*.log

# 调整日志级别
python main.py --log-level DEBUG
```

### Q4: 如何自定义性能分析规则？

编辑 `config/default_config.yaml`：

```yaml
perf_parser:
  rules:
    - name: "custom_task"
      start_pattern: "START\\s+(\\w+).*ts=(\\d+)"
      end_pattern: "END\\s+(\\w+).*ts=(\\d+)"
      correlation_field: 1  # 使用第1个捕获组关联
      time_field: 2         # 使用第2个捕获组作为时间
```

### Q5: 如何自定义数据解析格式？

编辑 `config/default_config.yaml`：

```yaml
data_parser:
  fields:
    - name: "header"
      offset: 0
      length: 2
      type: "hex"
    - name: "device_id"
      offset: 2
      length: 1
      type: "uint8"
    - name: "payload"
      offset: 3
      length: 16
      type: "hex"
  value_mapping:
    device_id:
      0x01: "DeviceA"
      0x02: "DeviceB"
```

### Q6: 如何添加新插件？

1. **创建插件目录**：`src/plugins/your_plugin/`
2. **实现插件类**：
   ```python
   from src.plugins.base import Plugin

   class YourPlugin(Plugin):
       level = 1  # 设置执行顺序
       dependencies = []  # 依赖的其他插件

       def execute(self, context: dict) -> dict:
           # 实现插件逻辑
           return {"result": "success"}
   ```
3. **注册插件**：在 `src/plugins/__init__.py` 中注册
4. **添加配置**：在 `config/default_config.yaml` 中添加配置节

详见：[docs/PLUGINS_OVERVIEW.md](docs/PLUGINS_OVERVIEW.md)

### Q7: 如何使用模板下载功能？

```bash
# 启用模板下载插件
# 编辑 config/default_config.yaml:
dld_configtmp:
  enable: true
  api_url: "https://your-template-server.com/api/templates"
  cache_dir: ".cache/templates"
  cache_ttl: 86400  # 24小时

# 运行时自动下载
python main.py --template-id ABC123
```

### Q8: Phase 2 重构带来了什么改进？

**参数减少 85%**：
- Before: `function(arg1, arg2, arg3, arg4, arg5, arg6, arg7)`
- After: `function(context)`  # 使用数据类

**好处**：
- ✅ 更易读
- ✅ 更易维护
- ✅ 更易测试
- ✅ IDE 支持更好

详见：[docs/REFACTORING_GUIDE.md](docs/REFACTORING_GUIDE.md)

---

## 📚 8. 进阶阅读

### 文档
- [插件系统总览](docs/PLUGINS_OVERVIEW.md) - 完整的插件架构说明 ⭐
- [重构指南](docs/REFACTORING_GUIDE.md) - Phase 2 数据类最佳实践
- [代码质量分析](docs/CODE_QUALITY_REVIEW.md) - 质量改进详情

### 插件 README（9个）
- [auto_filename](src/plugins/auto_filename/README.md) - 自动文件命名
- [config_parser](src/plugins/config_parser/README.md) - 配置日志解析
- [excel_writer](src/plugins/excel_writer/README.md) - Excel 模板填充
- [constraint_checker](src/plugins/constraint_checker/README.md) - 约束检查
- [dld_configtmp](src/plugins/dld_configtmp/README.md) - 模板下载
- [perf_parser](src/plugins/perf_parser/README.md) - 性能日志解析
- [perf_analyzer](src/plugins/perf_analyzer/README.md) - 性能指标分析
- [perf_visualizer](src/plugins/perf_visualizer/README.md) - PyEcharts 可视化
- [data_parser](src/plugins/data_parser/README.md) - 二进制数据提取

### 示例代码
```bash
# 查看示例代码
ls examples/*_example.py

# 运行示例
python examples/constraint_checker_demo.py
python examples/data_parser_example.py
python examples/binary_export_example.py
```

---

## 🎯 9. 下一步

1. **配置您的第一个模板** - 编辑 `config/default_config.yaml`
2. **运行示例** - `python main.py`
3. **查看文档** - [docs/PLUGINS_OVERVIEW.md](docs/PLUGINS_OVERVIEW.md)
4. **加入开发** - 查看 [CONTRIBUTING.md](CONTRIBUTING.md)（如果有）

---

## 📞 10. 获取帮助

- **Issues**: https://github.com/xshii/ailogproc/issues
- **文档**: [docs/](docs/)
- **示例**: [examples/](examples/)

---

**当前版本**: v1.0.1
**最后更新**: 2026-02-09
**测试状态**: 316/316 ✅
