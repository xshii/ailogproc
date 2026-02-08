# 配置文件说明

本目录包含项目的所有配置文件。

## 📁 文件列表

### 代码质量配置

| 文件 | 用途 | 文档 |
|------|------|------|
| `.pylintrc` | Pylint 代码质量检查配置 | [QUALITY_GATE.md](../docs/QUALITY_GATE.md) |

**主要配置**:
- 代码质量门限: 9.5/10
- 禁用的检查: missing-docstring
- 启用的检查: bare-except, raise-missing-from

---

### 测试配置

| 文件 | 用途 | 文档 |
|------|------|------|
| `pytest.ini` | Pytest 测试框架配置 | [COVERAGE.md](../docs/COVERAGE.md) |
| `.coveragerc` | Coverage.py 覆盖率配置 | [COVERAGE.md](../docs/COVERAGE.md) |

**主要配置**:
- 测试覆盖率门限: 70%
- 测试目录: `tests/`
- 分支覆盖率: 已启用

---

## 🔧 使用方法

### 本地使用

```bash
# 代码质量检查
pylint src/ --rcfile=config/.pylintrc

# 测试覆盖率
pytest tests/ -c config/pytest.ini --cov-config=config/.coveragerc

# 或使用 Makefile（推荐）
make quality   # 代码质量
make coverage  # 测试覆盖率
make all       # 全部检查
```

### CI/CD 使用

配置文件会被 GitHub Actions 自动使用：
- `.github/workflows/pylint.yml` - 代码质量检查
- `.github/workflows/coverage.yml` - 测试覆盖率检查

---

## 📝 修改配置

### 修改 Pylint 门限

编辑 `.github/workflows/pylint.yml` 和 `scripts/check_quality.sh`:

```bash
THRESHOLD=9.5  # 改为你需要的值
```

### 修改 Coverage 门限

编辑 `.github/workflows/coverage.yml` 和 `scripts/check_coverage.sh`:

```bash
THRESHOLD=70  # 改为你需要的值
```

### 修改 Pylint 规则

编辑 `config/.pylintrc`:

```ini
[MESSAGES CONTROL]
disable=
    C0114,  # 添加要禁用的规则

enable=
    W0702,  # 添加要启用的规则
```

### 修改 Coverage 规则

编辑 `config/.coveragerc`:

```ini
[run]
omit =
    */tests/*    # 添加要排除的文件

[report]
exclude_lines =
    pragma: no cover  # 添加要排除的代码行
```

---

## 📚 参考文档

- [Pylint 文档](https://pylint.pycqa.org/)
- [Pytest 文档](https://docs.pytest.org/)
- [Coverage.py 文档](https://coverage.readthedocs.io/)

---

**更新时间**: 2026-02-08
