# 日志到Excel匹配工具

将结构化日志文件自动填充到Excel模板中的工程化工具。

## 项目结构

```
ailogproc/
├── README.md
├── SETUP.md                   # 详细设置指南
├── requirements.txt
├── setup_venv.sh             # 环境设置脚本 (Linux/macOS)
├── setup_venv.bat            # 环境设置脚本 (Windows)
├── main.py                   # 主程序入口
├── config/
│   ├── __init__.py
│   ├── default_config.yaml   # YAML 配置文件
│   └── default_config.py     # 配置加载模块
├── src/
│   ├── __init__.py
│   ├── log_parser.py         # 日志解析模块
│   ├── excel_processor.py    # Excel处理模块
│   ├── workflow.py           # 业务流程模块
│   ├── utils.py              # 工具函数模块
│   └── plugins/              # 插件目录
│       ├── __init__.py       # 插件注册表
│       ├── base.py           # 插件基类
│       └── auto_filename.py  # 自动文件名插件
├── examples/
│   ├── templates/            # Excel模板示例
│   ├── logs/                 # 日志文件示例
│   └── outputs/              # 输出结果
└── tests/                    # 测试文件
```

## 快速开始

### 1. 设置环境

```bash
# Linux/macOS
bash setup_venv.sh

# Windows
setup_venv.bat
```

### 2. 激活环境

```bash
# Linux/macOS
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### 3. 运行程序

```bash
# 基本使用
python main.py examples/templates/template_a_column.xlsx examples/logs/sample_log_opsch.txt

# 指定输出文件
python main.py template.xlsx log.txt --output result.xlsx

# 指定工作表
python main.py template.xlsx log.txt --sheet 配置表
```

### 4. 退出环境

```bash
deactivate
```

## 配置

### YAML 配置文件

所有配置在 `config/default_config.yaml` 中，包括：
- 关键字映射 (`keyword_mapping`)
- 字段名映射 (`field_name_mapping`)
- 特殊前缀处理 (`special_prefix`)
- 顶格表格配置 (`top_table`)
- 插件配置 (`auto_filename` 等)

### 插件系统

项目采用**层级插件架构**，插件按层级顺序执行。

**插件层级：**
- **Level 1: Extractor（提取层）** - 从日志提取信息
  - `config_extractor` - 提取配置
- **Level 2: Processor（处理层）** - 处理提取的数据
  - `excel_writer` - 写入Excel
  - `constraint_validator` - 约束检查（未来）
- **Level 3: 小插件** - 轻量级收尾工作
  - `auto_filename` - 自动重命名

**添加新插件：**
1. 创建 `src/plugins/your_plugin.py`（继承 Plugin 基类）
2. 设置 `level` 和 `dependencies`
3. 在 `src/plugins/__init__.py` 注册
4. 在 `config/default_config.yaml` 添加配置

详见 [SETUP.md](SETUP.md)

## 功能特性

✅ 顶格表格处理
✅ 多子表支持
✅ 多 TopConfig 自动分页
✅ 智能字段匹配
✅ 合并单元格支持
✅ 自动文件命名
✅ 插件化架构
✅ YAML 配置驱动
✅ Python venv 虚拟环境

## 许可证

MIT License
