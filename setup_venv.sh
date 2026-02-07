#!/bin/bash

# 使用 Python venv 的简单设置脚本
# 不需要 miniconda，只需要系统 Python 3.9+

set -e

VENV_NAME="venv"
REQUIRED_PYTHON_VERSION="3.9"

echo "=========================================="
echo "  Python venv 环境设置脚本"
echo "  不需要 miniconda，使用系统 Python"
echo "=========================================="

# 检测 Python 版本
check_python_version() {
    local python_cmd=$1
    if ! command -v "$python_cmd" &> /dev/null; then
        return 1
    fi

    local version=$($python_cmd --version 2>&1 | awk '{print $2}')
    local major=$(echo $version | cut -d. -f1)
    local minor=$(echo $version | cut -d. -f2)

    if [ "$major" -ge 3 ] && [ "$minor" -ge 9 ]; then
        echo "$python_cmd:$version"
        return 0
    fi
    return 1
}

# 查找合适的 Python
PYTHON_CMD=""
for cmd in python3.12 python3.11 python3.10 python3.9 python3 python; do
    if result=$(check_python_version $cmd); then
        PYTHON_CMD=$(echo $result | cut -d: -f1)
        PYTHON_VERSION=$(echo $result | cut -d: -f2)
        echo "✓ 找到合适的 Python: $PYTHON_CMD ($PYTHON_VERSION)"
        break
    fi
done

if [ -z "$PYTHON_CMD" ]; then
    echo ""
    echo "❌ 错误: 未找到 Python $REQUIRED_PYTHON_VERSION 或更高版本"
    echo ""
    echo "请先安装 Python 3.9+:"
    echo ""
    echo "macOS:"
    echo "  brew install python@3.9"
    echo ""
    echo "Ubuntu/Debian:"
    echo "  sudo apt-get update"
    echo "  sudo apt-get install python3.9 python3.9-venv python3-pip"
    echo ""
    echo "CentOS/RHEL:"
    echo "  sudo yum install python39 python39-pip"
    echo ""
    echo "Fedora:"
    echo "  sudo dnf install python3.9"
    echo ""
    exit 1
fi

# 检查是否已存在虚拟环境
if [ -d "$VENV_NAME" ]; then
    echo ""
    echo "⚠️  虚拟环境 '$VENV_NAME' 已存在"
    read -p "是否删除并重建? (y/N): " response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        echo "删除现有环境..."
        rm -rf "$VENV_NAME"
    else
        echo "使用现有环境"
    fi
fi

# 创建虚拟环境
if [ ! -d "$VENV_NAME" ]; then
    echo ""
    echo "创建虚拟环境..."
    $PYTHON_CMD -m venv "$VENV_NAME"
    echo "✓ 虚拟环境创建完成"
fi

# 激活虚拟环境并安装依赖
echo ""
echo "安装项目依赖..."
source "$VENV_NAME/bin/activate"
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "=========================================="
echo "✅ 环境设置完成!"
echo "=========================================="
echo ""
echo "激活环境："
echo "  source $VENV_NAME/bin/activate"
echo ""
echo "运行示例："
echo "  source $VENV_NAME/bin/activate"
echo "  python main.py examples/templates/template_a_column.xlsx examples/logs/sample_log_opsch.txt"
echo ""
echo "退出环境："
echo "  deactivate"
echo "=========================================="
