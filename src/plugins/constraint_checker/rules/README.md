# 约束规则目录说明

## 目录结构

```
rules/
├── README.md                    # 本文件
├── versions.yaml                # 版本索引（必需）
├── EXAMPLES.md                  # 配置示例
├── v1.0.0_20240115.yaml        # 版本1.0.0规则
├── v1.1.0_20240208.yaml        # 版本1.1.0规则
└── v1.2.0_20240208.yaml        # 版本1.2.0规则（最新）
```

## 版本管理

### 当前版本

| 版本 | 日期 | 说明 | 状态 |
|------|------|------|------|
| 1.0.0 | 2024-01-15 | 初始版本 | 稳定 |
| 1.1.0 | 2024-02-08 | 增强版本 - 三组级联 | 稳定 |
| 1.2.0 | 2024-02-08 | **字段组合约束** | **最新** ⭐ |

### 版本选择

**自动使用最新版本**（默认）：
```yaml
# config.yaml
active_version: null  # 自动使用 v1.2.0
```

**指定固定版本**（生产环境推荐）：
```yaml
# config.yaml
active_version: "1.1.0_20240208"
```

## 功能对比

### v1.0.0 - 基础功能

✅ 单组约束：
- `only_allow` - 字段值白名单
- `forbid` - 字段值黑名单

✅ 多组约束：
- `same_value` - 字段值一致性

### v1.1.0 - 增强功能

✅ 在 v1.0.0 基础上新增：

**多组约束**：
- `sequence` - 字段值序列检查（递增/递减）
- `conditional` - 条件约束（if-then逻辑）
- 支持三组级联约束

### v1.2.0 - 组合约束（当前最新 ⭐）

✅ 在 v1.1.0 基础上新增：

**单组约束**：
- `only_allow_combinations` - 多字段组合约束
  ```yaml
  only_allow_combinations:
    - A: "2"
      B: "1"
      C: "2"
    - A: "3"
      B: "2"
      C: "1"
  ```

**多组约束**：
- `only_allow_combinations` - 组间组合映射
  ```yaml
  only_allow_combinations:
    - group0: {A: "2", B: "1"}
      group1: {X: "1", Y: "2"}
    - group0: {A: "3", B: "2"}
      group1: {X: "2", Y: "3"}
  ```

## 快速开始

### 1. 查看示例

```bash
cat rules/EXAMPLES.md
```

### 2. 选择版本

编辑 `config.yaml`：
```yaml
constraint_checker:
  enable: true
  active_version: null  # 或指定版本号
```

### 3. 创建新版本

```bash
# 复制最新版本
cp rules/v1.2.0_20240208.yaml rules/v1.3.0_YYYYMMDD.yaml

# 编辑新版本
vim rules/v1.3.0_YYYYMMDD.yaml

# 更新版本索引
vim rules/versions.yaml
```

**版本索引示例**：
```yaml
versions:
  - version: "1.3.0"
    date: "2024-02-10"
    file: "v1.3.0_20240210.yaml"
    description: "新增功能描述"
    deprecated: false
```

### 4. 测试新版本

```bash
# 指定版本测试
python main.py --log-level DEBUG

# 查看日志确认版本
# [约束检查] 使用规则版本: 1.3.0_20240210
```

## 规则文件格式

### 完整结构

```yaml
# 文件头（元数据）
version: "x.y.z"
date: "YYYY-MM-DD"
description: "版本描述"
author: "作者"
changelog:
  - "变更1"
  - "变更2"

# 单组约束
single_constraints:
  - name: "约束名称"
    description: "说明"
    when:                    # 可选：触发条件
      field1: "value1"
    only_allow:              # 可选：白名单
      field2: ["val1", "val2"]
    forbid:                  # 可选：黑名单
      field3: ["val3"]
    only_allow_combinations: # 可选：组合约束
      - fieldA: "value"
        fieldB: "value"

# 多组约束
multi_constraints:
  - name: "约束名称"
    group_count: 2           # 必需：组数（2或3）
    rules:                   # 传统方式
      - type: "same_value"
        field: "fieldName"
    only_allow_combinations: # 新方式：组合映射
      - group0: {field: "val"}
        group1: {field: "val"}
```

### 字段说明

| 字段 | 必需 | 说明 |
|------|------|------|
| `version` | ✅ | 版本号（语义化版本） |
| `date` | ✅ | 创建日期 YYYY-MM-DD |
| `description` | ❌ | 版本描述 |
| `single_constraints` | ✅ | 单组约束列表 |
| `multi_constraints` | ❌ | 多组约束列表 |

## 最佳实践

### 1. 版本命名

```
格式: vMAJOR.MINOR.PATCH_YYYYMMDD.yaml

示例:
v1.0.0_20240115.yaml  # 主版本1，次版本0，修订版0
v1.1.0_20240208.yaml  # 新增功能（次版本+1）
v1.1.1_20240210.yaml  # Bug修复（修订版+1）
v2.0.0_20240301.yaml  # 不兼容变更（主版本+1）
```

### 2. 变更管理

**每次新建版本**：
1. 更新 `changelog` 说明变更
2. 在 `versions.yaml` 中添加记录
3. 保留旧版本文件（不删除）

### 3. 生产环境

- ✅ 指定固定版本（`active_version: "1.2.0_20240208"`）
- ✅ 充分测试后再更新版本
- ✅ 保留回退能力（旧版本文件）

### 4. 开发/测试环境

- ✅ 使用最新版本（`active_version: null`）
- ✅ 频繁迭代规则
- ✅ 验证新功能

## 规则编写技巧

### 1. 从简单到复杂

```yaml
# 阶段1：基本约束
only_allow:
  debugLevel: ["0", "1", "2"]

# 阶段2：组合约束
only_allow_combinations:
  - debugLevel: "0"
    powerMode: "low"
  - debugLevel: "2"
    powerMode: "high"
```

### 2. 使用YAML锚点复用

```yaml
# 定义可复用的配置
definitions:
  low_power: &low_power
    powerLevel: "5"
    voltage: "0.8V"

  high_power: &high_power
    powerLevel: "15"
    voltage: "1.2V"

# 使用
only_allow_combinations:
  - *low_power
  - *high_power
```

### 3. 添加注释和说明

```yaml
- name: "功率切换规则"
  description: "防止高功率直接切到低功率，需要中间过渡"
  only_allow_combinations:
    # 低→中（安全）
    - group0: {powerLevel: "5"}
      group1: {powerLevel: "10"}

    # 高→低（禁止，不在列表中）
```

### 4. 矩阵格式（大量组合）

```yaml
only_allow_combinations:
  fields: [A, B, C]
  values:
    - ["2", "1", "2"]  # 组合1
    - ["3", "2", "1"]  # 组合2
  comments:
    - "低功率配置"
    - "高功率配置"
```

## 故障排查

### 1. 查看当前使用的版本

```bash
python main.py --log-level DEBUG 2>&1 | grep "使用规则版本"
```

输出：
```
[约束检查] 使用规则版本: 1.2.0_20240208
```

### 2. 验证规则文件语法

```bash
python -c "import yaml; yaml.safe_load(open('rules/v1.2.0_20240208.yaml'))"
```

### 3. 常见错误

**错误1**：`FileNotFoundError`
```
原因：versions.yaml中的file路径错误
解决：检查文件名是否匹配
```

**错误2**：版本不生效
```
原因：active_version指定了错误的版本号
解决：检查版本号格式（不要包含.yaml后缀）
```

**错误3**：约束未触发
```
原因：when条件不匹配
解决：检查字段名和值是否完全匹配（区分大小写）
```

## 性能考虑

### 规则数量建议

| 约束类型 | 建议数量 | 最大数量 |
|---------|---------|---------|
| 单组约束 | < 20 | 100 |
| 多组约束 | < 10 | 50 |
| 组合数（每个约束） | < 10 | 100 |

### 优化技巧

1. **避免过度约束**：只添加必要的约束
2. **合并相似规则**：使用组合约束代替多个单一约束
3. **使用条件触发**：用`when`减少检查次数

## 相关文档

- [EXAMPLES.md](EXAMPLES.md) - 配置示例
- [../README.md](../README.md) - 插件使用文档
- [../SOTA_CONSTRAINT_DESIGN.md](../SOTA_CONSTRAINT_DESIGN.md) - 设计方案
- [../MULTI_GROUP_COMBINATION_DESIGN.md](../MULTI_GROUP_COMBINATION_DESIGN.md) - 多组组合设计

## 联系支持

遇到问题？
1. 查看 [EXAMPLES.md](EXAMPLES.md) 获取示例
2. 启用 DEBUG 日志：`python main.py --log-level DEBUG`
3. 查看违规详细信息

---

**最后更新**: 2024-02-08
**维护者**: Team
