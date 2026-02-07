# 快速开始指南

## 1. 安装

```bash
# 安装依赖
pip install -r requirements.txt
```

## 2. 运行示例

```bash
# 基本使用
python main.py examples/templates/template_a_column.xlsx examples/logs/sample_log_opsch.txt

# 指定输出文件
python main.py examples/templates/template_a_column.xlsx examples/logs/sample_log_opsch.txt --output my_result.xlsx
```

## 3. 配置

编辑 `config/default_config.py` 修改：

```python
# 关键字映射
KEYWORD_MAPPING = {
    'ExCfg-ER': r'ERCfg\s*\(grp\s*=\s*\d+\)',
    'INxCfg': r'InxCfg\d+',
}

# 顶表关键字
TOP_TABLE_LOG_KEYWORD = 'opSch'

# 文件名生成
FILENAME_FIELDS = ['systemMode', 'debugLevel']
```

## 4. 目录说明

```
config/          - 配置文件
src/             - 源代码
  ├── log_parser.py       - 日志解析
  ├── excel_processor.py  - Excel处理
  ├── workflow.py         - 业务流程
  └── utils.py            - 工具函数
examples/        - 示例文件
  ├── templates/ - Excel模板
  ├── logs/      - 日志文件
  └── outputs/   - 输出结果
```

## 5. 核心功能

- ✅ 自动识别多个TopConfig并创建多个工作表
- ✅ 智能字段匹配（A列/B列）
- ✅ 特殊前缀处理（合并单元格）
- ✅ 按日志顺序生成子表
- ✅ 自动文件命名

## 6. 常见问题

### Q: 如何添加新的子表类型？

修改 `config/default_config.py`:

```python
KEYWORD_MAPPING = {
    'NewTable': r'NewPattern\d+',
}
```

### Q: 如何更改顶表关键字？

```python
TOP_TABLE_LOG_KEYWORD = 'YourKeyword'
```

### Q: 如何禁用自动文件名？

```python
ENABLE_AUTO_FILENAME = False
```
