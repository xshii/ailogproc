# 测试文档

## 目录结构

```
tests/
├── unit/              # 单元测试（UT）
│   ├── test_excel_processor.py          # Excel处理器基础测试
│   ├── test_excel_processor_advanced.py # Excel处理器高级测试
│   ├── test_plugins.py                  # 插件系统测试
│   ├── test_utils.py                    # 工具函数测试
│   └── test_config_parser_advanced.py    # ConfigParser高级测试
│
└── integration/       # 集成测试（IT）
    ├── test_workflow.py                 # 工作流集成测试
    ├── test_workflow_simple.py          # 简单工作流测试
    └── test_multi_top_mode.py           # 多顶格模式测试
```

## 测试分类

### 单元测试（Unit Tests）

**定义：** 测试单个类、函数或方法的功能，不涉及外部依赖或多组件协同。

**特点：**
- 测试粒度细
- 运行速度快
- 易于定位问题
- 不依赖外部资源

**文件列表：**
- `test_excel_processor.py` - ExcelProcessor 类的基础功能测试
- `test_excel_processor_advanced.py` - ExcelProcessor 类的高级功能测试（子表、匹配、特殊前缀）
- `test_plugins.py` - Plugin 基类、插件依赖、层级测试
- `test_utils.py` - 日志系统、工具函数测试
- `test_config_parser_advanced.py` - ConfigParser 解析逻辑、字段映射、边界情况测试

### 集成测试（Integration Tests）

**定义：** 测试多个组件协同工作的场景，验证整个系统的端到端功能。

**特点：**
- 测试粒度粗
- 覆盖完整流程
- 验证组件协同
- 可能依赖外部资源

**文件列表：**
- `test_workflow.py` - 完整工作流测试（插件加载、执行、输出）
- `test_workflow_simple.py` - 简化工作流测试
- `test_multi_top_mode.py` - 多顶格配置模式测试

## 运行测试

### 运行所有测试
```bash
make test
# 或
pytest tests/ -c config/pytest.ini -v
```

### 只运行单元测试
```bash
pytest tests/unit/ -c config/pytest.ini -v
```

### 只运行集成测试
```bash
pytest tests/integration/ -c config/pytest.ini -v
```

### 运行特定测试文件
```bash
pytest tests/unit/test_excel_processor.py -c config/pytest.ini -v
```

### 运行特定测试用例
```bash
pytest tests/unit/test_excel_processor.py::TestExcelProcessor::test_init_with_file_path -c config/pytest.ini -v
```

## 测试覆盖率

### 生成覆盖率报告
```bash
make coverage
# 或
pytest tests/ -c config/pytest.ini --cov=src --cov-config=config/.coveragerc --cov-report=html
```

### 查看覆盖率报告
```bash
make report
# 或
open htmlcov/index.html
```

## 测试统计

| 类别 | 文件数 | 测试用例数 | 说明 |
|------|--------|-----------|------|
| **单元测试** | 5 | ~60 | 测试单个组件功能 |
| **集成测试** | 3 | ~15 | 测试端到端流程 |
| **总计** | 8 | ~75 | - |

## 测试覆盖率目标

| 模块 | 当前覆盖率 | 目标覆盖率 |
|------|-----------|-----------|
| 整体 | 62% | ≥ 70% |
| logger.py | 84% | ≥ 80% |
| excel_writer/plugin.py | 81% | ≥ 80% |
| base.py | 80% | ≥ 80% |
| workflow.py | 76% | ≥ 75% |

## 编写测试指南

### 单元测试示例
```python
import unittest
from src.module import MyClass

class TestMyClass(unittest.TestCase):
    def setUp(self):
        self.obj = MyClass()

    def test_method_returns_expected_value(self):
        result = self.obj.method()
        self.assertEqual(result, expected_value)
```

### 集成测试示例
```python
import unittest
from src.workflow import process_log_to_excel

class TestWorkflow(unittest.TestCase):
    def test_end_to_end_processing(self):
        result = process_log_to_excel(
            excel_file="template.xlsx",
            trace_file="trace.txt"
        )
        self.assertTrue(os.path.exists(result))
```

## 持续集成

测试在 GitHub Actions CI 中自动运行：
- `.github/workflows/coverage.yml` - 测试覆盖率检查
- `.github/workflows/pylint.yml` - 代码质量检查

**质量门限：**
- 测试覆盖率：≥ 70%
- Pylint 分数：≥ 9.5/10
- 所有测试必须通过
