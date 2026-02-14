# 配置约束检查插件

## 功能概述

该插件用于验证配置是否满足预定义的约束条件，支持：

1. **单组约束**：针对单个配置组内字段的约束
   - `only_allow`: 字段值仅允许在指定列表中
   - `forbid`: 字段值禁止在指定列表中
   - `only_allow_combinations`: 多字段组合只能是指定的组合之一

2. **多组约束**：针对连续 2-3 个配置组之间的约束（滑动窗口）
   - `same_value`: 多组间同一字段值必须相同
   - `sequence`: 字段值必须满足递增/递减序列
   - `conditional`: 条件约束，如果组A满足条件，则组B必须满足约束
   - `only_allow_combinations`: 多组间字段组合只能是指定的组合对之一

3. **关联约束**（v1.4.0+）：针对非连续配置组的跨算子约束
   - 通过 `associate_by` 定义角色（src1/src2/src3）和关联方式
   - 支持同字段匹配、跨字段匹配、多字段联合匹配
   - 支持线性链、扇入、扇出等拓扑结构
   - 复用所有多组约束类型 + `validate` 表达式
   - 适用于算子间有插排、配置日志非连续的场景

4. **字段前缀命名**：所有字段使用 `sectionName.fieldName` 格式
   - top 表字段：`opSch.powerLevel`、`opSch.systemMode`
   - 子表字段：`ERCfg.cfgGroup`、`I2C.0.speed`、`I2C.1.speed`

5. **版本管理**：按版本管理约束规则，支持版本号+日期后缀

## 插件信息

- **Level**: 2（验证层）
- **依赖**: `config_parser`
- **执行时机**: 在 `config_parser` 之后、`excel_writer` 之前

## 配置文件结构

```yaml
enable: true

# 使用的规则版本（null 表示自动使用最新版本）
active_version: null

# 仅检查模式：true 时检查完约束后停止后续插件执行
check_only: false

# 是否生成 JSON 违规报告
generate_report: true

# 报告输出路径（null 表示使用默认路径 output/constraint_report.json）
report_path: null

# 规则目录（相对于插件目录的路径）
rules_dir: "rules"
```

## 约束类型详解

### 1. 单组约束

#### only_allow（仅允许）

当触发条件满足时，指定字段的值必须在允许列表中。

```yaml
- name: "系统模式1下的参数限制"
  description: "限制调试级别和功率模式的取值范围，防止不安全的配置组合"
  when:
    opSch.systemMode: "1"
  only_allow:
    opSch.debugLevel: ["0", "1", "2"]
```

#### forbid（禁止）

当触发条件满足时，指定字段的值不能在禁止列表中。

```yaml
- name: "高级调试模式的生产配置禁止"
  description: "避免调试配置与生产配置混用导致异常"
  when:
    opSch.debugLevel: "3"
  forbid:
    opSch.productionMode: ["1", "enabled"]
```

#### only_allow_combinations（字段组合约束）

多个字段必须配套使用，只允许指定的组合。

```yaml
- name: "功率-电压-频率配套约束"
  description: "功率等级、电压等级、频率模式三者必须配套，防止硬件损坏"
  when:
    opSch.systemMode: "1"
  only_allow_combinations:
    - opSch.powerLevel: "5"
      opSch.voltageLevel: "1"
      opSch.frequencyMode: "low"
    - opSch.powerLevel: "10"
      opSch.voltageLevel: "2"
      opSch.frequencyMode: "medium"
```

### 2. 多组约束（滑动窗口）

#### same_value（相同值）

连续多组配置中，指定字段的值必须相同。

```yaml
- name: "相邻配置组系统模式一致性"
  description: "防止连续操作中出现模式突变导致系统状态不连续"
  group_count: 2
  rules:
    - type: "same_value"
      field: "opSch.systemMode"
```

#### sequence（序列）

连续多组配置中，指定字段的值必须满足递增或递减。

```yaml
- name: "连续三组配置ID严格递增"
  description: "确保配置的执行顺序正确，避免重复或乱序执行"
  group_count: 3
  rules:
    - type: "sequence"
      field: "opSch.configId"
      order: "increasing"  # 或 "decreasing"
```

#### conditional（条件约束）

如果某组满足条件，则另一组必须满足约束。

```yaml
- name: "功率模式级联降档保护"
  description: "高功率不允许直接切换到低功率，防止电压跌落"
  group_count: 2
  rules:
    - type: "conditional"
      when_group: 0
      when_field: "opSch.powerMode"
      when_value: "high"
      then_group: 1
      then_field: "opSch.powerMode"
      forbid: ["low"]
```

#### only_allow_combinations（组间组合映射）

定义允许的组间状态转换路径。

```yaml
- name: "功率等级切换路径白名单"
  description: "只允许保持当前等级或相邻等级间切换，防止电压骤降"
  group_count: 2
  only_allow_combinations:
    - group0:
        opSch.powerLevel: "5"
      group1:
        opSch.powerLevel: "5"
    - group0:
        opSch.powerLevel: "5"
      group1:
        opSch.powerLevel: "10"
```

### 3. 关联约束（v1.4.0+）

通过 `associate_by` 定义角色和关联方式，支持非连续组的约束检查。适用于算子调度导致配置日志交错的场景。

#### 核心概念

```yaml
associate_by:
  src1:                           # 角色1定义
    where: { opSch.opType: "dma" }   # 角色识别条件
  src2:                           # 角色2定义
    where: { opSch.opType: "compute" }
  src3:                           # 角色3（可选，最多3个）
    where: { opSch.opType: "output" }
  links:                          # 关联条件列表
    - { src1: "opSch.channelId", src2: "opSch.channelId" }   # 同字段匹配
    - { src2: "opSch.outBufId", src3: "opSch.inBufId" }      # 跨字段匹配
```

- **where**: 根据字段值匹配角色，支持 `"*"` 通配符（字段存在即可）
- **links**: 定义角色间的关联字段，每对关联独立描述
- **角色**: 最多 3 个（src1/src2/src3），支持多种拓扑

#### 示例：两算子同字段关联

```yaml
- name: "DMA与计算算子通道一致性"
  description: "同一通道上 DMA 和计算算子的 systemMode 必须一致"
  associate_by:
    src1:
      where: { opSch.opType: "dma" }
    src2:
      where: { opSch.opType: "compute" }
    links:
      - { src1: "opSch.channelId", src2: "opSch.channelId" }
  rules:
    - type: "same_value"
      field: "opSch.systemMode"
```

#### 示例：两算子跨字段关联

```yaml
- name: "生产者到消费者功率约束"
  description: "消费者的功率等级不能高于生产者，防止下游功率过载"
  associate_by:
    src1:
      where: { opSch.opType: "producer" }
    src2:
      where: { opSch.opType: "consumer" }
    links:
      - { src1: "opSch.outputPort", src2: "opSch.inputPort" }
  rules:
    - type: "conditional"
      when_group: "src1"
      when_field: "opSch.powerLevel"
      when_value: "5"
      then_group: "src2"
      then_field: "opSch.powerLevel"
      only_allow: ["5"]
```

#### 示例：三算子线性链

```yaml
- name: "三级流水线功率递减"
  description: "DMA→计算→输出三级流水线中，功率等级必须逐级递减"
  associate_by:
    src1:
      where: { opSch.opType: "dma" }
    src2:
      where: { opSch.opType: "compute" }
    src3:
      where: { opSch.opType: "output" }
    links:
      - { src1: "opSch.channelId", src2: "opSch.channelId" }
      - { src2: "opSch.outBufId", src3: "opSch.inBufId" }
  rules:
    - type: "sequence"
      groups: ["src1", "src2", "src3"]
      field: "opSch.powerLevel"
      order: "decreasing"
```

#### 示例：组合白名单

```yaml
- name: "三级流水线功率切换白名单"
  description: "三级流水线各级功率只允许指定的组合"
  associate_by:
    src1:
      where: { opSch.opType: "dma" }
    src2:
      where: { opSch.opType: "compute" }
    src3:
      where: { opSch.opType: "output" }
    links:
      - { src1: "opSch.channelId", src2: "opSch.channelId" }
      - { src2: "opSch.outBufId", src3: "opSch.inBufId" }
  only_allow_combinations:
    - src1: { opSch.powerLevel: "15" }
      src2: { opSch.powerLevel: "10" }
      src3: { opSch.powerLevel: "5" }
    - src1: { opSch.powerLevel: "10" }
      src2: { opSch.powerLevel: "10" }
      src3: { opSch.powerLevel: "5" }
```

#### 示例：表达式约束（validate）

```yaml
- name: "缓冲区大小与数据速率匹配"
  description: "计算算子的缓冲区大小必须>=DMA数据速率的2倍"
  associate_by:
    src1:
      where: { opSch.opType: "dma" }
    src2:
      where: { opSch.opType: "compute" }
    links:
      - { src1: "opSch.channelId", src2: "opSch.channelId" }
  validate:
    - expr: "src2.opSch.bufSize >= src1.opSch.dataRate * 2"
      message: "计算算子缓冲区大小必须>=DMA数据速率的2倍"
```

表达式求值优先使用 CEL 引擎（需安装 `cel-python`），不可用时自动回退到内置 AST 安全求值器。支持比较、算术、逻辑运算和属性访问，不允许函数调用等危险操作。

#### 示例：扇出拓扑

```yaml
- name: "调度器到双工作者功率约束"
  description: "两个工作者的功率模式必须与调度器一致"
  associate_by:
    src1:
      where: { opSch.opType: "scheduler" }
    src2:
      where: { opSch.opType: "workerA" }
    src3:
      where: { opSch.opType: "workerB" }
    links:
      - { src1: "opSch.groupId", src2: "opSch.groupId" }
      - { src1: "opSch.groupId", src3: "opSch.groupId" }
  rules:
    - type: "same_value"
      groups: ["src1", "src2", "src3"]
      field: "opSch.powerMode"
```

### 关联约束 vs 滑动窗口

| 特性 | 滑动窗口 (`group_count`) | 关联约束 (`associate_by`) |
|------|--------------------------|---------------------------|
| 组的关系 | 物理连续 | 逻辑关联（可不连续） |
| 组的识别 | 位置索引 (0, 1, 2) | 角色名 (src1, src2, src3) |
| 适用场景 | 相邻配置组检查 | 跨算子、交错日志检查 |
| 约束类型 | 共享同一套约束引擎 | 共享同一套约束引擎 |

## 字段命名规范

所有字段必须使用 `sectionName.fieldName` 格式：

| 字段类型 | 格式 | 示例 |
|----------|------|------|
| top 表字段 | `topName.fieldName` | `opSch.powerLevel` |
| 子表字段（唯一） | `subName.fieldName` | `ERCfg.cfgGroup` |
| 子表字段（重复） | `subName.索引.fieldName` | `I2C.0.speed`、`I2C.1.speed` |

## 规则编写建议

### name 和 description 的编写规范

- **name**：简洁的约束名称，使用纯中文描述，避免混入原始字段名
  - 好：`"功率模式级联降档保护"`
  - 差：`"opSch功率等级组合约束"`

- **description**：说明约束存在的 **原因**（why），而不仅仅是约束的内容（what）
  - 好：`"高功率不允许直接切换到低功率，防止电压骤降导致硬件损坏"`
  - 差：`"功率等级约束"`

### 使用场景对照表

| 需求 | 使用的约束类型 | 示例 |
|------|----------------|------|
| 限制单个字段的值 | `only_allow` 或 `forbid` | debugLevel 只能 0-3 |
| 多个字段必须配套 | `only_allow_combinations`（单组） | (功率,电压,频率) 组合 |
| 相邻组字段值一致 | `same_value` + `group_count` | systemMode 必须一致 |
| 字段值递增/递减 | `sequence` + `group_count` | configId 递增 |
| 状态转换限制 | `only_allow_combinations`（多组） | 功率切换路径 |
| 条件依赖 | `conditional` | 如果 A=high 则 B 不能是 low |
| 非连续组关联 | `associate_by` + 任意约束类型 | 跨算子通道一致性 |
| 数值表达式约束 | `validate` | bufSize >= dataRate * 2 |

## 架构说明（v1.4.0 统一架构）

v1.4.0 对内部架构进行了重构，统一了滑动窗口和关联约束的检查逻辑：

- **滑动窗口**：将连续的 N 组窗口转换为角色分配 (`group0`, `group1`, ...)
- **关联约束**：通过 where 条件和 links 匹配角色分配 (`src1`, `src2`, `src3`)
- **统一检查引擎**：`_check_constraints_on_assignment()` 接收角色分配，执行 same_value / sequence / conditional / combinations / validate

这意味着所有约束类型（same_value, sequence, conditional, combinations, validate）对滑动窗口和关联约束通用，无需重复实现。

表达式求值使用基于 AST 白名单的安全求值器，仅允许比较、算术、逻辑运算和属性访问，杜绝代码注入风险。

## 版本管理

### 版本历史

| 版本 | 日期 | 主要变更 |
|------|------|----------|
| v1.0.0 | 2024-01-15 | 初始版本：only_allow、forbid、same_value、conditional |
| v1.1.0 | 2024-02-08 | 新增 sequence、三组级联、多条件触发 |
| v1.2.0 | 2024-02-08 | 新增 only_allow_combinations（单组和多组） |
| v1.3.0 | 2024-02-08 | 字段统一使用 `sectionName.fieldName` 前缀格式，支持子表约束 |
| v1.4.0 | 2024-02-10 | 新增 associate_by 关联约束，统一检查引擎，AST 安全表达式求值 |

## 输出结果

插件返回：

```python
{
    'validation_passed': True/False,  # 是否通过
    'violations': [                   # 违规列表
        {
            'type': 'only_allow',     # 约束类型
            'rule': '规则名称',
            'field': '字段名',
            'value': '实际值',
            'message': '详细错误信息'
        }
    ],
    'version': '1.4.0_20240210'       # 使用的规则版本
}
```

### 违规消息格式

| 约束类型 | 消息格式 |
|----------|----------|
| only_allow | `[组0] 规则名: 字段 'X' 的值 'Y' 不在允许列表 ['a', 'b'] 中` |
| forbid | `[组0] 规则名: 字段 'X' 的值 'Y' 在禁止列表 ['a', 'b'] 中` |
| same_value | `[组[0,1]] 规则名: 字段 'X' 在各组中的值不一致: ['1', '2']` |
| same_value (关联) | `[src1=组0, src2=组3] 规则名: 字段 'X' 在各组中的值不一致: ['1', '2']` |
| sequence | `[组[0,1,2]] 规则名: 字段 'X' 的值 [3,1,2] 不满足递增序列` |
| conditional | `[组[0,1]] 规则名: 当 0(组0) 的 X=high 时，1(组1) 的 Y 不应为 'low'` |
| combinations | `[src1=组0, src2=组1] 规则名: 字段组合 (...) 不在允许的 N 个组合中` |
| validate | `[src1=组0, src2=组1] 规则名: 自定义错误消息` |

## 开发指南

### 添加新的约束类型

1. 在 `_check_constraints_on_assignment()` 中添加分发逻辑
2. 实现新的检查方法（参考 `_check_same_value`、`_check_sequence` 等）
3. 新方法接收统一的 `role_assignment` 格式，自动兼容滑动窗口和关联约束

### 调试技巧

```bash
# 启用 DEBUG 日志
python main.py --log-level DEBUG

# 禁用约束检查（在 config.yaml 中）
enable: false

# 仅检查模式（不继续写入 Excel）
check_only: true
```

## 常见问题

### Q1: 关联约束和滑动窗口约束有什么区别？

A: 滑动窗口检查物理连续的组（按日志顺序），关联约束通过 where 条件识别角色、links 条件建立关联，可以检查非连续的组。两者共享同一套约束检查引擎。

### Q2: validate 表达式支持哪些操作？

A: 支持比较（>=, <=, >, <, ==, !=）、算术（+, -, *, /）、逻辑（and, or, not）和属性访问（src1.opSch.powerLevel）。不支持函数调用、下标访问等。优先使用 CEL 引擎（需安装 cel-python），否则自动使用内置 AST 安全求值器。

### Q3: 字段值比较是否区分大小写？

A: 是的，所有比较都转换为字符串后进行，区分大小写。

### Q4: links 中的多字段联合匹配怎么写？

A: 使用列表格式：`{ src1: ["opSch.channelId", "opSch.bankId"], src2: ["opSch.channelId", "opSch.bankId"] }`，所有字段对必须同时匹配。

### Q5: 最多支持几个角色？

A: 最多 3 个（src1/src2/src3），支持线性链（A→B→C）、扇出（A→B, A→C）、扇入（A→C, B→C）等拓扑。
