# 配置约束检查插件

## 功能概述

该插件用于验证配置是否满足预定义的约束条件，支持：

1. **单组约束**：针对单个 top 表配置组的约束
   - `only_allow`: 字段值仅允许在指定列表中
   - `forbid`: 字段值禁止在指定列表中

2. **多组约束**：需要连续 2-3 个 top 表的约束
   - `same_value`: 多组间同一字段值必须相同
   - `sequence`: 字段值必须满足递增/递减序列
   - `conditional`: 条件约束，如果组A满足条件，则组B必须满足约束

3. **版本管理**：按版本管理约束规则，支持版本号+日期后缀

## 插件信息

- **Level**: 2（验证层）
- **依赖**: `config_parser`
- **执行时机**: 在 `config_parser` 之后、`excel_writer` 之前

## 配置文件结构

```yaml
enable: true

# 使用的规则版本（null 表示自动使用最新版本）
active_version: null

# 约束规则库
constraint_rules:
  "1.0.0_20240115":
    description: "版本描述"

    # 单组约束
    single_constraints:
      - name: "约束名称"
        when:
          field1: "value1"  # 触发条件（可多个，需全部满足）
          field2: "value2"
        only_allow:
          field3: ["allowed1", "allowed2"]  # 仅允许这些值
        forbid:
          field4: ["forbidden1", "forbidden2"]  # 禁止这些值

    # 多组约束
    multi_constraints:
      - name: "约束名称"
        group_count: 2  # 连续组数（2或3）
        rules:
          - type: "same_value"
            field: "systemMode"

          - type: "sequence"
            field: "configId"
            order: "increasing"  # 或 "decreasing"

          - type: "conditional"
            when_group: 0  # 条件组索引
            when_field: "systemMode"
            when_value: "1"
            then_group: 1  # 结果组索引
            then_field: "powerLevel"
            only_allow: ["5", "10"]
            # 或 forbid: ["0"]
```

## 约束类型详解

### 1. 单组约束

#### only_allow（仅允许）

当触发条件满足时，指定字段的值必须在允许列表中。

```yaml
- name: "系统模式1的调试级别限制"
  when:
    systemMode: "1"
  only_allow:
    debugLevel: ["0", "1", "2"]  # systemMode=1 时，debugLevel 只能是 0/1/2
```

#### forbid（禁止）

当触发条件满足时，指定字段的值不能在禁止列表中。

```yaml
- name: "调试模式禁止生产配置"
  when:
    debugLevel: "3"
  forbid:
    productionMode: ["1", "enabled"]  # debugLevel=3 时，productionMode 不能是 1 或 enabled
```

### 2. 多组约束

#### same_value（相同值）

连续多组配置中，指定字段的值必须相同。

```yaml
- name: "连续配置一致性"
  group_count: 2
  rules:
    - type: "same_value"
      field: "systemMode"  # 连续两组的 systemMode 必须相同
```

#### sequence（序列）

连续多组配置中，指定字段的值必须满足递增或递减。

```yaml
- name: "配置ID递增"
  group_count: 3
  rules:
    - type: "sequence"
      field: "configId"
      order: "increasing"  # 连续三组的 configId 必须递增
```

#### conditional（条件约束）

如果某组满足条件，则另一组必须满足约束。

```yaml
- name: "级联功率控制"
  group_count: 2
  rules:
    - type: "conditional"
      when_group: 0          # 第一组
      when_field: "powerMode"
      when_value: "high"
      then_group: 1          # 第二组
      then_field: "powerMode"
      forbid: ["low"]        # 如果第一组 powerMode=high，则第二组不能是 low
```

## 版本管理

### 版本命名规则

格式：`主版本.次版本.修订版_日期`

- 主版本：重大变更
- 次版本：功能增加
- 修订版：bug 修复
- 日期：YYYYMMDD

示例：`1.2.3_20240208`

### 版本选择

1. **指定版本**：设置 `active_version: "1.1.0_20240208"`
2. **自动最新**：设置 `active_version: null`（默认），自动使用版本号最大的版本

### 版本示例

```yaml
constraint_rules:
  "1.0.0_20240115":  # 初始版本
    single_constraints: [...]

  "1.1.0_20240208":  # 新版本（会自动使用此版本）
    single_constraints: [...]
    multi_constraints: [...]

  "1.2.0_20240301":  # 未来版本
    single_constraints: [...]
```

## 使用示例

### 示例1：基本单组约束

```yaml
"1.0.0_20240115":
  single_constraints:
    - name: "系统模式约束"
      when:
        systemMode: "1"
      only_allow:
        debugLevel: ["0", "1", "2"]
        powerMode: ["low", "medium"]
      forbid:
        dangerousFlag: ["1"]
```

配置：
```
opSch
|- systemMode = 1
|- debugLevel  = 2    # ✓ 在允许列表中
|- powerMode   = low  # ✓ 在允许列表中
```

违规示例：
```
opSch
|- systemMode = 1
|- debugLevel  = 5      # ✗ 不在允许列表中
|- dangerousFlag = 1    # ✗ 在禁止列表中
```

### 示例2：多条件触发

```yaml
- name: "双重条件约束"
  when:
    systemMode: "2"
    debugLevel: "3"  # 两个条件都满足才触发
  forbid:
    productionMode: ["1"]
```

### 示例3：连续两组一致性

```yaml
multi_constraints:
  - name: "系统模式一致性"
    group_count: 2
    rules:
      - type: "same_value"
        field: "systemMode"

      - type: "conditional"
        when_group: 0
        when_field: "systemMode"
        when_value: "1"
        then_group: 1
        then_field: "powerLevel"
        only_allow: ["5", "10"]
```

配置组：
```
[组0]
opSch
|- systemMode = 1
|- ...

[组1]
opSch
|- systemMode = 1    # ✓ 与组0相同
|- powerLevel = 5    # ✓ 组0 systemMode=1 时，允许 5
```

### 示例4：三组级联

```yaml
- name: "三组配置ID递增"
  group_count: 3
  rules:
    - type: "sequence"
      field: "configId"
      order: "increasing"
```

配置组：
```
[组0] configId = 1
[组1] configId = 2  # ✓ 递增
[组2] configId = 3  # ✓ 递增
```

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
    'version': '1.1.0_20240208'       # 使用的规则版本
}
```

## 日志输出

```
[约束检查] 开始检查配置约束...
[约束检查] 使用规则版本: 1.1.0_20240208
[约束检查] ✓ 所有约束检查通过
```

或

```
[约束检查] ✗ 发现 2 个违规
  [1] [组0] 系统模式约束: 字段 'debugLevel' 的值 '5' 不在允许列表 ['0', '1', '2'] 中
  [2] [组0] 系统模式约束: 字段 'dangerousFlag' 的值 '1' 在禁止列表中
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
