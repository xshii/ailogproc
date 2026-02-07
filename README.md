# 日志到Excel匹配工具

将结构化日志文件自动填充到Excel模板中的工程化工具。

## 项目结构

```
log_matcher_project/
├── README.md
├── requirements.txt
├── main.py                    # 主程序入口
├── config/
│   ├── __init__.py
│   └── default_config.py      # 配置文件
├── src/
│   ├── __init__.py
│   ├── log_parser.py          # 日志解析模块
│   ├── excel_processor.py     # Excel处理模块
│   ├── workflow.py            # 业务流程模块
│   └── utils.py               # 工具函数模块
├── examples/
│   ├── templates/             # Excel模板示例
│   ├── logs/                  # 日志文件示例
│   └── outputs/               # 输出结果
└── tests/                     # 测试文件
```

## 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 基本使用

```bash
python main.py examples/templates/template.xlsx examples/logs/log.txt
```

### 指定输出

```bash
python main.py template.xlsx log.txt --output result.xlsx
```

## 配置

所有配置在 `config/default_config.py` 中，包括：
- 关键字映射
- 字段名映射
- 特殊前缀处理
- 自动文件名生成

## 功能特性

✅ 顶格表格处理
✅ 多子表支持
✅ 多TopConfig自动分页
✅ 智能字段匹配
✅ 合并单元格支持
✅ 自动文件命名

## 许可证

MIT License
