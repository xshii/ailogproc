#!/bin/bash
# 测试覆盖率检查脚本
# 使用方法: ./scripts/check_coverage.sh

set -e

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "测试覆盖率检查"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 激活虚拟环境
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "⚠️  未找到虚拟环境，使用系统Python"
fi

# 运行测试并生成覆盖率报告
echo -e "\n📊 运行测试并收集覆盖率数据...\n"
pytest tests/ \
    -c config/pytest.ini \
    --cov=src \
    --cov-config=config/.coveragerc \
    --cov-report=term-missing \
    --cov-report=html \
    --cov-report=json \
    -v \
    2>&1 | tee /tmp/coverage_output.txt

# 提取覆盖率百分比
COVERAGE=$(grep "TOTAL" /tmp/coverage_output.txt | awk '{print $4}' | sed 's/%//')

# 如果没有提取到覆盖率，尝试从 JSON 读取
if [ -z "$COVERAGE" ]; then
    if [ -f "coverage.json" ]; then
        COVERAGE=$(python3 -c "import json; print(json.load(open('coverage.json'))['totals']['percent_covered'])")
    else
        echo "❌ 无法提取覆盖率数据"
        exit 1
    fi
fi

echo -e "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "覆盖率报告"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 设置门限
THRESHOLD=70

echo "测试覆盖率: ${COVERAGE}%"
echo "覆盖率门限: ${THRESHOLD}%"

# 比较覆盖率
if awk "BEGIN {exit !($COVERAGE < $THRESHOLD)}"; then
    echo -e "\n❌ 未通过覆盖率门限"
    echo "   覆盖率 (${COVERAGE}%) 低于门限 (${THRESHOLD}%)"
    echo -e "\n💡 建议："
    echo "   1. 查看 htmlcov/index.html 了解详情"
    echo "   2. 为未覆盖的代码添加测试"
    echo "   3. 重新运行检查"
    echo -e "\n📄 HTML 报告: htmlcov/index.html"
    exit 1
else
    echo -e "\n✅ 通过覆盖率门限"
    echo "   测试覆盖率符合标准！"
    echo -e "\n📄 HTML 报告: htmlcov/index.html"
    exit 0
fi
