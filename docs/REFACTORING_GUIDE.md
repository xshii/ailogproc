# 重构指南 - 使用数据类减少参数

> 展示如何使用数据类优化函数签名

## 问题：参数过多

### Before (7个参数)
```python
def _try_match_b_column(
    self,
    row,
    field_name_lower,
    enable_partial_match,
    a_col_str,
    field_name,
    special_prefix_no_match,
):
    """尝试匹配B列"""
    # 实现...
```

**问题**:
- 难以记住参数顺序
- 调用时容易出错
- 难以扩展（添加新参数）
- 测试复杂

## 解决方案：使用数据类

### 1. 定义数据类

```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class MatchContext:
    """匹配上下文"""
    row: int
    field_name: str
    field_name_lower: str
    a_col_str: str
    enable_partial_match: bool = True
    special_prefix_no_match: Optional[list] = None
```

### 2. 重构后的函数

```python
def _try_match_b_column(self, ctx: MatchContext) -> MatchResult:
    """尝试匹配B列

    Args:
        ctx: 匹配上下文，包含所有必要信息

    Returns:
        MatchResult: 匹配结果对象
    """
    b_col_value = self.get_cell_value_smart(ctx.row, 2)

    if b_col_value:
        b_col_str_lower = str(b_col_value).strip().lower()
        if b_col_str_lower == ctx.field_name_lower:
            return MatchResult.success(ctx.row, 2, "b_column")

        if ctx.enable_partial_match:
            if (ctx.field_name_lower in b_col_str_lower or
                b_col_str_lower in ctx.field_name_lower):
                return MatchResult.success(ctx.row, 2, "b_column_partial", 0.8)
    else:
        if ctx.special_prefix_no_match is not None:
            if ctx.row not in [info[0] for info in ctx.special_prefix_no_match]:
                ctx.special_prefix_no_match.append(
                    (ctx.row, ctx.a_col_str, ctx.field_name)
                )

    return MatchResult.failure()
```

### 3. 调用示例

```python
# Before: 7个参数，顺序容易搞错
result = self._try_match_b_column(
    row,
    field_name_lower,
    enable_partial_match,
    a_col_str,
    field_name,
    special_prefix_no_match,
)

# After: 清晰的数据对象
ctx = MatchContext(
    row=row,
    field_name=field_name,
    field_name_lower=field_name.lower(),
    a_col_str=a_col_str,
    enable_partial_match=True,
    special_prefix_no_match=warnings_list,
)
result = self._try_match_b_column(ctx)

# 检查结果
if result.matched:
    print(f"Matched at row {result.row}, method: {result.method}")
```

## 收益对比

### Before
```python
# 调用7参数函数 - 难以理解
result = processor._try_match_b_column(
    5,
    "field_name",
    True,
    "A5 Value",
    "field_name",
    []
)

# 返回值不明确
if result:
    row, is_special = result  # 需要知道返回tuple的结构
```

### After
```python
# 清晰的上下文对象
ctx = MatchContext(
    row=5,
    field_name="field_name",
    field_name_lower="field_name",
    a_col_str="A5 Value",
)
result = processor._try_match_b_column(ctx)

# 清晰的结果对象
if result.matched:
    print(f"Row: {result.row}")
    print(f"Method: {result.method}")
    print(f"Confidence: {result.confidence}")
```

## 更多示例

### CellPosition - 替代 (row, col) 元组

```python
# Before
def process_cell(self, row: int, col: int):
    pass

# After
from data_models import CellPosition

def process_cell(self, pos: CellPosition):
    print(f"Processing {pos}")  # 自动格式化为 "(5, 3)"
```

### TableRange - 替代多个参数

```python
# Before
def fill_table(self, start_row: int, end_row: int,
               start_col: int, end_col: int):
    rows = end_row - start_row + 1  # 重复计算
    pass

# After
def fill_table(self, range: TableRange):
    rows = range.row_count  # 内置属性
    if range.contains_row(10):  # 内置方法
        pass
```

### ProcessingStats - 收集统计信息

```python
# Before: 多个变量
total = 0
matched = 0
failed = 0
warnings = 0

# 到处传递...
def process(total, matched, failed, warnings):
    pass

# After: 单个对象
stats = ProcessingStats()
stats.add_match(success=True)
stats.add_match(success=False)
stats.add_warning()

print(stats)  # "Stats: 1/2 matched (50.0%), 1 warnings, 0 errors"
print(f"Match rate: {stats.match_rate:.1%}")
```

## 测试改进

### Before
```python
def test_match():
    result = processor._try_match_b_column(
        5, "name", True, "A5", "name", []
    )
    assert result == (5, True)  # 魔法值
```

### After
```python
def test_match():
    ctx = MatchContext(
        row=5,
        field_name="name",
        field_name_lower="name",
        a_col_str="A5",
    )
    result = processor._try_match_b_column(ctx)

    assert result.matched is True
    assert result.row == 5
    assert result.method == "b_column"
    assert result.confidence == 1.0
```

## 渐进式重构策略

### 阶段1: 创建数据类（✅ 已完成）
- 定义所有数据模型
- 编写完整测试
- 26个测试全部通过

### 阶段2: 新代码使用数据类
- 所有新写的函数使用数据类
- 逐步迁移旧代码
- 保持向后兼容

### 阶段3: 完全迁移（可选）
- 重构所有旧函数
- 移除旧接口
- 更新所有调用者

## 已创建的数据类

| 数据类 | 用途 | 测试 |
|--------|------|------|
| CellPosition | 单元格位置 | ✅ 2个 |
| TableRange | 表格范围 | ✅ 3个 |
| MatchContext | 匹配上下文 | ✅ 2个 |
| MatchResult | 匹配结果 | ✅ 3个 |
| FillOptions | 填充选项 | ✅ 2个 |
| TopTableWarning | 顶表告警 | ✅ 2个 |
| SubTablePosition | 子表位置 | ✅ 2个 |
| MatchConfig | 匹配配置 | ✅ 3个 |
| ProcessingStats | 处理统计 | ✅ 7个 |

**总计**: 9个数据类，26个测试 ✅

## 下一步

1. ✅ 数据类已创建并测试
2. 📝 使用指南已编写
3. 🔄 在新代码中优先使用数据类
4. 🔄 逐步重构旧代码

---

**最后更新**: 2026-02-09
**测试状态**: 26/26 passed ✅
