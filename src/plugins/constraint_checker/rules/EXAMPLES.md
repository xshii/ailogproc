# 约束规则配置示例

## 快速参考

### 单组约束类型

| 类型 | 说明 | 示例 |
|------|------|------|
| `only_allow` | 字段只能是指定值之一 | debugLevel只能是0/1/2/3 |
| `forbid` | 字段不能是指定值 | 禁止dangerousFlag=1 |
| `only_allow_combinations` | 多字段组合只能是指定组合 | (A,B,C)只能是(2,1,2)或(3,2,1) |

### 多组约束类型

| 类型 | 说明 | 示例 |
|------|------|------|
| `same_value` | 连续组的字段值必须相同 | 组1和组2的systemMode必须一致 |
| `sequence` | 连续组的字段值必须递增/递减 | configId必须递增 |
| `conditional` | if-then条件约束 | 如果组1是X，则组2必须是Y |
| `only_allow_combinations` | 组间组合映射 | 组1的(A,B)到组2的(X,Y)映射 |

---

## 示例1：简单字段值约束

```yaml
single_constraints:
  - name: "调试级别限制"
    when:
      systemMode: "1"
    only_allow:
      debugLevel: ["0", "1", "2", "3"]
```

**解释**：当systemMode=1时，debugLevel只能是0、1、2或3

---

## 示例2：字段组合约束

```yaml
single_constraints:
  - name: "功率配置组合"
    only_allow_combinations:
      - powerLevel: "5"
        voltage: "0.8V"
        frequency: "500MHz"

      - powerLevel: "10"
        voltage: "1.0V"
        frequency: "1.0GHz"

      - powerLevel: "15"
        voltage: "1.2V"
        frequency: "2.0GHz"
```

**解释**：powerLevel、voltage、frequency三个字段必须配套使用，只允许三种组合

**允许**：
- ✓ (5, 0.8V, 500MHz)
- ✓ (10, 1.0V, 1.0GHz)
- ✓ (15, 1.2V, 2.0GHz)

**禁止**：
- ✗ (5, 1.0V, 1.0GHz) - 不匹配任何允许的组合
- ✗ (10, 0.8V, 2.0GHz) - 不匹配任何允许的组合

---

## 示例3：多组字段一致性

```yaml
multi_constraints:
  - name: "系统模式一致性"
    group_count: 2
    rules:
      - type: "same_value"
        field: "systemMode"
```

**解释**：连续两个配置组的systemMode必须相同

**允许**：
- ✓ 组1: systemMode=1, 组2: systemMode=1
- ✓ 组1: systemMode=2, 组2: systemMode=2

**禁止**：
- ✗ 组1: systemMode=1, 组2: systemMode=2

---

## 示例4：多组组合映射

```yaml
multi_constraints:
  - name: "功率切换规则"
    group_count: 2
    only_allow_combinations:
      # 低→低
      - group0:
          powerLevel: "5"
          voltage: "0.8V"
        group1:
          powerLevel: "5"
          voltage: "0.8V"

      # 低→中
      - group0:
          powerLevel: "5"
          voltage: "0.8V"
        group1:
          powerLevel: "10"
          voltage: "1.0V"

      # 中→低
      - group0:
          powerLevel: "10"
          voltage: "1.0V"
        group1:
          powerLevel: "5"
          voltage: "0.8V"

      # 中→中
      - group0:
          powerLevel: "10"
          voltage: "1.0V"
        group1:
          powerLevel: "10"
          voltage: "1.0V"

      # 高→中（允许）
      - group0:
          powerLevel: "15"
          voltage: "1.2V"
        group1:
          powerLevel: "10"
          voltage: "1.0V"

      # 注意：高→低 不在列表中，因此被禁止
```

**解释**：定义允许的功率切换路径

**允许的切换**：
- ✓ 低(5)→低(5)
- ✓ 低(5)→中(10)
- ✓ 中(10)→低(5)
- ✓ 中(10)→中(10)
- ✓ 高(15)→中(10)

**禁止的切换**：
- ✗ 高(15)→低(5) - 不在允许列表中

---

## 示例5：完整配置示例

```yaml
version: "1.2.0"
date: "2024-02-08"

# ===== 单组约束 =====
single_constraints:
  # 基本约束
  - name: "系统模式1的限制"
    when:
      systemMode: "1"
    only_allow:
      debugLevel: ["0", "1", "2", "3"]
    forbid:
      dangerousFlag: ["1"]

  # 字段组合约束
  - name: "电源配置组合"
    only_allow_combinations:
      # 节能模式
      - powerMode: "eco"
        voltage: "0.8V"
        frequency: "500MHz"
        fanSpeed: "30%"

      # 性能模式
      - powerMode: "performance"
        voltage: "1.2V"
        frequency: "2.0GHz"
        fanSpeed: "80%"

# ===== 多组约束 =====
multi_constraints:
  # 一致性约束
  - name: "系统模式一致性"
    group_count: 2
    rules:
      - type: "same_value"
        field: "systemMode"

  # 递增约束
  - name: "配置ID递增"
    group_count: 3
    rules:
      - type: "sequence"
        field: "configId"
        order: "increasing"

  # 组合映射约束
  - name: "电源切换规则"
    group_count: 2
    only_allow_combinations:
      - group0: {powerMode: "eco", voltage: "0.8V"}
        group1: {powerMode: "eco", voltage: "0.8V"}

      - group0: {powerMode: "eco", voltage: "0.8V"}
        group1: {powerMode: "performance", voltage: "1.2V"}

      - group0: {powerMode: "performance", voltage: "1.2V"}
        group1: {powerMode: "performance", voltage: "1.2V"}
```

---

## 使用场景对照表

| 需求 | 使用的约束类型 | 示例 |
|------|----------------|------|
| 限制单个字段的值 | `only_allow` 或 `forbid` | debugLevel只能0-3 |
| 多个字段必须配套 | `only_allow_combinations` (单组) | (功率,电压,频率)组合 |
| 相邻组字段值一致 | `same_value` | systemMode必须一致 |
| 字段值递增/递减 | `sequence` | configId递增 |
| 状态转换限制 | `only_allow_combinations` (多组) | 功率切换路径 |
| 条件依赖 | `conditional` | if A=1 then B必须<5 |

---

## 调试技巧

### 1. 查看使用的规则版本

```bash
# 查看日志输出
[约束检查] 使用规则版本: 1.2.0_20240208
```

### 2. 禁用约束检查

```yaml
# config.yaml
enable: false
```

### 3. 指定规则版本

```yaml
# config.yaml
active_version: "1.1.0_20240208"
```

### 4. 查看违规详情

违规消息格式：
```
[组2] 功率配置组合: 字段组合 (powerLevel=10, voltage=0.8V, frequency=2.0GHz)
不在允许列表中。允许的组合: (powerLevel=5, voltage=0.8V, frequency=500MHz),
(powerLevel=10, voltage=1.0V, frequency=1.0GHz), ...
```

---

## 常见问题

### Q1: 如何表达"A=2且B=1时，C只能是2或3"？

**方案1（推荐）**：使用组合约束
```yaml
only_allow_combinations:
  - A: "2"
    B: "1"
    C: "2"
  - A: "2"
    B: "1"
    C: "3"
```

**方案2**：使用条件约束（未来支持）
```yaml
validate:
  expression: "(A=='2' and B=='1') implies (C in ['2','3'])"
```

### Q2: 组合数量很多（>50个）怎么办？

使用矩阵格式：
```yaml
only_allow_combinations:
  fields: [A, B, C]
  values:
    - ["2", "1", "2"]
    - ["2", "1", "3"]
    - ["3", "2", "1"]
    # ... 更多组合
```

### Q3: 如何表达"除了X,Y,Z组合外都允许"？

当前不支持否定逻辑。建议：
1. 列出所有允许的组合
2. 或使用表达式（未来支持）

### Q4: 字段值可以是范围吗？

当前版本不支持。未来可以使用表达式：
```yaml
validate:
  expression: "powerLevel >= 0 and powerLevel <= 100"
```

---

## 版本升级指南

### 从 v1.1.0 升级到 v1.2.0

**新增功能**：
- ✅ `only_allow_combinations` - 字段组合约束

**向后兼容**：
- ✅ 所有 v1.1.0 的配置在 v1.2.0 中继续有效

**迁移步骤**：
1. 无需修改现有配置
2. 如需使用新功能，添加 `only_allow_combinations` 配置

**示例迁移**：

**旧配置（v1.1.0）**：
```yaml
# 分别限制每个字段
- name: "功率限制"
  only_allow:
    powerLevel: ["5", "10", "15"]
    voltage: ["0.8V", "1.0V", "1.2V"]
```

**新配置（v1.2.0）**：
```yaml
# 更精确：限制字段组合
- name: "功率限制"
  only_allow_combinations:
    - powerLevel: "5"
      voltage: "0.8V"
    - powerLevel: "10"
      voltage: "1.0V"
    - powerLevel: "15"
      voltage: "1.2V"
```

区别：
- 旧配置允许 (5, 1.2V) - 不合理的组合
- 新配置只允许配套的组合
