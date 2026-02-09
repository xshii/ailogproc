# Perf Visualizer Plugin

性能可视化插件 - 生成性能时间线图表

## 功能

基于性能分析数据，生成可视化图表：
- **甘特图**: 任务执行时间线
- **并发度图表**: 并发任务数随时间变化
- **热力图**: 执行单元负载分布
- **交互式HTML**: 可缩放、可点击的图表

## 配置

```yaml
perf_visualizer:
  enable: true
  output_format: "html"     # html, png, svg
  output_dir: "output/"

  gantt:
    title: "性能时间线"
    show_duration: true     # 显示时长标签
    color_by: "unit"        # 按unit着色 (unit, task, duration)
    width: 1200
    height: 600

  zoom:
    enable: true            # 启用缩放
    slider: true            # 显示滑块
```

## 依赖

- **Level**: 3 (可视化层)
- **Dependencies**: `perf_parser`, `perf_analyzer`
- **被依赖**: 无

使用 **PyEcharts** 生成轻量级、交互式的图表。

## 命令行使用

```bash
# 完整分析+可视化
python main.py --mode perf performance.log

# 指定输出格式
python main.py --mode perf performance.log --output-format html

# 指定输出目录
python main.py --mode perf performance.log -o charts/

# 自定义图表标题
python main.py --mode perf performance.log --chart-title "系统性能分析"
```

## 生成的图表

### 1. 时间线甘特图

使用PyEcharts的Bar图模拟甘特图效果：

```
Unit1  ▓▓▓░░░░░░▓▓▓▓▓░░░░░▓▓
Unit2  ░░▓▓▓▓░░░░░░▓▓░░░░░░░
Unit3  ░░░░▓▓▓▓▓▓▓▓░░░░░░░░░
       │────────────────────│
       0s    5s    10s   15s
```

**特性**:
- 颜色编码（按Unit、Task或Duration）
- 悬停显示详细信息
- 时间轴缩放
- 数据缩放滑块

### 2. 交互功能

- **缩放**: 滚轮缩放时间轴
- **拖拽**: 平移查看不同时间段
- **悬停**: 显示任务详情（名称、时长、起止时间）
- **点击**: 高亮相关任务

## 与其他插件的配合

### 工作流位置

```
perf_parser → perf_analyzer → [perf_visualizer]
                                      ↓
                                 生成HTML图表
                                 (timeline.html)
```

### 数据流

1. **perf_parser**: 解析日志 → tasks列表
2. **perf_analyzer**: 计算指标 → 时长、并发等
3. **perf_visualizer**:
   - 使用tasks生成时间线
   - 使用指标着色和标注
   - 输出HTML文件

### 配合示例

```yaml
# 完整性能分析流程
perf_parser:
  enable: true

perf_analyzer:
  enable: true
  metrics:
    - duration
    - bottleneck

perf_visualizer:
  enable: true
  gantt:
    title: "任务执行时间线"
    color_by: "duration"      # 按时长着色
    highlight_slow: true       # 高亮慢任务（使用analyzer数据）
```

## PyEcharts实现

### 为什么选择PyEcharts？

相比Plotly，PyEcharts更轻量级：

| 特性 | Plotly | PyEcharts |
|------|--------|-----------|
| 依赖大小 | ~50MB | ~5MB |
| 加载速度 | 慢 | 快 |
| 中文支持 | 一般 | 优秀 |
| 自定义 | 复杂 | 简单 |

### 图表代码示例

```python
from pyecharts.charts import Bar

bar = Bar()
bar.add_xaxis(units)
bar.add_yaxis("任务", data, ...)
bar.set_global_opts(
    title_opts=opts.TitleOpts(title="性能时间线"),
    datazoom_opts=[opts.DataZoomOpts()]
)
bar.render("timeline.html")
```

## 示例输出

```
[性能可视化] 生成图表...
  → 解析任务: 156个
  → 执行单元: 8个
  → 时间范围: 10.5秒

  生成甘特图:
    ✓ 时间线图表: timeline.html
    - 宽度: 1200px
    - 高度: 600px
    - 交互: 启用

  图表特性:
    ✓ 按Unit着色
    ✓ 显示时长标签
    ✓ 缩放滑块
    ✓ 悬停提示

  输出文件:
    → output/timeline.html (1.2MB)
    ✓ 在浏览器中打开查看
```

## 图表配置

### 着色方案

**按执行单元着色** (color_by: "unit"):
```yaml
color_by: "unit"
# Unit1: 蓝色
# Unit2: 绿色
# Unit3: 红色
```

**按任务类型着色** (color_by: "task"):
```yaml
color_by: "task"
# Initialize: 浅蓝
# Process: 深蓝
# Finalize: 紫色
```

**按时长着色** (color_by: "duration"):
```yaml
color_by: "duration"
# 快速 (<100ms): 绿色
# 正常 (100-500ms): 黄色
# 慢速 (>500ms): 红色
```

### 时间轴配置

```yaml
gantt:
  time_format: "HH:mm:ss.SSS"   # 时间格式
  show_grid: true               # 显示网格
  grid_interval: 1000           # 网格间隔（ms）
```

### 标签配置

```yaml
gantt:
  show_labels: true             # 显示任务名
  show_duration: true           # 显示时长
  label_position: "inside"      # 标签位置 (inside, outside)
```

## 输出文件

### HTML格式

- **优点**: 交互式、可缩放、无需额外软件
- **缺点**: 文件较大（包含JavaScript）
- **适用**: 分析报告、团队分享

### PNG格式

- **优点**: 体积小、易于嵌入文档
- **缺点**: 静态、无交互
- **适用**: 文档、PPT

### SVG格式

- **优点**: 矢量图、缩放不失真
- **缺点**: 文件较大
- **适用**: 高质量打印、出版

## 性能优化

### 大量任务优化

对于大量任务（1000+）：

```yaml
# 启用采样
sampling:
  enable: true
  max_tasks: 500   # 最多显示500个任务

# 或聚合显示
aggregation:
  enable: true
  group_by: "unit"  # 按unit聚合
```

### 文件大小优化

```yaml
# 压缩输出
compression:
  enable: true
  level: 9          # 压缩级别 1-9

# 简化数据
simplify:
  enable: true
  merge_short_tasks: true   # 合并极短任务
  min_duration_ms: 10       # 只显示>10ms的任务
```

## 常见问题

**Q: 图表无法加载？**
A: 检查浏览器JavaScript是否启用，或使用现代浏览器（Chrome, Firefox, Edge）。

**Q: 如何导出为图片？**
A: 在浏览器中打开HTML，使用浏览器的"打印 → 保存为PDF"功能。

**Q: 时间线太长，无法查看全部？**
A: 使用缩放滑块或启用采样显示。

**Q: 可以自定义颜色吗？**
A: 可以，在配置中指定：
```yaml
colors:
  Unit1: "#FF5733"
  Unit2: "#33FF57"
```

**Q: 生成的HTML文件太大？**
A: 启用压缩和简化选项，或使用PNG格式。
