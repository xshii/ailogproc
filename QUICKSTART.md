# 快速开始指南

## 1. 安装

### 开发模式（推荐）

```bash
# 克隆或进入项目目录
cd ailogproc

# 安装包（可编辑模式）
pip install -e .

# 或者只安装依赖
pip install -r requirements.txt
```

### 生产模式

```bash
# 直接安装包
pip install .
```

## 2. 运行示例

```bash
# 最简单：使用默认模板和自动查找的 trace 文件
python main.py

# 指定模板文件（trace 文件仍自动查找）
python main.py examples/templates/template_a_column.xlsx

# 指定输出文件
python main.py examples/templates/template_a_column.xlsx --output my_result.xlsx

# 指定工作表
python main.py --sheet 配置表

# 设置日志级别
python main.py --log-level DEBUG
```

**自动查找规则：**
- **Excel 模板**：`templates/*.xlsx` → `examples/templates/*.xlsx`（取第一个）
- **Trace 文件**：`logs/trace_*.txt` → `logs/*.txt` → `examples/logs/*.txt`（取最新）

## 3. 配置

编辑 `config/default_config.yaml` 修改配置：

```yaml
# 插件配置
auto_filename:
  enable: true
  fields: ['systemMode', 'debugLevel']
  value_mapping:
    systemMode:
      FDD: FDD
      TDD: TDD

# Excel 写入插件配置
excel_writer:
  enable: true
  top_table:
    enable: true
    log_keyword: 'opSch'

# 关键字映射
keyword_mapping:
  ExCfg-ER: 'ERCfg\s*\(grp\s*=\s*\d+\)'
  INxCfg: 'InxCfg\d+'
```

详细配置说明见 [config/README.md](config/README.md)

## 4. 目录说明

```
config/                   - 配置目录
  ├── default_config.yaml - 应用配置（插件、字段映射等）
  ├── .pylintrc          - 代码质量配置
  └── .coveragerc        - 测试覆盖率配置

src/plugins/             - 插件目录（层级架构）
  ├── config_parser/     - Level 1: 解析 trace 日志
  ├── dld_configtmp/          - Level 0: 下载模板
  ├── config_extractor/ - Level 1: 提取配置
  ├── excel_writer/     - Level 2: 写入 Excel
  └── auto_filename/    - Level 3: 自动命名

src/utils/               - 工具模块
  └── logger.py         - 统一日志系统

examples/                - 示例文件
  ├── templates/        - Excel 模板
  ├── logs/            - 日志文件
  └── outputs/         - 输出结果

docs/                    - 文档
  ├── QUALITY_GATE.md   - 代码质量说明
  └── COVERAGE.md       - 测试覆盖率说明
```

## 5. 核心功能

- ✅ 层级插件架构（5 个插件协同工作）
- ✅ 智能字段匹配（A列/B列）
- ✅ 顶格表格处理
- ✅ 多子表支持
- ✅ 自动文件命名
- ✅ 统一日志系统（控制台 + 文件轮转）
- ✅ YAML 配置驱动

## 6. 开发命令

```bash
# 运行测试
make test

# 代码质量检查（Pylint ≥ 9.5/10）
make quality

# 测试覆盖率检查（≥ 70%）
make coverage

# 运行所有检查
make all

# 清理临时文件
make clean
```

## 7. 常见问题

### Q: 如何启用/禁用某个插件？

编辑 `config/default_config.yaml`：

```yaml
auto_filename:
  enable: false  # 禁用自动文件名插件
```

### Q: 如何添加新的子表类型？

编辑 `config/default_config.yaml`：

```yaml
keyword_mapping:
  NewTable: 'NewPattern\d+'
```

### Q: 如何查看日志？

```bash
# 日志文件位置（自动轮转，最大 1000MB）
ls -lh logs/app_*.log

# 查看最新日志
tail -f logs/app_*.log
```

### Q: 如何自定义默认模板和 trace 文件位置？

将文件放到指定目录即可：
```bash
# 默认模板目录（按优先级）
templates/             # 优先
examples/templates/    # 回退

# 默认 trace 文件目录（按优先级）
logs/trace_*.txt       # 优先（推荐命名格式）
logs/*.txt             # 回退
examples/logs/*.txt    # 最后回退
```

程序会自动选择：
- 模板：按字母顺序取第一个
- Trace：按修改时间取最新的

### Q: 如何添加新插件？

1. 创建插件目录：`src/plugins/your_plugin/`
2. 实现 `plugin.py`（继承 `Plugin` 基类）
3. 在 `src/plugins/__init__.py` 注册
4. 在 `config/default_config.yaml` 添加配置

详见 [README.md](README.md) 插件架构章节
