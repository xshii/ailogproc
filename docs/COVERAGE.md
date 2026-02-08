# 测试覆盖率配置指南

## 📊 当前覆盖率状态

**测试覆盖率**: 68% 📈
**覆盖率门限**: 70%
**状态**: 接近目标 ⚡

---

## 🎯 什么是测试覆盖率？

测试覆盖率（Code Coverage）衡量代码被测试覆盖的百分比。高覆盖率意味着：
- ✅ 更少的潜在 Bug
- ✅ 更安全的重构
- ✅ 更好的代码质量
- ✅ 更高的信心

---

## 🚀 快速开始

### 运行测试并查看覆盖率

```bash
# 方式1：使用 Makefile（推荐）
make coverage

# 方式2：直接使用脚本
./scripts/check_coverage.sh

# 方式3：手动运行
pytest tests/ --cov=src --cov-report=html
open htmlcov/index.html  # 打开报告
```

### 只运行测试（不检查覆盖率）

```bash
make test
# 或
pytest tests/ -v
```

---

## ⚙️ 门限配置

### 1. GitHub Actions 门限

**文件**: `.github/workflows/coverage.yml`

```yaml
# 设置门限（70%以上通过）
THRESHOLD=70
```

### 2. 本地检查门限

**文件**: `scripts/check_coverage.sh`

```bash
# 设置门限
THRESHOLD=70
```

### 3. 推荐的覆盖率目标

| 项目阶段 | 推荐覆盖率 | 说明 |
|---------|-----------|------|
| 新项目   | 50-60%    | 初期，覆盖核心功能 |
| 成熟项目 | 70-80%    | 标准要求（当前目标）⭐ |
| 关键系统 | 80-90%    | 高可靠性要求 |
| 核心库   | 90%+      | 接近完全覆盖 |

**注意**: 不要盲目追求 100% 覆盖率！
- 一些代码难以测试（如 UI、外部 API）
- 80-90% 是实际项目的合理目标
- 关注测试质量而非数量

---

## 📋 覆盖率类型

### 1. 行覆盖率（Line Coverage）
- **定义**: 代码行被执行的百分比
- **当前使用**: ✅
- **适用**: 大多数项目

### 2. 分支覆盖率（Branch Coverage）
- **定义**: 所有分支（if/else）被执行的百分比
- **当前使用**: ✅ (已启用)
- **更严格**: 确保所有条件都被测试

### 3. 函数覆盖率（Function Coverage）
- **定义**: 函数被调用的百分比
- **当前使用**: ❌
- **可选**: 补充指标

---

## 🛠️ 提高覆盖率

### 1. 查看未覆盖的代码

```bash
# 运行覆盖率并打开报告
make coverage
make report

# 或手动打开
open htmlcov/index.html
```

**HTML 报告功能**:
- 🟢 绿色：已覆盖
- 🔴 红色：未覆盖
- 🟡 黄色：部分覆盖（分支）

### 2. 找出覆盖率最低的文件

```bash
# 按覆盖率排序
pytest tests/ --cov=src --cov-report=term-missing | grep -E "^\w" | sort -k4 -n
```

### 3. 只测试特定模块

```bash
# 只测试 plugins
pytest tests/ --cov=src/plugins

# 只测试 excel_writer
pytest tests/ --cov=src/plugins/excel_writer
```

### 4. 为未覆盖代码添加测试

**示例**：当前覆盖率最低的模块：

| 模块 | 覆盖率 | 建议 |
|------|--------|------|
| processor.py | 48% | 添加 Excel 处理测试 |
| logger.py | 61% | 添加日志功能测试 |
| config_parser | 70% | 添加解析测试 |
| dld_configtmp | 74% | 添加下载测试 |

---

## 📈 覆盖率报告

### 本地 HTML 报告

```bash
# 生成并打开报告
make coverage
make report
```

**报告位置**: `htmlcov/index.html`

### CI/CD 报告

#### 1. GitHub Actions Artifacts

每次 CI 运行都会上传覆盖率报告：
- 访问 Actions → 选择运行 → Artifacts → coverage-report

#### 2. Codecov 集成

**已配置**: ✅ 自动上传到 Codecov

访问 [codecov.io](https://codecov.io) 查看：
- 覆盖率趋势图
- PR 覆盖率变化
- 文件级覆盖率

#### 3. PR 评论

每个 PR 会自动添加覆盖率评论：
- 📊 当前覆盖率
- 📈 覆盖率变化
- 🎯 是否达标

---

## 🔧 配置文件

### .coveragerc

```ini
[run]
source = src          # 测量 src 目录
branch = True         # 启用分支覆盖率

[report]
show_missing = True   # 显示缺失的行号
precision = 2         # 精度：小数点后2位

exclude_lines =
    pragma: no cover  # 排除标记的行
    def __repr__      # 排除 __repr__
    if __name__ == .__main__.:  # 排除主程序入口
```

### pytest.ini

```ini
[pytest]
testpaths = tests     # 测试目录
addopts =
    -v                # 详细输出
    --durations=10    # 显示最慢的10个测试
```

---

## 💡 最佳实践

### 1. 优先覆盖核心功能

```python
# ✅ 优先测试
- 业务逻辑
- 数据处理
- API 接口
- 工具函数

# ⏸️ 次要测试
- UI 代码
- 配置读取
- 简单的 getter/setter
- 异常处理分支
```

### 2. 排除不需要测试的代码

```python
# 在代码中标记
def debug_function():  # pragma: no cover
    print("Debug only")

# 或在 .coveragerc 中排除
[run]
omit =
    */debug/*
    */migrations/*
```

### 3. 测试重要的分支

```python
# ❌ 不好：只测试主流程
def test_process():
    result = process_data(valid_data)
    assert result == expected

# ✅ 好：测试所有分支
def test_process_valid():
    result = process_data(valid_data)
    assert result == expected

def test_process_invalid():
    with pytest.raises(ValueError):
        process_data(invalid_data)

def test_process_empty():
    result = process_data([])
    assert result == []
```

### 4. 使用参数化测试提高覆盖率

```python
import pytest

@pytest.mark.parametrize("input,expected", [
    ("trace_20260101.txt", True),
    ("log_20260101.txt", False),
    ("trace.txt", True),
    ("", False),
])
def test_is_trace_file(input, expected):
    assert is_trace_file(input) == expected
```

---

## 🔍 调试覆盖率问题

### 问题1：覆盖率报告为空

```bash
# 检查是否正确安装
pip install pytest-cov coverage

# 确认源代码路径
pytest tests/ --cov=src --cov-report=term
```

### 问题2：某些代码始终显示未覆盖

```bash
# 检查是否在测试中实际执行
pytest tests/ -v -s

# 添加调试输出
def my_function():
    print("Function called!")  # 临时调试
    ...
```

### 问题3：分支覆盖率很低

```python
# 确保测试所有条件分支
def process(value):
    if value > 0:    # 分支1
        return "positive"
    elif value < 0:  # 分支2
        return "negative"
    else:            # 分支3
        return "zero"

# 需要3个测试用例覆盖所有分支
```

---

## 🎯 覆盖率与代码质量

### 高覆盖率 ≠ 高质量

```python
# ❌ 100% 覆盖率但测试无意义
def test_bad():
    result = add(2, 3)
    # 没有断言！

# ✅ 有意义的测试
def test_good():
    result = add(2, 3)
    assert result == 5
    assert isinstance(result, int)
```

### 覆盖率指标

| 指标 | 描述 | 目标 |
|------|------|------|
| **行覆盖率** | 代码行被执行 | 70%+ |
| **分支覆盖率** | 所有分支被测试 | 65%+ |
| **测试质量** | 有效断言数量 | 每个测试 ≥ 1 |
| **测试独立性** | 测试间无依赖 | 100% |

---

## 📚 参考资料

- [Coverage.py 官方文档](https://coverage.readthedocs.io/)
- [pytest-cov 文档](https://pytest-cov.readthedocs.io/)
- [Codecov 文档](https://docs.codecov.com/)

---

## 🔧 常见命令速查

```bash
# 运行测试
make test
pytest tests/ -v

# 覆盖率检查
make coverage
./scripts/check_coverage.sh

# 查看报告
make report
open htmlcov/index.html

# 清理
make clean

# 提交前检查（全部）
make pre-commit
make all

# 只检查特定文件
pytest tests/test_workflow.py --cov=src/workflow

# 显示缺失的行
pytest tests/ --cov=src --cov-report=term-missing

# 生成 JSON 报告（CI）
pytest tests/ --cov=src --cov-report=json
```

---

**更新时间**: 2026-02-08
**维护者**: ailogproc 团队
**当前覆盖率**: 68% → 目标 70%+
