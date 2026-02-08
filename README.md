# 日志到Excel匹配工具

将结构化日志文件自动填充到Excel模板中的工程化工具。

## 项目结构

```
ailogproc/
├── main.py                   # 主程序入口
├── Makefile                  # 开发命令快捷方式
├── requirements.txt
├── config/                   # 配置目录
│   ├── default_config.yaml   # 应用配置
│   ├── default_config.py     # 配置加载器
│   ├── .pylintrc            # Pylint 质量检查配置
│   ├── .coveragerc          # 测试覆盖率配置
│   ├── pytest.ini           # Pytest 测试配置
│   └── README.md            # 配置说明文档
├── src/
│   ├── utils/
│   │   ├── logger.py        # 统一日志系统
│   │   └── logger_config.yaml
│   └── plugins/             # 插件目录
│       ├── base.py          # 插件基类
│       ├── config_parser/   # 配置解析插件
│       ├── dld_configtmp/   # 模板下载插件
│       ├── constraint_checker/ # 配置约束检查插件
│       ├── excel_writer/    # Excel 写入插件
│       └── auto_filename/   # 自动命名插件
├── docs/                    # 文档目录
│   ├── QUALITY_GATE.md      # 代码质量门限说明
│   └── COVERAGE.md          # 测试覆盖率说明
├── scripts/                 # 脚本目录
│   ├── check_quality.sh     # 质量检查脚本
│   └── check_coverage.sh    # 覆盖率检查脚本
├── .github/workflows/       # CI/CD 工作流
│   ├── pylint.yml          # 代码质量检查
│   └── coverage.yml        # 测试覆盖率检查
└── tests/                   # 测试文件
```

## 快速开始

### 1. 安装

```bash
# 开发模式（推荐）
pip install -e .

# 或只安装依赖
pip install -r requirements.txt
```

### 2. 运行程序

```bash
# 最简单：无参数运行，插件自动查找模板和 trace
python main.py

# 指定模板文件
python main.py template.xlsx

# 指定输出文件和工作表
python main.py template.xlsx --output result.xlsx --sheet 配置表

# 设置日志级别
python main.py --log-level DEBUG
```

**自动查找规则（由插件实现）：**
- **Excel 模板**：`templates/*.xlsx` → `examples/templates/*.xlsx`（`dld_configtmp` 插件）
- **Trace 文件**：`logs/trace_*.txt` → `logs/*.txt` → `examples/logs/*.txt`（`config_parser` 插件）

## 插件架构

项目采用**层级插件架构**，插件按层级和依赖关系顺序执行：

| 层级 | 插件 | 依赖 | 功能 |
|------|------|------|------|
| **Level 0** | `dld_configtmp` | - | 下载/准备 Excel 模板 |
| **Level 1** | `config_parser` | `dld_configtmp` | 解析 trace 日志文件 |
| **Level 2** | `constraint_checker` | `config_parser` | 检查配置约束条件 |
| **Level 3** | `excel_writer` | `dld_configtmp`, `config_parser`, `constraint_checker` | 将数据写入 Excel 表格 |
| **Level 4** | `auto_filename` | `excel_writer` | 根据内容自动重命名输出文件 |

**插件依赖链：**
```
dld_configtmp (Level 0)
  └─> config_parser (Level 1)
        └─> constraint_checker (Level 2)
              └─> excel_writer (Level 3)
                    └─> auto_filename (Level 4)
```

**添加新插件：**
1. 创建插件目录 `src/plugins/your_plugin/`
2. 实现 `plugin.py`（继承 `Plugin` 基类，设置 `level` 和 `dependencies`）
3. 在 `src/plugins/__init__.py` 注册
4. 在插件目录创建 `config.yaml` 配置文件

详见：[插件依赖关系文档](docs/PLUGIN_DEPENDENCIES.md)

## 配置文件

所有配置文件统一放在 `config/` 目录：

| 文件 | 用途 |
|------|------|
| `default_config.yaml` | 应用配置（插件、字段映射等） |
| `.pylintrc` | Pylint 代码质量检查配置 |
| `.coveragerc` | 测试覆盖率配置 |
| `pytest.ini` | Pytest 测试框架配置 |

详见 [config/README.md](config/README.md)

## 开发

### 常用命令

```bash
# 运行测试
make test

# 代码质量检查（Pylint）
make quality

# 测试覆盖率检查
make coverage

# 运行所有检查
make all

# 清理临时文件
make clean

# 查看覆盖率报告
make report
```

### 代码质量门限

本项目设置了严格的质量门限，CI 会自动检查：

| 指标 | 门限 | 状态 |
|------|------|------|
| **Pylint 分数** | ≥ 9.5/10 | ✅ 9.70/10 |
| **测试覆盖率** | ≥ 70% | ⚠️ 68% |

详见：
- [代码质量门限文档](docs/QUALITY_GATE.md)
- [测试覆盖率文档](docs/COVERAGE.md)

### 日志系统

项目使用统一的日志系统 (`src/utils/logger.py`)：
- 支持控制台和文件输出
- 自动日志轮转（1000MB，保留 5 个备份）
- 日志文件名包含时间戳：`app_YYYYMMDD_HHMMSS.log`
- 配置文件：`src/utils/logger_config.yaml`

## 功能特性

✅ 层级插件架构
✅ 顶格表格处理
✅ 多子表支持
✅ 智能字段匹配
✅ 自动文件命名
✅ YAML 配置驱动
✅ 统一日志系统
✅ 代码质量门限 (Pylint 9.5+)
✅ 测试覆盖率检查 (70%+)
✅ CI/CD 自动化

## 许可证

MIT License
