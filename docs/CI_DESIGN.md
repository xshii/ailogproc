# CI/CD 设计说明

## 检查项拆分策略

为了便于快速定位问题，CI 检查被拆分为以下独立任务：

### 1. 代码格式检查 (Ruff)
- **检查内容**: 代码格式规范、import 顺序、引号风格等
- **失败原因**: 代码格式不符合规范
- **修复方法**: `ruff format src/ main.py`

### 2. 代码质量检查 (Pylint)
- **检查内容**: 代码复杂度、命名规范、潜在bug、函数长度等
- **失败原因**: 代码质量问题（评分 < 要求）
- **修复方法**: 根据 pylint 报告逐项修复
- **配置**: `.pylintrc` 中设置 `max-statements=35` 间接限制函数长度

### 3. 单元测试（预留）
- **检查内容**: 功能正确性
- **失败原因**: 测试用例失败
- **修复方法**: 修复代码逻辑或更新测试

## 优势

### GitHub Actions
- 每个 job 独立显示状态（✅/❌）
- 可以快速看出是哪个环节失败
- 点击具体 job 查看详细日志
- 并行执行，总耗时 = max(各 job 耗时)

示例界面：
```
✅ 代码格式检查 (Ruff)     - 15s
❌ 代码质量检查 (Pylint)   - 28s  <- 一眼看出是质量问题
```

### Jenkins
- Pipeline 视图清晰展示每个 stage 状态
- 并行 stage 同时显示
- Blue Ocean 界面更直观

示例界面：
```
准备环境 ✅
├─ 代码格式检查 ✅
└─ 代码质量检查 ❌  <- 清楚看到质量检查失败
```

## 本地快速检查

```bash
# 检查格式
ruff format --check src/ main.py

# 自动修复格式
ruff format src/ main.py

# 代码质量检查
pylint src/ main.py --rcfile=.pylintrc

# 自动修复简单问题
ruff check --fix src/ main.py
```

## 配置文件位置

- GitHub Actions: `.github/workflows/ci.yml`
- Jenkins: `Jenkinsfile`
- Pylint 配置: `.pylintrc`
- Ruff 配置: `pyproject.toml` (可选)
