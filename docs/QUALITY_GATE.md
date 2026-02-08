# 代码质量门限配置指南

## 📊 当前质量状态

**Pylint 分数**: 9.70/10 ✅
**质量门限**: 9.5/10
**状态**: 通过 ✅

---

## 🎯 什么是质量门限？

质量门限（Quality Gate）是代码质量的最低标准。当代码质量低于门限时，CI/CD 流程会失败，防止低质量代码合并。

---

## 🚀 快速开始

### 本地检查（提交前）

```bash
# 运行质量检查脚本
./scripts/check_quality.sh
```

### CI 自动检查（提交后）

推送代码后，GitHub Actions 会自动运行 Pylint 检查。

---

## ⚙️ 门限配置

### 1. GitHub Actions 门限

**文件**: `.github/workflows/pylint.yml`

```yaml
# 设置门限（9.5分以上通过）
THRESHOLD=9.5
```

**修改方法**:
```bash
# 编辑文件，修改 THRESHOLD 值
vim .github/workflows/pylint.yml

# 例如改为 9.0
THRESHOLD=9.0
```

### 2. 本地检查门限

**文件**: `scripts/check_quality.sh`

```bash
# 设置门限
THRESHOLD=9.5
```

**修改方法**:
```bash
# 编辑文件，修改 THRESHOLD 值
vim scripts/check_quality.sh
```

### 3. 推荐的门限设置

| 项目阶段 | 推荐门限 | 说明 |
|---------|---------|------|
| 新项目   | 8.0     | 初期，允许较多警告 |
| 成熟项目 | 9.0     | 标准质量要求 |
| 核心库   | 9.5     | 高质量要求（当前） |
| 严格模式 | 9.8     | 近乎完美 |

---

## 📋 Pylint 告警级别

### 级别说明

| 级别 | 代码 | 严重程度 | 说明 |
|-----|------|---------|------|
| **Error** | E | 🔴 高 | 代码错误，必须修复 |
| **Warning** | W | 🟡 中 | 潜在问题，建议修复 |
| **Refactor** | R | 🟡 中 | 代码结构问题 |
| **Convention** | C | 🟢 低 | 代码风格问题 |
| **Info** | I | 🟢 低 | 信息提示 |

### 当前项目告警分布

```
🔴 Error (E):     0 个  ✅
🟡 Warning (W):   0 个  ✅
🟡 Refactor (R):  19 个 （架构问题，可接受）
🟢 Convention (C): 5 个 （风格问题）
```

---

## 🛠️ 如何提高 Pylint 分数？

### 1. 修复高优先级问题

```bash
# 只显示 Error 和 Warning
pylint src/ --rcfile=.pylintrc --disable=R,C,I

# 修复这些问题后，分数会显著提升
```

### 2. 修复可快速解决的问题

```bash
# 未使用的导入
pylint src/ --rcfile=.pylintrc --disable=all --enable=W0611

# 参数名冲突
pylint src/ --rcfile=.pylintrc --disable=all --enable=W0621
```

### 3. 架构优化（长期）

```bash
# 函数参数过多
pylint src/ --rcfile=.pylintrc --disable=all --enable=R0913

# 函数过长
pylint src/ --rcfile=.pylintrc --disable=all --enable=R0915
```

---

## 🔧 禁用特定规则

### 在 .pylintrc 中禁用

```ini
[MESSAGES CONTROL]
disable=
    C0114,  # missing-module-docstring
    R0913,  # too-many-arguments (如果接受这个问题)
```

### 在代码中临时禁用

```python
# pylint: disable=too-many-arguments
def my_function(a, b, c, d, e, f):
    pass
# pylint: enable=too-many-arguments
```

### 单行禁用

```python
result = complex_function()  # pylint: disable=too-many-locals
```

---

## 📈 CI/CD 集成示例

### 1. 仅警告，不阻止（Soft Gate）

```yaml
- name: Run Pylint (warning only)
  run: |
    pylint src/ --rcfile=.pylintrc --exit-zero
    # 总是返回 0，不阻止 CI
```

### 2. 严格模式（Hard Gate）

```yaml
- name: Run Pylint (strict)
  run: |
    pylint src/ --rcfile=.pylintrc --fail-under=9.5
    # 低于 9.5 分立即失败
```

### 3. 渐进式提升（Current）

```yaml
- name: Run Pylint (progressive)
  run: |
    SCORE=$(pylint src/ --rcfile=.pylintrc --exit-zero | ...)
    if (( $(echo "$SCORE < 9.5" | bc -l) )); then
      exit 1
    fi
```

---

## 💡 最佳实践

### 1. 提交前检查

```bash
# 添加到 git hooks
cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash
./scripts/check_quality.sh
EOF
chmod +x .git/hooks/pre-commit
```

### 2. 定期审查

```bash
# 每周运行完整检查
pylint src/ --rcfile=.pylintrc > pylint_report.txt

# 对比上周分数
diff pylint_report_last_week.txt pylint_report.txt
```

### 3. 团队协作

- **新功能**: 不降低整体分数
- **Bug修复**: 顺便修复相关告警
- **重构**: 提升该模块分数

---

## 📚 参考资料

- [Pylint 官方文档](https://pylint.pycqa.org/)
- [Pylint 消息列表](https://pylint.pycqa.org/en/latest/user_guide/messages/messages_overview.html)
- [GitHub Actions 官方文档](https://docs.github.com/en/actions)

---

## 🔍 常见问题

### Q: 为什么我的分数是 9.70，但告警还有 24 个？

A: Pylint 分数不是简单的"告警数量"计算：
- Error/Warning 影响大
- Refactor/Convention 影响小
- 代码总行数也影响分数

### Q: 可以把门限设为 10.0 吗？

A: 不建议：
- 10.0 = 完美代码，几乎不可能
- 过于严格会降低开发效率
- 9.5-9.8 是实际项目的合理目标

### Q: CI 失败了怎么办？

A: 三个选择：
1. **修复代码**（推荐）- 提升质量
2. **降低门限**（临时）- 赶进度
3. **禁用规则**（谨慎）- 确认不是问题

---

**更新时间**: 2026-02-08
**维护者**: ailogproc 团队
