# 性能日志处理架构

## 目录结构

```
ailogproc/
├── src/plugins/
│   ├── # === 配置日志处理流程（日志B - 现有功能） ===
│   ├── config_parser/          # Level 1: 解析配置日志
│   ├── constraint_checker/     # Level 2: 检查配置约束
│   ├── excel_writer/           # Level 3: 写入Excel
│   ├── auto_filename/          # Level 4: 自动重命名
│   │
│   └── # === 性能日志处理流程（日志A - 新功能） ===
│       ├── perf_parser/        # Level 1: 解析性能日志，匹配开始/结束
│       ├── perf_analyzer/      # Level 2: 性能数据统计分析
│       └── perf_visualizer/    # Level 3: 生成算子执行时间线图
│
├── examples/
│   ├── logs/
│   │   ├── sample_log_opsch.txt      # 配置日志示例
│   │   └── sample_perf_log.txt       # 性能日志示例
│   └── templates/
│       └── template_a_column.xlsx    # Excel模板
│
└── output/                     # 输出目录
    ├── constraint_report.json  # 约束检查报告
    ├── perf_analysis.json      # 性能分析报告
    ├── perf_analysis.csv       # 性能数据CSV
    └── perf_gantt.html         # 算子执行时间线图
```

## 性能日志处理插件

### 1. perf_parser - 性能日志解析器

**功能：**
- 支持多组提取规则（不同的日志格式）
- 使用正则表达式提取字段（开始cycle、结束cycle等）
- 根据配置的匹配字段关联开始/结束事件
- 自动计算性能指标（耗时 = 结束 - 开始）

**配置示例：**
```yaml
extraction_rules:
  - name: "通用任务"
    start_pattern:
      regex: '开始.*ID:\s*(?P<task_id>\w+).*单元:\s*(?P<unit>\w+).*cycle:\s*(?P<cycle_start>\d+)'
      fields:
        task_id: {type: "string", required: true}
        unit: {type: "string", required: true}
        cycle_start: {type: "int", required: true}
    
    end_pattern:
      regex: '完成.*ID:\s*(?P<task_id>\w+).*单元:\s*(?P<unit>\w+).*cycle:\s*(?P<cycle_end>\d+)'
      fields:
        task_id: {type: "string", required: true}
        cycle_end: {type: "int", required: true}
    
    match_fields:
      - "task_id"
      - "unit"
    
    performance:
      duration_field: "duration_cycles"
      formula: "cycle_end - cycle_start"
```

**输出：**
```python
{
  'pairs': [
    {
      'correlation_id': 'TASK001',
      'start_event': {...},
      'end_event': {...},
      'duration_cycles': 1250,
      'execution_unit': 'NPU0'
    }
  ]
}
```

### 2. perf_analyzer - 性能数据分析器

**功能：**
- 计算统计指标（min, max, mean, p50, p90, p95, p99）
- 按执行单元分组统计
- 异常值检测（IQR / Z-score / 百分位）
- 生成JSON和CSV报告

**配置示例：**
```yaml
analysis:
  compute_statistics: true
  detect_outliers: true
  outlier_method: "iqr"  # iqr | zscore | percentile

grouping:
  by_execution_unit: true

reporting:
  generate_json: true
  json_path: "output/perf_analysis.json"
  generate_csv: true
  csv_path: "output/perf_analysis.csv"
```

**输出报告：**
```json
{
  "summary": {
    "count": 100,
    "min": 125,
    "max": 3450,
    "mean": 850.5,
    "p50": 800,
    "p90": 1500,
    "p95": 2000
  },
  "by_unit": {
    "NPU0": {"count": 45, "mean": 920},
    "NPU1": {"count": 35, "mean": 780},
    "CPU0": {"count": 20, "mean": 450}
  }
}
```

### 3. perf_visualizer - 性能可视化器

**功能：**
- 生成算子执行时间线（类似升腾Studio）
- 甘特图展示各执行单元的算子执行情况
- 支持缩放、悬停查看详情
- 可选：生成耗时分布直方图

**配置示例：**
```yaml
gantt:
  output_path: "output/perf_gantt.html"
  title: "算子执行时间线"
  group_by_unit: true
  show_duration: true
  color_scheme: "default"  # default | rainbow | monochrome
  height: 600
  width: 1400
```

**输出：**
- HTML交互式图表（使用Plotly）
- 按执行单元分行显示
- 时间轴横向展开
- 悬停显示详细信息

## 使用方式

### 处理配置日志（日志B - 现有功能）

```bash
# 解析配置 + 填充Excel + 约束检查
python main.py config_log.txt

# 仅检查约束，不生成Excel
# 修改 src/plugins/constraint_checker/config.yaml
# check_only: true
python main.py config_log.txt
```

### 处理性能日志（日志A - 新功能）

```bash
# 性能分析 + 生成时间线图
python perf_main.py perf_log.txt

# 或指定配置
python perf_main.py perf_log.txt --config custom_perf_config.yaml
```

## 扩展性

### 添加新的提取规则

编辑 `src/plugins/perf_parser/config.yaml`，添加新的规则组：

```yaml
extraction_rules:
  - name: "新规则"
    description: "描述"
    start_pattern:
      regex: '你的正则表达式'
      fields: {...}
    end_pattern:
      regex: '你的正则表达式'
      fields: {...}
    match_fields: [...]
    performance:
      duration_field: "..."
      formula: "..."
```

### 自定义可视化

修改 `src/plugins/perf_visualizer/config.yaml`：
- 调整颜色方案
- 修改图表尺寸
- 启用/禁用不同类型的图表

## 技术栈

- **日志解析**: 正则表达式 + 命名捕获组
- **数据分析**: Python标准库（统计计算）
- **可视化**: Plotly（交互式HTML图表）
- **报告**: JSON + CSV

## 优势

✅ **灵活的规则配置** - 支持多组不同格式的日志
✅ **自动匹配关联** - 根据字段组合自动匹配开始/结束
✅ **性能计算** - 自动计算cycle差值
✅ **专业可视化** - 升腾Studio风格的时间线图
✅ **统计分析** - 完整的统计指标和异常检测
✅ **插件化架构** - 易于扩展和维护
