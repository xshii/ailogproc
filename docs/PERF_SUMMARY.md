# 性能日志处理框架 - 规划总结

## ✅ 已完成的工作

### 1. 目录结构创建

```
src/plugins/
├── perf_parser/           ✅ 已创建
│   ├── __init__.py
│   ├── plugin.py
│   └── config.yaml
├── perf_analyzer/         ✅ 已创建
│   ├── __init__.py
│   ├── plugin.py
│   └── config.yaml
└── perf_visualizer/       ✅ 已创建
    ├── __init__.py
    ├── plugin.py
    └── config.yaml
```

### 2. 核心功能设计

#### perf_parser（性能日志解析器）
- ✅ 支持多组提取规则配置
- ✅ 使用正则表达式 + 命名捕获组提取字段
- ✅ 灵活的字段匹配条件
- ✅ 自动计算性能指标（cycle差值）

**配置结构：**
```yaml
extraction_rules:
  - name: "规则名称"
    start_pattern:
      regex: '正则表达式(?P<字段名>...)'
      fields:
        字段名: {type: "string|int", required: true}
    end_pattern:
      regex: '正则表达式(?P<字段名>...)'
      fields: {...}
    match_fields: ["字段1", "字段2"]  # 匹配条件
    performance:
      duration_field: "duration_cycles"
      formula: "end - start"
```

#### perf_analyzer（性能数据分析器）
- ✅ 统计指标计算（min, max, mean, p50, p90, p95, p99）
- ✅ 按执行单元分组统计
- ✅ 异常值检测（3种方法：IQR/Z-score/百分位）
- ✅ 生成JSON和CSV报告

#### perf_visualizer（性能可视化器）
- ✅ 算子执行时间线图（升腾Studio风格）
- ✅ 甘特图横向展示
- ✅ 按执行单元分行显示
- ✅ 交互式HTML（Plotly）
- ✅ 可选：耗时分布直方图

## 🎯 关键特性

### 1. 多组规则支持
可以同时定义多组不同的提取规则，处理不同格式的日志：
- 通用任务
- AI算子执行
- 数据传输
- 自定义规则...

### 2. 灵活的匹配逻辑
- 支持多字段组合匹配
- 字段类型转换（string/int）
- 可选字段（required: false）

### 3. 自动性能计算
```yaml
performance:
  duration_field: "duration_cycles"
  formula: "cycle_end - cycle_start"
```

### 4. 专业可视化
类似升腾 Ascend Studio 的效果：
- 时间轴横向展开
- 执行单元纵向分组
- 悬停显示详情
- 支持缩放

## 📋 下一步工作

### 待实现的内容

1. **实现 perf_parser 插件核心逻辑** ⚠️
   - [ ] 多规则匹配引擎
   - [ ] 字段提取和类型转换
   - [ ] 开始/结束事件关联
   - [ ] 性能指标计算

2. **完善 perf_analyzer** ⚠️
   - [x] 基础统计实现（已完成）
   - [ ] 测试异常值检测
   - [ ] CSV格式优化

3. **优化 perf_visualizer** ⚠️
   - [x] 基础甘特图实现（已完成）
   - [ ] 颜色方案优化
   - [ ] 更多图表类型

4. **创建入口脚本**
   ```bash
   # perf_main.py
   python perf_main.py perf_log.txt
   ```

5. **编写测试用例**
   - [ ] perf_parser 单元测试
   - [ ] perf_analyzer 单元测试
   - [ ] 端到端集成测试

6. **文档和示例**
   - [ ] 用户手册
   - [ ] 示例日志文件
   - [ ] 配置模板

## 💡 使用示例

### 场景：AI模型性能分析

**日志格式：**
```
OP_START opType:Conv2D opId:001 core:NPU0 cycle:1000
OP_END opType:Conv2D opId:001 core:NPU0 cycle:1250
OP_START opType:ReLU opId:002 core:NPU0 cycle:1260
OP_END opType:ReLU opId:002 core:NPU0 cycle:1280
```

**配置：**
```yaml
extraction_rules:
  - name: "算子执行"
    start_pattern:
      regex: 'OP_START.*opType:\s*(?P<op_type>\w+).*opId:\s*(?P<op_id>\d+).*core:\s*(?P<core>\w+).*cycle:\s*(?P<start_cycle>\d+)'
    end_pattern:
      regex: 'OP_END.*opType:\s*(?P<op_type>\w+).*opId:\s*(?P<op_id>\d+).*core:\s*(?P<core>\w+).*cycle:\s*(?P<end_cycle>\d+)'
    match_fields: ["op_type", "op_id", "core"]
    performance:
      formula: "end_cycle - start_cycle"
```

**输出：**
- `output/perf_analysis.json` - 统计报告
- `output/perf_analysis.csv` - 原始数据
- `output/perf_gantt.html` - 可视化时间线

## 🔧 技术选型

| 组件 | 技术 | 原因 |
|------|------|------|
| 日志解析 | 正则表达式 + 命名捕获组 | 灵活、易配置 |
| 数据处理 | Python标准库 | 无额外依赖 |
| 可视化 | Plotly | 交互式、专业 |
| 报告 | JSON + CSV | 通用格式 |

## 📊 架构优势

✅ **插件化** - 遵循现有框架，易于集成
✅ **配置驱动** - YAML配置，无需修改代码
✅ **多场景支持** - 一套框架处理多种日志
✅ **专业可视化** - 升腾Studio级别的效果
✅ **扩展性强** - 添加规则只需编辑配置

---

**当前状态：** 📐 架构规划完成，待实现核心逻辑

**预计工作量：** 
- perf_parser 核心实现：4-6小时
- 测试和调试：2-3小时
- 文档完善：1-2小时
