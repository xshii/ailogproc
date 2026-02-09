# Perf Parser Plugin

性能日志解析插件 - 解析性能测试日志

## 功能

从性能测试日志中提取：
- 任务执行记录
- 时间戳信息
- 执行单元（Unit）信息
- 性能指标数据

## 配置

```yaml
perf_parser:
  enable: true
  log_format: "standard"   # 日志格式
  encoding: "utf-8"        # 文件编码
```

## 依赖

- **Level**: 1 (解析层)
- **Dependencies**: 无
- **被依赖**: `perf_analyzer`, `perf_visualizer`

作为性能分析流程的第一步，为后续分析和可视化提供数据。

## 命令行使用

```bash
# 性能日志分析
python main.py --mode perf performance.log

# 指定输出目录
python main.py --mode perf performance.log -o output/

# 仅解析（不分析）
python main.py --mode perf performance.log --parse-only
```

## 日志格式

### 标准格式

```
[2026-02-09 10:00:00.123] [Unit1] Task: Initialize, Status: Start
[2026-02-09 10:00:00.456] [Unit1] Task: Initialize, Status: Complete
[2026-02-09 10:00:01.123] [Unit2] Task: Process, Status: Start
[2026-02-09 10:00:02.456] [Unit2] Task: Process, Status: Complete
```

### 输出格式

```python
{
    "tasks": [
        {
            "unit": "Unit1",
            "task": "Initialize",
            "start_time": "2026-02-09 10:00:00.123",
            "end_time": "2026-02-09 10:00:00.456",
            "duration_ms": 333
        },
        {
            "unit": "Unit2",
            "task": "Process",
            "start_time": "2026-02-09 10:00:01.123",
            "end_time": "2026-02-09 10:00:02.456",
            "duration_ms": 1333
        }
    ]
}
```

## 与其他插件的配合

### 工作流位置

```
[perf_parser] → perf_analyzer → perf_visualizer
      ↓               ↓                ↓
   解析日志        计算指标         生成图表
```

### 插件依赖链

1. **perf_parser**: 解析日志 → 任务列表
2. **perf_analyzer**: 分析任务 → 性能指标
3. **perf_visualizer**: 可视化 → 时间线图表

### 配合示例

```yaml
# 完整性能分析配置
perf_parser:
  enable: true
  log_format: "standard"

perf_analyzer:
  enable: true
  metrics:
    - duration
    - overlap

perf_visualizer:
  enable: true
  output_format: "html"
  gantt:
    title: "性能时间线"
```

## 解析方法

### parse_log()

主解析方法：

```python
parser = PerfParser(config)
result = parser.parse_log("performance.log")

# 返回
{
    "tasks": [...],
    "units": ["Unit1", "Unit2", ...],
    "time_range": {
        "start": "2026-02-09 10:00:00.123",
        "end": "2026-02-09 10:00:10.456"
    }
}
```

### validate_format()

验证日志格式：

```python
is_valid = parser.validate_format(log_file)
# 返回: True/False
```

## 示例输出

```
[性能解析] 开始解析性能日志...
  → 文件: performance.log
  ✓ 格式验证通过
  → 解析任务记录...
  ✓ 解析完成: 156个任务
  - 执行单元: 8个
  - 时间范围: 10.5秒

  任务分布:
    Unit1: 23个任务
    Unit2: 18个任务
    Unit3: 31个任务
    ...
```

## 错误处理

### 格式错误

```
✗ 日志格式错误: 第42行
  期望: [时间戳] [单元] Task: 任务名, Status: 状态
  实际: Invalid log line
```

### 不完整的任务

```
⚠️  发现不完整的任务: 15个
  - Unit3/Task5: 只有开始时间
  - Unit4/Task7: 只有结束时间
  → 这些任务将被忽略
```

### 时间戳异常

```
⚠️  时间戳异常: 第78行
  任务结束时间早于开始时间
  → 已修正为0ms
```

## 自定义解析器

支持扩展解析器：

```python
from src.plugins.perf_parser.plugin import PerfParser

class CustomPerfParser(PerfParser):
    def parse_line(self, line):
        # 自定义行解析逻辑
        pass

    def extract_timestamp(self, line):
        # 自定义时间戳提取
        pass
```

## 常见问题

**Q: 支持哪些时间戳格式？**
A: 支持ISO 8601和常见的日志时间格式。

**Q: 如何处理多线程日志？**
A: 使用 `unit` 字段区分不同的执行单元。

**Q: 日志文件太大怎么办？**
A: 使用流式解析，自动处理大文件（支持GB级别）。

**Q: 可以解析压缩的日志吗？**
A: 支持 `.gz` 和 `.zip` 格式的压缩日志。
