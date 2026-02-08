# Perf Analyzer Plugin

性能分析插件 - 计算性能指标和统计数据

## 功能

基于解析后的任务数据，计算：
- **任务时长**: 每个任务的执行时间
- **并发度**: 同时执行的任务数
- **空闲时间**: 执行单元的空闲时段
- **瓶颈分析**: 识别性能瓶颈
- **统计摘要**: 最大值、最小值、平均值、P95等

## 配置

```yaml
perf_analyzer:
  enable: true
  metrics:
    - duration       # 时长分析
    - concurrency    # 并发分析
    - idle_time      # 空闲分析
    - bottleneck     # 瓶颈分析
  thresholds:
    slow_task_ms: 1000      # 慢任务阈值
    high_concurrency: 5     # 高并发阈值
```

## 依赖

- **Level**: 2 (分析层)
- **Dependencies**: `perf_parser`
- **被依赖**: `perf_visualizer`

## 命令行使用

```bash
# 完整性能分析
python main.py --mode perf performance.log

# 只分析特定指标
python main.py --mode perf performance.log --metrics duration,concurrency

# 生成详细报告
python main.py --mode perf performance.log --detailed-analysis
```

## 分析指标

### 1. 时长分析 (Duration)

```python
{
    "durations": {
        "Unit1": {
            "tasks": ["Task1", "Task2", ...],
            "total_ms": 5000,
            "avg_ms": 250,
            "max_ms": 800,
            "min_ms": 50,
            "p95_ms": 650
        }
    }
}
```

### 2. 并发分析 (Concurrency)

```python
{
    "concurrency": {
        "max": 8,           # 最大并发数
        "avg": 3.5,         # 平均并发数
        "timeline": [
            {"time": "10:00:00.123", "count": 4},
            {"time": "10:00:01.456", "count": 5}
        ]
    }
}
```

### 3. 空闲分析 (Idle Time)

```python
{
    "idle_time": {
        "Unit1": {
            "total_idle_ms": 2000,
            "idle_periods": [
                {"start": "10:00:05", "end": "10:00:07", "duration_ms": 2000}
            ]
        }
    }
}
```

### 4. 瓶颈分析 (Bottleneck)

```python
{
    "bottlenecks": [
        {
            "unit": "Unit3",
            "task": "HeavyCompute",
            "duration_ms": 5000,
            "impact": "high",
            "suggestion": "考虑优化或并行化"
        }
    ]
}
```

## 与其他插件的配合

### 工作流位置

```
perf_parser → [perf_analyzer] → perf_visualizer
                    ↓
              计算性能指标
              (时长、并发、瓶颈)
```

### 数据流

1. **perf_parser** → tasks列表
2. **perf_analyzer** → 性能指标
3. **perf_visualizer** → 使用指标生成图表

### 配合示例

```yaml
perf_parser:
  enable: true

perf_analyzer:
  enable: true
  metrics:
    - duration
    - bottleneck
  thresholds:
    slow_task_ms: 500

perf_visualizer:
  enable: true
  # 使用 analyzer 计算的指标
  highlight_slow_tasks: true  # 高亮慢任务
```

## 示例输出

```
[性能分析] 开始分析性能数据...
  ✓ 解析任务: 156个

  时长分析:
    总执行时间: 10.5秒
    最长任务: Unit3/HeavyCompute (5.0秒)
    最短任务: Unit1/Initialize (0.05秒)
    平均时长: 67ms
    P95时长: 320ms

  并发分析:
    最大并发: 8个任务
    平均并发: 3.5个任务
    并发峰值时刻: 10:00:03.456

  瓶颈识别:
    ⚠️  发现3个瓶颈任务:
      1. Unit3/HeavyCompute (5.0秒) - 影响: 高
      2. Unit5/DataLoad (2.8秒) - 影响: 中
      3. Unit2/Network (1.5秒) - 影响: 中

  优化建议:
    → Unit3/HeavyCompute: 考虑并行化处理
    → Unit5/DataLoad: 使用缓存减少加载时间
    → Unit2/Network: 优化网络请求，使用连接池
```

## 分析方法

### analyze_duration()

分析任务时长：

```python
analyzer = PerfAnalyzer(config)
duration_data = analyzer.analyze_duration(tasks)

# 返回统计数据
```

### find_bottlenecks()

识别性能瓶颈：

```python
bottlenecks = analyzer.find_bottlenecks(tasks, threshold_ms=1000)

# 返回瓶颈任务列表
```

### calculate_concurrency()

计算并发度：

```python
concurrency_data = analyzer.calculate_concurrency(tasks)

# 返回时间线和统计数据
```

## 阈值配置

### 慢任务阈值

```yaml
thresholds:
  slow_task_ms: 1000  # 超过1秒的任务标记为慢任务
```

### 高并发阈值

```yaml
thresholds:
  high_concurrency: 5  # 并发数超过5标记为高并发
```

### 空闲时间阈值

```yaml
thresholds:
  idle_threshold_ms: 500  # 空闲超过500ms才记录
```

## 统计指标

### 百分位数 (Percentiles)

- **P50**: 中位数
- **P95**: 95%的任务在此时长内完成
- **P99**: 99%的任务在此时长内完成

### 使用场景

- **P50**: 了解典型性能
- **P95**: 优化目标（覆盖大部分情况）
- **P99**: 识别极端情况

## 常见问题

**Q: 如何定义"瓶颈任务"？**
A: 基于以下条件：
1. 任务时长超过阈值
2. 阻塞其他任务执行
3. 对总体性能影响大

**Q: 并发分析的准确性如何？**
A: 基于时间戳精确计算，精度取决于日志时间戳精度。

**Q: 可以导出分析数据吗？**
A: 可以，分析结果保存在context中，可被其他插件使用。

**Q: 如何优化分析性能？**
A: 对于大量任务（10万+），可以：
1. 启用采样分析
2. 只分析关键指标
3. 使用多进程分析
