# Makefile - 快速执行常用命令

.PHONY: help test coverage quality lint clean install

# 默认目标：显示帮助
help:
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "可用命令"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	@echo "  make install     安装依赖"
	@echo "  make test        运行测试"
	@echo "  make coverage    测试覆盖率检查"
	@echo "  make quality     代码质量检查（pylint）"
	@echo "  make lint        快速代码检查（ruff）"
	@echo "  make all         运行所有检查（quality + coverage）"
	@echo "  make clean       清理临时文件"
	@echo "  make report      打开覆盖率报告"
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 安装依赖
install:
	@echo "📦 安装依赖..."
	pip install -r requirements.txt

# 运行测试
test:
	@echo "🧪 运行测试..."
	pytest tests/ -c config/pytest.ini -v

# 测试覆盖率
coverage:
	@echo "📊 运行覆盖率检查..."
	@./scripts/check_coverage.sh

# 代码质量检查
quality:
	@echo "🔍 运行代码质量检查..."
	@./scripts/check_quality.sh

# 快速 lint 检查
lint:
	@echo "⚡ 快速 lint 检查..."
	ruff check src/ --fix

# 运行所有检查
all: quality coverage
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "✅ 所有检查完成！"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 清理临时文件
clean:
	@echo "🧹 清理临时文件..."
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage
	rm -rf coverage.json coverage.xml
	rm -rf *.egg-info
	rm -rf dist build
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	@echo "✓ 清理完成"

# 打开覆盖率报告
report:
	@if [ -f "htmlcov/index.html" ]; then \
		echo "📄 打开覆盖率报告..."; \
		open htmlcov/index.html 2>/dev/null || xdg-open htmlcov/index.html 2>/dev/null || echo "请手动打开 htmlcov/index.html"; \
	else \
		echo "❌ 未找到覆盖率报告，请先运行: make coverage"; \
	fi

# 快速检查（在提交前运行）
pre-commit: lint quality coverage
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "✅ 提交前检查通过！可以安全提交代码"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
