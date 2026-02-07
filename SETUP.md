# 环境设置指南

本项目使用 Python venv 虚拟环境。

## 🚀 快速开始

### 自动设置（推荐）

#### Linux / macOS

```bash
bash setup_venv.sh
```

#### Windows

```cmd
setup_venv.bat
```

脚本会自动完成：
- 检测系统 Python 版本（需要 3.9+）
- 创建虚拟环境 `venv`
- 安装所有项目依赖

---

## ⚙️ 手动设置

如果自动脚本无法运行：

```bash
# 1. 创建虚拟环境
python3 -m venv venv

# 2. 激活环境
source venv/bin/activate      # Linux/macOS
venv\Scripts\activate         # Windows

# 3. 安装依赖
pip install -r requirements.txt
```

---

## 📋 系统要求

### Python 版本

**必需：** Python 3.9 或更高版本

### 安装 Python（如果没有）

#### macOS

```bash
brew install python@3.9
```

#### Ubuntu/Debian

```bash
sudo apt-get update
sudo apt-get install python3.9 python3.9-venv python3-pip
```

#### CentOS/RHEL

```bash
sudo yum install python39 python39-pip
```

#### Fedora

```bash
sudo dnf install python3.9
```

#### Windows

访问 https://www.python.org/downloads/ 下载安装

**⚠️ 安装时务必勾选 "Add Python to PATH"**

---

## 🚀 使用方法

### 1. 激活环境

**Linux/macOS:**
```bash
source venv/bin/activate
```

**Windows:**
```cmd
venv\Scripts\activate
```

### 2. 运行程序

```bash
# 基本用法
python main.py <Excel文件> <日志文件>

# 示例
python main.py examples/templates/template_a_column.xlsx examples/logs/sample_log_opsch.txt

# 指定输出文件
python main.py template.xlsx log.txt --output result.xlsx

# 指定工作表
python main.py template.xlsx log.txt --sheet 配置表

# 使用配置文件中的日志路径（需在 config/default_config.yaml 中配置 log_file）
python main.py template.xlsx
```

### 3. 退出环境

```bash
deactivate
```

---

## 🔌 插件系统

项目采用**层级插件架构**，插件按层级顺序执行：

### 插件层级

#### Level 1: Extractor（提取层）
从日志中提取各类信息

**当前插件：**
- **config_extractor** - 从日志中提取配置信息

#### Level 2: Processor（处理层）
处理提取的数据

**当前插件：**
- **excel_writer** - 将配置写入Excel模板

#### Level 3: 小插件
轻量级收尾工作

**当前插件：**
- **auto_filename** - 根据字段值自动重命名文件

### 执行流程

```
[Level 1] config_extractor 提取配置 → sections
              ↓
[Level 2] excel_writer 写入Excel → output_file
              ↓
[Level 3] auto_filename 重命名 → final_file
```

### 插件配置

**配置文件：** `config/default_config.yaml`

```yaml
# 插件按层级执行：Level 1 -> Level 2 -> Level 3

config_extractor:
  enable: true

excel_writer:
  enable: true

auto_filename:
  enable: true
  fields: [systemMode, controlMode, debugLevel, verboseLevel]
  value_mapping:
    systemMode:
      '1': auto
      '0x01': auto
      '2': manual
      '0x02': manual
    debugLevel:
      '1': low
      '0x01': low
      '2': high
      '0x02': high
```

### 添加新插件

**示例：添加约束检查插件（Level 2）**

1. **创建插件类** (`src/plugins/constraint_validator.py`)

```python
from src.plugins.base import Plugin

class ConstraintValidatorPlugin(Plugin):
    """约束检查插件 - Level 2"""

    level = 2  # 处理层
    dependencies = ['config_extractor']  # 依赖配置提取

    def execute(self, context: dict) -> dict:
        """
        检查配置约束

        Args:
            context: 上下文字典，包含 config_extractor 的输出

        Returns:
            {'violations': [...]}
        """
        # 获取配置数据
        config_data = context.get('config_extractor', {})
        sections = config_data.get('sections', [])

        # 检查约束
        violations = []
        for section in sections:
            # 检查逻辑...
            pass

        return {'violations': violations}
```

2. **注册插件** (`src/plugins/__init__.py`)

```python
from src.plugins.constraint_validator import ConstraintValidatorPlugin

PLUGIN_REGISTRY = {
    'config_extractor': ConfigExtractorPlugin,
    'excel_writer': ExcelWriterPlugin,
    'constraint_validator': ConstraintValidatorPlugin,  # 添加
    'auto_filename': AutoFilenamePlugin,
}
```

3. **添加配置** (`config/default_config.yaml`)

```yaml
constraint_validator:
  enable: true
  rules:
    - type: range
      field: powerLevel
      min: 0
      max: 100
```

### 插件依赖

插件可以声明依赖关系：

- `dependencies = []` - 无依赖（如 config_extractor）
- `dependencies = ['config_extractor']` - 依赖配置提取
- `dependencies = ['excel_writer']` - 依赖Excel写入

插件调度器会自动检查依赖，确保按正确顺序执行。

---

## 💡 常见问题

### Q: 提示"权限被拒绝"怎么办？

**Linux/macOS:**
```bash
chmod +x setup_venv.sh
```

### Q: 找不到 Python 怎么办？

检查 Python 是否安装：

```bash
python3 --version
```

如果未安装，参考上面"系统要求"部分的安装说明。

### Q: 虚拟环境激活后提示找不到命令？

确保正确激活了环境：

**Linux/macOS:**
```bash
source venv/bin/activate
```

**Windows:**
```cmd
venv\Scripts\activate
```

激活成功后，命令行前面会显示 `(venv)`。

### Q: Windows 提示"无法执行脚本"？

如果使用 PowerShell，需要设置执行策略：

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

或者直接使用批处理脚本 `setup_venv.bat`。

### Q: 想删除虚拟环境怎么办？

```bash
# 先退出环境
deactivate

# 删除 venv 目录
rm -rf venv          # Linux/macOS
rmdir /s venv        # Windows
```

---

## 📦 依赖包

- openpyxl >= 3.0.0
- pyyaml >= 6.0

---

## 📞 获取帮助

如果遇到问题：

1. 检查 Python 版本：`python --version` 或 `python3 --version`
2. 确认虚拟环境已激活（命令行前有 `(venv)` 标识）
3. 查看错误日志
4. 参考本文档的"常见问题"部分

---

**祝使用愉快！** 🎉
