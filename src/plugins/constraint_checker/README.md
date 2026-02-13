# 配置约束检查插件

## 功能概述

该插件用于验证配置是否满足预定义的约束条件，支持：

1. **单组约束**：针对单个配置组内字段的约束
   - `only_allow`: 字段值仅允许在指定列表中
   - `forbid`: 字段值禁止在指定列表中
   - `only_allow_combinations`: 多字段组合只能是指定的组合之一（v1.2.0+）

2. **多组约束**：针对连续 2-3 个配置组之间的约束
   - `same_value`: 多组间同一字段值必须相同
   - `sequence`: 字段值必须满足递增/递减序列
   - `conditional`: 条件约束，如果组A满足条件，则组B必须满足约束
   - `only_allow_combinations`: 多组间字段组合只能是指定的组合对之一（v1.2.0+）

3. **字段前缀命名**：所有字段使用 `sectionName.fieldName` 格式（v1.3.0+）
   - top 表字段：`opSch.powerLevel`、`opSch.systemMode`
   - 子表字段：`ERCfg.cfgGroup`、`I2C.0.speed`、`I2C.1.speed`

4. **版本管理**：按版本管理约束规则，支持版本号+日期后缀

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

#### only_allow_combinations（字段组合约束，v1.2.0+）

多个字段必须配套使用，只允许指定的组合。适用于字段之间有关联依赖的场景。

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
    - opSch.powerLevel: "15"
      opSch.voltageLevel: "3"
      opSch.frequencyMode: "high"
```

### 2. 多组约束

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

#### only_allow_combinations（组间组合映射，v1.2.0+）

定义允许的组间状态转换路径，适用于状态机切换、功率等级切换等场景。

```yaml
- name: "功率等级切换路径白名单"
  description: "只允许保持当前等级或相邻等级间切换，防止电压骤降"
  group_count: 2
  only_allow_combinations:
    # 低→低（保持）
    - group0:
        opSch.powerLevel: "5"
        opSch.voltageLevel: "1"
      group1:
        opSch.powerLevel: "5"
        opSch.voltageLevel: "1"
    # 低→中（提升）
    - group0:
        opSch.powerLevel: "5"
        opSch.voltageLevel: "1"
      group1:
        opSch.powerLevel: "10"
        opSch.voltageLevel: "2"
    # 注意：高→低 不在列表中，因此被禁止
```

## 字段命名规范（v1.3.0+）

所有字段必须使用 `sectionName.fieldName` 格式：

| 字段类型 | 格式 | 示例 |
|----------|------|------|
| top 表字段 | `topName.fieldName` | `opSch.powerLevel` |
| 子表字段（唯一） | `subName.fieldName` | `ERCfg.cfgGroup` |
| 子表字段（重复） | `subName.索引.fieldName` | `I2C.0.speed`、`I2C.1.speed` |

优势：
1. 明确字段所属的表，避免歧义
2. 不同子表的同名字段可以明确区分
3. 支持跨 top 和 sub 表的组合约束

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
| 相邻组字段值一致 | `same_value` | systemMode 必须一致 |
| 字段值递增/递减 | `sequence` | configId 递增 |
| 状态转换限制 | `only_allow_combinations`（多组） | 功率切换路径 |
| 条件依赖 | `conditional` | 如果 A=high 则 B 不能是 low |

## 版本管理

### 版本命名规则

格式：`主版本.次版本.修订版_日期`

- 主版本：重大变更（不兼容的 API 更改）
- 次版本：功能增加（向后兼容）
- 修订版：bug 修复（向后兼容）
- 日期：YYYYMMDD

示例：`1.3.0_20240208`

### 版本选择

1. **指定版本**：设置 `active_version: "1.1.0_20240208"`
2. **自动最新**：设置 `active_version: null`（默认），自动使用版本号最大的版本

### 版本历史

| 版本 | 日期 | 主要变更 |
|------|------|----------|
| v1.0.0 | 2024-01-15 | 初始版本：only_allow、forbid、same_value、conditional |
| v1.1.0 | 2024-02-08 | 新增 sequence、三组级联、多条件触发 |
| v1.2.0 | 2024-02-08 | 新增 only_allow_combinations（单组和多组） |
| v1.3.0 | 2024-02-08 | 字段统一使用 `sectionName.fieldName` 前缀格式，支持子表约束 |

## 输出结果

插件返回：

```python
{
    'validation_passed': True/False,  # 是否通过
    'violations': [                   # 违规列表
        {
            'type': 'only_allow',
            'rule': '规则名称',
            'group': 0,
            'field': '字段名',
            'value': '实际值',
            'allowed': ['允许值列表'],
            'message': '详细错误信息'
        }
    ],
    'version': '1.3.0_20240208'       # 使用的规则版本
}
```

### 违规消息格式

| 约束类型 | 消息格式 |
|----------|----------|
| only_allow | `[组0] 规则名: 字段 'X' 的值 'Y' 不在允许列表 ['a', 'b'] 中` |
| forbid | `[组0] 规则名: 字段 'X' 的值 'Y' 在禁止列表 ['a', 'b'] 中` |
| same_value | `[组[0,1]] 规则名: 字段 'X' 在各组中的值不一致: ['1', '2']` |
| sequence | `[组[0,1,2]] 规则名: 字段 'X' 的值 [3,1,2] 不满足递增序列` |
| conditional | `[组0->1] 规则名: 当组0的 X=high 时，组1的 Y 不应为 'low'（禁止值: ['low']）` |

### 报告生成

启用 `generate_report: true` 时，生成 JSON 报告：

```json
{
  "timestamp": "2024-02-08T10:30:00",
  "passed": false,
  "version": "1.3.0_20240208",
  "violations": 2,
  "summary": {"only_allow": 1, "forbid": 1},
  "errors": [...]
}
```

## 日志输出

```
[约束检查] 开始检查配置约束...
[约束检查] 使用规则版本: 1.3.0_20240208
[约束检查] ✓ 所有约束检查通过
```

或

```
[约束检查] ✗ 发现 2 个违规
  [1] [组0] 系统模式1下的参数限制: 字段 'opSch.debugLevel' 的值 '5' 不在允许列表 ['0', '1', '2', '3'] 中
  [2] [组0] 系统模式1下的参数限制: 字段 'opSch.dangerousFlag' 的值 '1' 在禁止列表 ['1', 'true'] 中
```

## 开发指南

### 添加新的约束类型

1. 在配置中定义新的 `type`
2. 在 `_check_multi_rule()` 中添加处理逻辑
3. 实现检查函数（参考 `_check_same_value`、`_check_sequence` 等）

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

### Q1: 如何禁用某个版本的约束？

A: 不要设置为 `active_version`，或者直接删除该版本的配置。

### Q2: 如何让约束检查失败时不阻止 Excel 写入？

A: 修改 `excel_writer` 插件的依赖，去掉 `constraint_checker`。

### Q3: 字段值比较是否区分大小写？

A: 是的，所有比较都转换为字符串后进行，区分大小写。

### Q4: 如何查看使用的是哪个版本？

A: 查看日志输出 `[约束检查] 使用规则版本: xxx` 或检查返回结果的 `version` 字段。

### Q5: v1.2.0 的 only_allow_combinations 和分别用 only_allow 约束每个字段有什么区别？

A: `only_allow` 是对每个字段独立约束，不同字段之间可以自由组合。`only_allow_combinations` 要求多个字段的值必须作为一个整体匹配指定的组合。例如：
- `only_allow` 分别限制 powerLevel=[5,10] 和 voltage=[0.8V,1.0V]，则允许 (5, 1.0V) 这种不合理组合
- `only_allow_combinations` 只允许 (5, 0.8V) 和 (10, 1.0V)，更精确

### Q6: v1.3.0 的字段前缀格式是否向后兼容？

A: 不兼容。v1.3.0 要求所有字段使用 `sectionName.fieldName` 格式。如果需要使用旧格式的规则，请指定 `active_version` 为 v1.2.0 或更早版本。
