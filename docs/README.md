# 文档目录

## 架构设计文档

### 插件系统
- [插件系统总览](./PLUGINS_OVERVIEW.md) - 完整的插件架构、依赖关系和使用指南

### 性能日志处理
- [性能日志处理架构](./PERFORMANCE_LOG_ARCHITECTURE.md) - 完整的性能日志处理框架设计
- [性能日志规划总结](./PERF_SUMMARY.md) - 当前进度和下一步工作

### 配置日志处理插件

- [Config Parser](../src/plugins/config_parser/README.md) - 配置解析插件，解析日志文件
- [Excel Writer](../src/plugins/excel_writer/README.md) - Excel填充插件，填充模板
- [Auto Filename](../src/plugins/auto_filename/README.md) - 自动文件名插件，生成文件名后缀
- [Constraint Checker](../src/plugins/constraint_checker/README.md) - 约束检查插件，验证配置规则
- [DLD Config Tmp](../src/plugins/dld_configtmp/README.md) - 模板下载插件，获取最新模板

### 性能日志处理插件

- [Perf Parser](../src/plugins/perf_parser/README.md) - 性能日志解析插件
- [Perf Analyzer](../src/plugins/perf_analyzer/README.md) - 性能分析插件，计算指标
- [Perf Visualizer](../src/plugins/perf_visualizer/README.md) - 性能可视化插件，生成图表
- [Data Parser](../src/plugins/data_parser/README.md) - 数据解析插件，提取二进制数据

## 代码质量文档

- [代码质量分析报告](./CODE_QUALITY_REVIEW.md) - 完整的代码质量分析和重构建议
- [重构指南](./REFACTORING_GUIDE.md) - 数据类使用指南和重构最佳实践
- [覆盖率报告](./COVERAGE.md) - 测试覆盖率分析
- [质量门禁](./QUALITY_GATE.md) - 代码质量标准

## 开发文档

- [工作流说明](./WORKFLOW.md) - 完整的处理流程和工作流说明
- [插件依赖关系](./PLUGIN_DEPENDENCIES.md) - 插件系统架构和依赖关系

## 快速导航

### 对于用户
- **处理配置日志（填表 + 约束检查）**: 见项目根目录 `README.md`
- **处理性能日志（时间线分析）**: 见 [性能日志处理架构](./PERFORMANCE_LOG_ARCHITECTURE.md)

### 对于开发者
- **代码质量改进**: 见 [代码质量分析报告](./CODE_QUALITY_REVIEW.md)
- **重构参考**: 见 [重构指南](./REFACTORING_GUIDE.md)
- **测试覆盖**: 见 [覆盖率报告](./COVERAGE.md)

## 文档结构

```
docs/
├── README.md                           # 本文件
├── CODE_QUALITY_REVIEW.md              # 代码质量分析
├── REFACTORING_GUIDE.md                # 重构指南
├── COVERAGE.md                         # 覆盖率报告
├── QUALITY_GATE.md                     # 质量门禁
├── WORKFLOW.md                         # 工作流说明
├── PLUGIN_DEPENDENCIES.md              # 插件依赖
├── PERFORMANCE_LOG_ARCHITECTURE.md     # 性能日志架构
└── PERF_SUMMARY.md                     # 性能日志规划
```
